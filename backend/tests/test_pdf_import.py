from collections.abc import Generator
from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import delete, select

from app.api.pdf_import import get_embedding_service, get_llm_service
from app.core.config import EMBEDDING_DIMENSION, settings
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import PoolItemSource
from app.models.pool_item import PoolItem
from app.models.profile import Profile
from app.models.user import User
from app.schemas.pdf_import import PDFExtraction

client = TestClient(app)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.25] * EMBEDDING_DIMENSION


class FakeLLMService:
    async def structured(self, prompt: str, response_model: type[PDFExtraction], *, system_prompt: str | None = None) -> PDFExtraction:
        assert "FastAPI" in prompt
        assert system_prompt
        return response_model(
            profile={
                "full_name": "John Doe",
                "email": "john@example.com",
                "phone": "+90 555 111 22 33",
                "location": "Istanbul",
                "summary": "Backend developer focused on FastAPI services.",
                "education": [{"school": "Example University", "degree": "Computer Engineering"}],
            },
            items=[
                {
                    "kind": "experience",
                    "title": "Backend Developer",
                    "raw_content": "Built FastAPI services with PostgreSQL and Docker.",
                    "tags": ["backend"],
                    "technologies": ["FastAPI", "PostgreSQL", "Docker"],
                },
                {
                    "kind": "education",
                    "title": "Computer Engineering",
                    "raw_content": "BSc in Computer Engineering.",
                    "tags": ["degree"],
                    "technologies": [],
                },
                {
                    "kind": "skill",
                    "title": "Python",
                    "raw_content": "Python, FastAPI, SQLAlchemy",
                    "tags": ["backend"],
                    "technologies": ["Python", "FastAPI", "SQLAlchemy"],
                },
            ]
        )


@pytest.fixture(autouse=True)
def clean_users_and_override_ai_services() -> Generator[None, None, None]:
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
    app.dependency_overrides[get_llm_service] = lambda: FakeLLMService()
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


def sample_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 72 720 Td (John Doe) Tj "
        b"0 -18 Td (Built FastAPI services with PostgreSQL and Docker.) Tj ET"
    )
    page[NameObject("/Contents")] = content
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )

    data = BytesIO()
    writer.write(data)
    return data.getvalue()


def test_pdf_import_creates_unverified_pdf_pool_items_with_embeddings() -> None:
    owner_headers = auth_headers("pdf-owner@example.com")
    other_headers = auth_headers("pdf-other@example.com")

    response = client.post(
        "/pool/import/pdf",
        headers=owner_headers,
        files={"file": ("cv.pdf", sample_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["imported_count"] == 3
    assert [item["source"] for item in body["items"]] == ["pdf", "pdf", "pdf"]
    assert [item["verified_by_user"] for item in body["items"]] == [False, False, False]
    assert [item["embedding_dimensions"] for item in body["items"]] == [EMBEDDING_DIMENSION] * 3
    assert body["items"][1]["type"] == "education"
    assert "education" in body["items"][1]["tags"]
    assert body["profile"]["full_name"] == "John Doe"
    assert body["profile"]["contact"]["email"] == "john@example.com"
    assert body["profile"]["education"][0]["school"] == "Example University"

    with SessionLocal() as db:
        stored = db.scalars(select(PoolItem).order_by(PoolItem.created_at, PoolItem.id)).all()
        assert len(stored) == 3
        assert {item.user_id for item in stored} == {UUID(body["items"][0]["user_id"])}
        assert {item.source for item in stored} == {PoolItemSource.PDF}
        assert all(item.verified_by_user is False for item in stored)
        assert all(item.embedding is not None and len(item.embedding) == EMBEDDING_DIMENSION for item in stored)
        profile = db.scalar(select(Profile).where(Profile.full_name == "John Doe"))
        assert profile is not None
        assert profile.contact["phone"] == "+90 555 111 22 33"
        assert profile.personal_info["summary"] == "Backend developer focused on FastAPI services."

    other_list = client.get("/pool-items", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json() == []


def test_pdf_import_rejects_corrupt_or_empty_pdf_without_crashing() -> None:
    headers = auth_headers("pdf-invalid@example.com")

    corrupt = client.post(
        "/pool/import/pdf",
        headers=headers,
        files={"file": ("cv.pdf", b"not a pdf", "application/pdf")},
    )
    assert corrupt.status_code == 422
    assert "PDF" in corrupt.json()["detail"]

    blank = client.post(
        "/pool/import/pdf",
        headers=headers,
        files={"file": ("blank.pdf", b"", "application/pdf")},
    )
    assert blank.status_code == 422


def test_pdf_import_validates_type_size_and_authentication() -> None:
    assert client.post(
        "/pool/import/pdf",
        files={"file": ("cv.pdf", sample_pdf_bytes(), "application/pdf")},
    ).status_code == 401

    headers = auth_headers("pdf-validation@example.com")
    wrong_type = client.post(
        "/pool/import/pdf",
        headers=headers,
        files={"file": ("cv.txt", b"hello", "text/plain")},
    )
    assert wrong_type.status_code == 415

    too_large = client.post(
        "/pool/import/pdf",
        headers=headers,
        files={"file": ("cv.pdf", b"%PDF-" + (b"0" * settings.pdf_import_max_bytes), "application/pdf")},
    )
    assert too_large.status_code == 413
