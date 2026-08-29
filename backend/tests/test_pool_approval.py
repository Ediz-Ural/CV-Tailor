from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.pool_items import get_embedding_service
from app.core.config import EMBEDDING_DIMENSION
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.pool_item import PoolItem
from app.models.user import User
from app.services.item_extractor import ExtractedPoolItem, create_unverified_pool_items

client = TestClient(app)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.75] * EMBEDDING_DIMENSION


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


def create_pending_item(user_id, source: PoolItemSource, title: str) -> PoolItem:
    items = create_unverified_pool_items(
        user_id,
        [
            ExtractedPoolItem(
                source=source,
                type=PoolItemType.PROJECT,
                title=title,
                raw_content=f"Built {title} with FastAPI and PostgreSQL.",
                tags=["backend", "backend"],
                technologies=["FastAPI", "PostgreSQL"],
            )
        ],
        FakeEmbeddingService(),
    )
    assert len(items) == 1
    return items[0]


def user_id_from_headers(headers: dict[str, str]):
    response = client.post(
        "/pool-items",
        headers=headers,
        json={
            "type": "skill",
            "title": "Temp",
            "raw_content": "Temporary manual item.",
            "tags": [],
            "technologies": [],
        },
    )
    assert response.status_code == 201
    item_id = UUID(response.json()["id"])
    with SessionLocal() as db:
        item = db.get(PoolItem, item_id)
        assert item is not None
        user_id = item.user_id
        db.delete(item)
        db.commit()
        return user_id


def seed_pending_items(owner_id, other_id) -> tuple[PoolItem, PoolItem, PoolItem]:
    with SessionLocal() as db:
        pdf_item = create_pending_item(owner_id, PoolItemSource.PDF, "PDF API")
        github_item = create_pending_item(owner_id, PoolItemSource.GITHUB, "GitHub API")
        other_item = create_pending_item(other_id, PoolItemSource.PDF, "Other PDF")
        manual_unverified = PoolItem(
            user_id=owner_id,
            source=PoolItemSource.MANUAL,
            type=PoolItemType.SKILL,
            title="Manual draft",
            raw_content="Manual draft must not enter pending approval.",
            tags=[],
            technologies=[],
            language=ContentLanguage.EN,
            embedding=[0.1] * EMBEDDING_DIMENSION,
            verified_by_user=False,
        )
        db.add_all([pdf_item, github_item, other_item, manual_unverified])
        db.commit()
        for item in [pdf_item, github_item, other_item]:
            db.refresh(item)
        return pdf_item, github_item, other_item


def setup_function() -> None:
    app.dependency_overrides[get_embedding_service] = lambda: FakeEmbeddingService()
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def teardown_function() -> None:
    app.dependency_overrides.clear()
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def test_pending_approve_and_reject_flow_for_automatic_items() -> None:
    owner_headers = auth_headers("approval-owner@example.com")
    other_headers = auth_headers("approval-other@example.com")
    owner_id = user_id_from_headers(owner_headers)
    other_id = user_id_from_headers(other_headers)
    pdf_item, github_item, _ = seed_pending_items(owner_id, other_id)

    pending = client.get("/pool/pending", headers=owner_headers)
    assert pending.status_code == 200
    assert {item["id"] for item in pending.json()} == {str(pdf_item.id), str(github_item.id)}
    assert {item["source"] for item in pending.json()} == {"pdf", "github"}
    assert all(item["verified_by_user"] is False for item in pending.json())

    approved = client.post("/pool/approve", headers=owner_headers, json={"ids": [str(pdf_item.id)]})
    assert approved.status_code == 200
    assert approved.json()["updated_count"] == 1
    assert approved.json()["items"][0]["verified_by_user"] is True

    rejected = client.post("/pool/reject", headers=owner_headers, json={"ids": [str(github_item.id)]})
    assert rejected.status_code == 200
    assert rejected.json() == {"deleted_count": 1}

    with SessionLocal() as db:
        stored_pdf = db.get(PoolItem, pdf_item.id)
        stored_github = db.get(PoolItem, github_item.id)
        assert stored_pdf is not None
        assert stored_pdf.verified_by_user is True
        assert stored_github is None

    assert client.get("/pool/pending", headers=owner_headers).json() == []


def test_pending_pool_items_are_tenant_isolated() -> None:
    owner_headers = auth_headers("approval-owner-iso@example.com")
    other_headers = auth_headers("approval-other-iso@example.com")
    owner_id = user_id_from_headers(owner_headers)
    other_id = user_id_from_headers(other_headers)
    owner_item, _, other_item = seed_pending_items(owner_id, other_id)

    other_pending = client.get("/pool/pending", headers=other_headers)
    assert other_pending.status_code == 200
    assert [item["id"] for item in other_pending.json()] == [str(other_item.id)]

    stolen_approve = client.post("/pool/approve", headers=other_headers, json={"ids": [str(owner_item.id)]})
    stolen_reject = client.post("/pool/reject", headers=other_headers, json={"ids": [str(owner_item.id)]})
    assert stolen_approve.status_code == 200
    assert stolen_approve.json()["updated_count"] == 0
    assert stolen_reject.status_code == 200
    assert stolen_reject.json()["deleted_count"] == 0

    with SessionLocal() as db:
        stored_owner_item = db.scalar(select(PoolItem).where(PoolItem.id == owner_item.id))
        assert stored_owner_item is not None
        assert stored_owner_item.verified_by_user is False
