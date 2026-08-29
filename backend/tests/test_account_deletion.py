from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.main import app
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.generated_cv import GeneratedCV
from app.models.github_connection import GitHubConnection
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.profile import Profile
from app.models.user import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_users() -> None:
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def _auth_headers(email: str) -> dict[str, str]:
    password = "strong-password"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": password, "kvkk_consent": True},
    )
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _count_user_rows(model: type, user_id) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) or 0


def _seed_full_user(email: str, pdf_path: Path) -> tuple[dict[str, str], object]:
    headers = _auth_headers(email)
    pdf_path.write_bytes(b"%PDF-1.7\naccount delete\n")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.add(Profile(user_id=user.id, full_name=email, contact={}, education=[], personal_info={}))
        pool_item = PoolItem(
            user_id=user.id,
            source=PoolItemSource.MANUAL,
            type=PoolItemType.PROJECT,
            raw_content="Built a FastAPI service.",
            title="FastAPI Service",
            tags=["backend"],
            technologies=["FastAPI"],
            language=ContentLanguage.EN,
            verified_by_user=True,
        )
        job = Job(
            user_id=user.id,
            raw_text="We need FastAPI.",
            detected_language=ContentLanguage.EN,
            parsed_requirements_json={"required_skills": ["FastAPI"]},
        )
        github = GitHubConnection(
            user_id=user.id,
            github_username="octocat",
            access_token_encrypted="encrypted-token",
        )
        db.add_all([pool_item, job, github])
        db.flush()
        db.add(
            GeneratedCV(
                user_id=user.id,
                job_id=job.id,
                selected_pool_item_ids=[pool_item.id],
                output_language=ContentLanguage.EN,
                typst_source="#let cv = (:)",
                pdf_path=str(pdf_path),
                ats_score=91.0,
            )
        )
        db.commit()
        user_id = user.id

    return headers, user_id


def test_delete_account_cascades_user_data_and_removes_pdf_files(tmp_path: Path) -> None:
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    first_headers, first_user_id = _seed_full_user("delete-me@example.com", first_pdf)
    _, second_user_id = _seed_full_user("keep-me@example.com", second_pdf)

    response = client.request(
        "DELETE",
        "/account",
        headers=first_headers,
        json={"confirmation": "HESABIMI SIL"},
    )

    assert response.status_code == 204
    assert not first_pdf.exists()
    assert second_pdf.exists()

    with SessionLocal() as db:
        assert db.get(User, first_user_id) is None
        assert db.get(User, second_user_id) is not None

    for model in [Profile, PoolItem, Job, GeneratedCV, GitHubConnection]:
        assert _count_user_rows(model, first_user_id) == 0
        assert _count_user_rows(model, second_user_id) == 1


def test_delete_account_requires_explicit_confirmation(tmp_path: Path) -> None:
    pdf = tmp_path / "still-here.pdf"
    headers, user_id = _seed_full_user("confirm-required@example.com", pdf)

    response = client.request(
        "DELETE",
        "/account",
        headers=headers,
        json={"confirmation": "delete"},
    )

    assert response.status_code == 400
    assert pdf.exists()
    with SessionLocal() as db:
        assert db.get(User, user_id) is not None
