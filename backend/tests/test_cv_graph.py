from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api import cv_generation as cv_generation_api
from app.db.session import SessionLocal
from app.graphs.nodes.cvtailor import TailoredCVDraft, TailoredCVDraftItem
from app.graphs.nodes.selector import SelectorRanking, SelectedPoolItem
from app.main import app
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.generated_cv import GeneratedCV
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.profile import Profile
from app.models.user import User
from app.schemas.job import JobRequirementExtraction

client = TestClient(app)


def unit_vector(index: int) -> list[float]:
    values = [0.0] * 1024
    values[index] = 1.0
    return values


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        return unit_vector(0)


class FakeGraphLLMService:
    async def structured(self, prompt: str, response_model, *, system_prompt: str | None = None):
        if response_model is JobRequirementExtraction:
            return JobRequirementExtraction(
                required_skills=["FastAPI", "PostgreSQL"],
                preferred_skills=["Docker"],
                years_experience=3,
                key_terms=["REST API"],
            )
        if response_model is SelectorRanking:
            with SessionLocal() as db:
                item = db.scalar(select(PoolItem).where(PoolItem.title == "Backend Platform"))
                assert item is not None
                return SelectorRanking(selected_items=[SelectedPoolItem(pool_item_id=item.id, score=0.96)])
        if response_model is TailoredCVDraft:
            with SessionLocal() as db:
                item = db.scalar(select(PoolItem).where(PoolItem.title == "Backend Platform"))
                assert item is not None
                return TailoredCVDraft(
                    output_language=ContentLanguage.EN,
                    summary="Backend engineer focused on FastAPI and PostgreSQL services.",
                    experience=[],
                    projects=[
                        TailoredCVDraftItem(
                            source_index=1,
                            title="Backend Platform",
                            content="Built REST API services with FastAPI and PostgreSQL.",
                            technologies=["FastAPI", "PostgreSQL"],
                        )
                    ],
                    skills=[],
                )
        raise AssertionError(f"Unexpected response model: {response_model}")


@pytest.fixture(autouse=True)
def clean_users_and_overrides(tmp_path: Path, monkeypatch):
    app.dependency_overrides[cv_generation_api.get_llm_service] = lambda: FakeGraphLLMService()
    app.dependency_overrides[cv_generation_api.get_embedding_service] = lambda: FakeEmbeddingService()

    def fake_render_task(generated_cv_id: UUID) -> None:
        pdf_path = tmp_path / f"{generated_cv_id}.pdf"
        pdf_path.write_bytes(b"%PDF-1.7\ncv graph\n")
        with SessionLocal() as db:
            generated = db.get(GeneratedCV, generated_cv_id)
            assert generated is not None
            generated.pdf_path = str(pdf_path)
            db.commit()

    monkeypatch.setattr("app.graphs.cv_graph.render_generated_cv_task", fake_render_task)

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


def seed_verified_pool(headers_email: str) -> UUID:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == headers_email))
        assert user is not None
        db.add(
            Profile(
                user_id=user.id,
                full_name="Ada Lovelace",
                contact={"email": headers_email, "github": "https://github.com/ada"},
                education=[],
                personal_info={},
            )
        )
        item = PoolItem(
            user_id=user.id,
            source=PoolItemSource.MANUAL,
            type=PoolItemType.PROJECT,
            title="Backend Platform",
            raw_content="Built REST API services with FastAPI and PostgreSQL.",
            tags=["backend"],
            technologies=["FastAPI", "PostgreSQL"],
            language=ContentLanguage.EN,
            embedding=unit_vector(0),
            verified_by_user=True,
        )
        unverified = PoolItem(
            user_id=user.id,
            source=PoolItemSource.PDF,
            type=PoolItemType.SKILL,
            title="Unverified Kubernetes",
            raw_content="Kubernetes operations.",
            tags=[],
            technologies=["Kubernetes"],
            language=ContentLanguage.EN,
            embedding=unit_vector(0),
            verified_by_user=False,
        )
        db.add_all([item, unverified])
        db.commit()
        db.refresh(item)
        return item.id


def test_cv_generation_graph_creates_job_generated_cv_pdf_and_ats_score() -> None:
    email = "graph-one@example.com"
    headers = auth_headers(email)
    selected_item_id = seed_verified_pool(email)

    start = client.post(
        "/cv-generation",
        headers=headers,
        json={"raw_text": "We need a backend engineer with FastAPI, PostgreSQL, Docker and REST API experience."},
    )

    assert start.status_code == 202
    pipeline_id = start.json()["pipeline_id"]
    status_response = client.get(f"/cv-generation/{pipeline_id}", headers=headers)
    assert status_response.status_code == 200
    progress = status_response.json()
    assert progress["status"] == "completed"
    assert [step["name"] for step in progress["steps"]] == [
        "job_parser",
        "selector",
        "cvtailor",
        "evaluator",
        "typst_renderer",
    ]
    assert {step["status"] for step in progress["steps"]} == {"completed"}
    assert all(step["duration_ms"] is not None for step in progress["steps"])
    assert progress["duration_ms"] is not None

    generated_id = UUID(progress["generated_cv_id"])
    with SessionLocal() as db:
        job = db.get(Job, UUID(progress["job_id"]))
        generated = db.get(GeneratedCV, generated_id)
        assert job is not None
        assert generated is not None
        assert generated.job_id == job.id
        assert generated.selected_pool_item_ids == [selected_item_id]
        assert generated.ats_score is not None
        assert 88.0 <= generated.ats_score <= 89.0
        assert generated.ats_score == 88.24
        assert generated.pdf_path is not None
        assert Path(generated.pdf_path).read_bytes().startswith(b"%PDF")
        assert "Ada Lovelace" in (generated.typst_source or "")


def test_cv_generation_progress_is_tenant_scoped() -> None:
    first_headers = auth_headers("graph-scope-one@example.com")
    seed_verified_pool("graph-scope-one@example.com")
    second_headers = auth_headers("graph-scope-two@example.com")

    start = client.post(
        "/cv-generation",
        headers=first_headers,
        json={"raw_text": "We need FastAPI and PostgreSQL."},
    )

    assert start.status_code == 202
    pipeline_id = start.json()["pipeline_id"]
    assert client.get(f"/cv-generation/{pipeline_id}", headers=second_headers).status_code == 404
