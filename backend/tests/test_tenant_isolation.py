from collections.abc import Generator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api import generated_cvs as generated_cvs_api
from app.api.pool_items import get_embedding_service
from app.core.config import EMBEDDING_DIMENSION
from app.db.session import SessionLocal
from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem
from app.main import app
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.generated_cv import GeneratedCV
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User

client = TestClient(app)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.375] * EMBEDDING_DIMENSION


@pytest.fixture(autouse=True)
def clean_users_and_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()

    def fake_render_task(generated_cv_id: UUID) -> None:
        pdf_path = tmp_path / f"{generated_cv_id}.pdf"
        pdf_path.write_bytes(b"%PDF-1.7\ntenant isolation\n")
        with SessionLocal() as db:
            generated = db.get(GeneratedCV, generated_cv_id)
            assert generated is not None
            generated.pdf_path = str(pdf_path)
            db.commit()

    monkeypatch.setattr(generated_cvs_api, "render_generated_cv_task", fake_render_task)

    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    app.dependency_overrides.clear()
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def auth_headers(email: str) -> dict[str, str]:
    password = "strong-password"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": password, "kvkk_consent": True},
    )
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def profile_payload(name: str) -> dict[str, object]:
    return {
        "full_name": name,
        "contact": {"email": f"{name.casefold().replace(' ', '.')}@example.com"},
        "education": [],
        "personal_info": {"summary": "Backend developer"},
    }


def pool_item_payload(title: str) -> dict[str, object]:
    return {
        "type": "project",
        "title": title,
        "raw_content": "Built FastAPI services with PostgreSQL.",
        "tags": ["backend"],
        "technologies": ["FastAPI", "PostgreSQL"],
    }


def tailored_cv_payload(source_id: UUID) -> dict[str, object]:
    return TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Backend engineer focused on FastAPI services.",
        projects=[
            TailoredCVItem(
                source_pool_item_id=source_id,
                title="Backend API",
                content="Built FastAPI services with PostgreSQL.",
                technologies=["FastAPI", "PostgreSQL"],
            )
        ],
    ).model_dump(mode="json")


def test_protected_profile_pool_job_and_generated_cv_resources_are_tenant_scoped() -> None:
    owner_headers = auth_headers("tenant-owner@example.com")
    other_headers = auth_headers("tenant-other@example.com")

    owner_profile = client.post("/profile", headers=owner_headers, json=profile_payload("Owner User"))
    other_profile = client.post("/profile", headers=other_headers, json=profile_payload("Other User"))
    assert owner_profile.status_code == other_profile.status_code == 201
    assert client.get("/profile", headers=owner_headers).json()["id"] == owner_profile.json()["id"]
    assert client.get("/profile", headers=other_headers).json()["id"] == other_profile.json()["id"]

    owner_item = client.post("/pool-items", headers=owner_headers, json=pool_item_payload("Owner API"))
    other_item = client.post("/pool-items", headers=other_headers, json=pool_item_payload("Other API"))
    assert owner_item.status_code == other_item.status_code == 201
    owner_item_id = owner_item.json()["id"]
    other_item_id = other_item.json()["id"]
    assert client.get(f"/pool-items/{owner_item_id}", headers=other_headers).status_code == 404
    assert [item["id"] for item in client.get("/pool-items", headers=owner_headers).json()] == [owner_item_id]
    assert [item["id"] for item in client.get("/pool-items", headers=other_headers).json()] == [other_item_id]

    with SessionLocal() as db:
        owner = db.scalar(select(User).where(User.email == "tenant-owner@example.com"))
        other = db.scalar(select(User).where(User.email == "tenant-other@example.com"))
        assert owner is not None
        assert other is not None
        owner_job = Job(
            user_id=owner.id,
            raw_text="We need FastAPI and PostgreSQL.",
            detected_language=ContentLanguage.EN,
            parsed_requirements_json={"required_skills": ["FastAPI", "PostgreSQL"]},
        )
        other_job = Job(
            user_id=other.id,
            raw_text="We need React.",
            detected_language=ContentLanguage.EN,
            parsed_requirements_json={"required_skills": ["React"]},
        )
        db.add_all([owner_job, other_job])
        db.commit()
        db.refresh(owner_job)
        db.refresh(other_job)
        owner_job_id = owner_job.id
        other_job_id = other_job.id

    assert client.get(f"/jobs/{owner_job_id}", headers=other_headers).status_code == 404
    assert [job["id"] for job in client.get("/jobs", headers=owner_headers).json()] == [str(owner_job_id)]
    assert [job["id"] for job in client.get("/jobs", headers=other_headers).json()] == [str(other_job_id)]

    source_id = uuid4()
    cross_tenant_render = client.post(
        "/generated-cvs/render",
        headers=other_headers,
        json={
            "job_id": str(owner_job_id),
            "selected_pool_item_ids": [str(source_id)],
            "tailored_cv": tailored_cv_payload(source_id),
            "ats_score": 91.0,
        },
    )
    assert cross_tenant_render.status_code == 404

    owner_render = client.post(
        "/generated-cvs/render",
        headers=owner_headers,
        json={
            "job_id": str(owner_job_id),
            "selected_pool_item_ids": [str(source_id)],
            "tailored_cv": tailored_cv_payload(source_id),
            "ats_score": 91.0,
        },
    )
    assert owner_render.status_code == 202
    generated_id = owner_render.json()["id"]
    assert client.get(f"/generated-cvs/{generated_id}/download", headers=other_headers).status_code == 404
    assert client.get(f"/generated-cvs/{generated_id}/download", headers=owner_headers).status_code == 200

    assert client.delete("/profile", headers=owner_headers).status_code == 204
    assert client.get("/profile", headers=other_headers).json()["id"] == other_profile.json()["id"]
