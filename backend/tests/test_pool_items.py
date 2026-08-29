from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.pool_items import get_embedding_service
from app.core.config import EMBEDDING_DIMENSION
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import PoolItemSource
from app.models.pool_item import PoolItem
from app.models.user import User

client = TestClient(app)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.125] * EMBEDDING_DIMENSION


@pytest.fixture(autouse=True)
def clean_users_and_override_embedding() -> Generator[None, None, None]:
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
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


def pool_item_payload(title: str = "Backend API") -> dict[str, object]:
    return {
        "type": "project",
        "title": title,
        "raw_content": "Built a FastAPI project with PostgreSQL and semantic search.",
        "tags": ["web-dev", " web-dev ", "api"],
        "technologies": ["FastAPI", "PostgreSQL"],
    }


def test_manual_pool_item_create_writes_embedding_and_metadata_to_database() -> None:
    headers = auth_headers("pool-owner@example.com")

    response = client.post("/pool-items", headers=headers, json=pool_item_payload())

    assert response.status_code == 201
    created = response.json()
    assert created["source"] == "manual"
    assert created["verified_by_user"] is True
    assert created["language"] == "en"
    assert created["embedding_dimensions"] == EMBEDDING_DIMENSION
    assert created["tags"] == ["web-dev", "api"]

    with SessionLocal() as db:
        item = db.get(PoolItem, UUID(created["id"]))
        assert item is not None
        assert item.source == PoolItemSource.MANUAL
        assert item.verified_by_user is True
        assert item.language.value == "en"
        assert item.embedding is not None
        assert len(item.embedding) == EMBEDDING_DIMENSION
        assert item.embedding[0] == pytest.approx(0.125)


def test_pool_item_crud_is_scoped_to_authenticated_user() -> None:
    first_headers = auth_headers("first-pool@example.com")
    second_headers = auth_headers("second-pool@example.com")

    first = client.post("/pool-items", headers=first_headers, json=pool_item_payload("First item"))
    second = client.post("/pool-items", headers=second_headers, json=pool_item_payload("Second item"))
    assert first.status_code == second.status_code == 201
    first_id = first.json()["id"]
    second_id = second.json()["id"]
    assert first.json()["user_id"] != second.json()["user_id"]

    assert client.get(f"/pool-items/{first_id}", headers=second_headers).status_code == 404
    assert client.patch(f"/pool-items/{first_id}", headers=second_headers, json={"title": "stolen"}).status_code == 404
    assert client.delete(f"/pool-items/{first_id}", headers=second_headers).status_code == 404

    first_list = client.get("/pool-items", headers=first_headers)
    second_list = client.get("/pool-items", headers=second_headers)
    assert [item["id"] for item in first_list.json()] == [first_id]
    assert [item["id"] for item in second_list.json()] == [second_id]

    patched = client.patch(
        f"/pool-items/{first_id}",
        headers=first_headers,
        json={"raw_content": "Merhaba, bu bir yazilim gelistirme projesidir.", "technologies": ["Python"]},
    )
    assert patched.status_code == 200
    assert patched.json()["language"] == "tr"
    assert patched.json()["verified_by_user"] is True
    assert patched.json()["embedding_dimensions"] == EMBEDDING_DIMENSION

    assert client.delete(f"/pool-items/{first_id}", headers=first_headers).status_code == 204
    assert client.get(f"/pool-items/{first_id}", headers=first_headers).status_code == 404
    assert client.get(f"/pool-items/{second_id}", headers=second_headers).status_code == 200

    with SessionLocal() as db:
        remaining = db.scalars(select(PoolItem)).all()
        assert [item.id for item in remaining] == [UUID(second_id)]


def test_pool_items_require_authentication_and_valid_payload() -> None:
    assert client.get("/pool-items").status_code == 401

    headers = auth_headers("pool-validation@example.com")
    education_item = client.post(
        "/pool-items",
        headers=headers,
        json={**pool_item_payload(), "type": "education", "title": "Computer Engineering"},
    )
    assert education_item.status_code == 201
    assert education_item.json()["type"] == "education"

    empty_content = client.post(
        "/pool-items",
        headers=headers,
        json={**pool_item_payload(), "raw_content": "   "},
    )
    assert empty_content.status_code == 422
