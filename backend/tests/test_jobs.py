from collections.abc import AsyncIterator, Generator
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.jobs import get_job_fetch_client, get_llm_service
from app.db.session import SessionLocal
from app.main import app
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobRequirementExtraction

client = TestClient(app)


class FakeLLMService:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def structured(
        self,
        prompt: str,
        response_model: type[JobRequirementExtraction],
        *,
        system_prompt: str | None = None,
    ) -> JobRequirementExtraction:
        assert response_model is JobRequirementExtraction
        assert system_prompt is not None
        self.prompts.append(prompt)
        return JobRequirementExtraction(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["PostgreSQL"],
            years_experience=3,
            key_terms=["REST API", "Docker"],
        )


@pytest.fixture(autouse=True)
def clean_users_and_overrides() -> Generator[None, None, None]:
    fake_llm = FakeLLMService()
    app.dependency_overrides[get_llm_service] = lambda: fake_llm
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


def test_job_text_input_detects_tr_and_stores_structured_requirements() -> None:
    headers = auth_headers("job-tr@example.com")
    text = "Kidemli Python gelistirici araniyor. FastAPI ile REST API gelistirme deneyimi gerekir."

    response = client.post("/jobs", headers=headers, json={"raw_text": text})

    assert response.status_code == 201
    created = response.json()
    assert created["source_url"] is None
    assert created["raw_text"] == text
    assert created["detected_language"] == "tr"
    assert created["parsed_requirements_json"] == {
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["PostgreSQL"],
        "years_experience": 3,
        "key_terms": ["REST API", "Docker"],
    }

    with SessionLocal() as db:
        job = db.get(Job, UUID(created["id"]))
        assert job is not None
        assert job.user_id == UUID(created["user_id"])
        assert job.detected_language.value == "tr"


def test_job_text_input_detects_en_and_mixed_uses_dominant_language() -> None:
    headers = auth_headers("job-language@example.com")

    en = client.post(
        "/jobs",
        headers=headers,
        json={"raw_text": "We are hiring a software engineer with FastAPI and PostgreSQL experience."},
    )
    mixed = client.post(
        "/jobs",
        headers=headers,
        json={"raw_text": "Python developer ariyoruz ve takim icin FastAPI experience gerekli."},
    )

    assert en.status_code == 201
    assert en.json()["detected_language"] == "en"
    assert mixed.status_code == 201
    assert mixed.json()["detected_language"] == "tr"


def test_job_url_input_fetches_one_page_and_keeps_tenant_scope() -> None:
    first_headers = auth_headers("job-url-one@example.com")
    second_headers = auth_headers("job-url-two@example.com")
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        assert request.method == "GET"
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="""
            <html><body>
              <a href="https://example.test/next">next page must not be fetched</a>
              <main>Senior software engineer for FastAPI and Docker.</main>
            </body></html>
            """,
        )

    async def mock_client() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as test_client:
            yield test_client

    app.dependency_overrides[get_job_fetch_client] = mock_client

    response = client.post("/jobs", headers=first_headers, json={"source_url": "https://example.test/job"})

    assert response.status_code == 201
    created = response.json()
    assert requested_urls == ["https://example.test/job"]
    assert created["source_url"] == "https://example.test/job"
    assert "next page must not be fetched" in created["raw_text"]
    assert created["parsed_requirements_json"]["required_skills"] == ["Python", "FastAPI"]

    assert client.get(f"/jobs/{created['id']}", headers=second_headers).status_code == 404
    assert [item["id"] for item in client.get("/jobs", headers=first_headers).json()] == [created["id"]]
    assert client.get("/jobs", headers=second_headers).json() == []

    with SessionLocal() as db:
        all_jobs = db.scalars(select(Job)).all()
        assert len(all_jobs) == 1
        assert str(all_jobs[0].source_url) == "https://example.test/job"


def test_job_input_requires_authentication_and_exactly_one_source() -> None:
    assert client.post("/jobs", json={"raw_text": "hello"}).status_code == 401

    headers = auth_headers("job-validation@example.com")
    both = client.post(
        "/jobs",
        headers=headers,
        json={"raw_text": "hello", "source_url": "https://example.test/job"},
    )
    neither = client.post("/jobs", headers=headers, json={})

    assert both.status_code == 422
    assert neither.status_code == 422
