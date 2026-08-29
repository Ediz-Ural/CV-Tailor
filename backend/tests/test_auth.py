from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import TenantScope
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.profile import Profile
from app.models.user import User

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_users() -> Generator[None, None, None]:
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def register(email: str = "user@example.com", password: str = "strong-password"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password, "kvkk_consent": True},
    )


def test_register_login_and_me_flow() -> None:
    register_response = register()

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["kvkk_consent_at"] is not None

    login_response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert claims["sub"] == registered["id"]
    assert "exp" in claims

    assert client.get("/me").status_code == 401
    me_response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["id"] == registered["id"]


def test_registration_requires_kvkk_consent_and_stores_a_hash() -> None:
    rejected = client.post(
        "/auth/register",
        json={"email": "no-consent@example.com", "password": "strong-password", "kvkk_consent": False},
    )
    assert rejected.status_code == 400

    response = register()
    assert response.status_code == 201

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert user.hashed_password != "strong-password"
        assert user.hashed_password.startswith("$2")
        assert user.kvkk_consent_at is not None


def test_kvkk_notice_is_public_and_contains_explicit_consent_text() -> None:
    response = client.get("/kvkk/aydinlatma")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "2026-06-21"
    assert "acik riza" in payload["explicit_consent_text"]
    assert any(section["title"] == "Isleme amaclari" for section in payload["sections"])


def test_invalid_token_is_rejected() -> None:
    response = client.get("/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_tenant_scope_excludes_another_users_rows() -> None:
    with SessionLocal() as db:
        first = User(email="first@example.com", hashed_password="unused")
        second = User(email="second@example.com", hashed_password="unused")
        db.add_all([first, second])
        db.flush()
        own_profile = Profile(user_id=first.id, full_name="First")
        other_profile = Profile(user_id=second.id, full_name="Second")
        db.add_all([own_profile, other_profile])
        db.commit()

        scope = TenantScope(user_id=first.id)
        profiles = db.scalars(scope.apply(select(Profile), Profile)).all()

        assert [profile.id for profile in profiles] == [own_profile.id]
