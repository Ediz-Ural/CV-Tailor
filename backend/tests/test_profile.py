from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
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
        "contact": {"email": f"{name.lower()}@example.com", "phone": "+90 555 000 0000"},
        "education": [
            {
                "institution": "Example University",
                "degree": "BSc Computer Engineering",
                "graduation_year": 2024,
            }
        ],
        "personal_info": {"location": "Istanbul", "summary": "Backend developer"},
    }


def test_profile_create_update_and_read_preserves_values() -> None:
    headers = auth_headers("profile-owner@example.com")

    created = client.post("/profile", headers=headers, json=profile_payload("First Name"))
    assert created.status_code == 201
    assert created.json()["full_name"] == "First Name"

    replaced_payload = profile_payload("Replacement Name")
    replaced_payload["education"] = []
    replaced = client.put("/profile", headers=headers, json=replaced_payload)
    assert replaced.status_code == 200
    assert replaced.json()["education"] == []

    patched = client.patch(
        "/profile",
        headers=headers,
        json={"full_name": "Updated Name", "contact": {"email": "updated@example.com"}},
    )
    assert patched.status_code == 200

    fetched = client.get("/profile", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["full_name"] == "Updated Name"
    assert fetched.json()["contact"] == {"email": "updated@example.com"}
    assert fetched.json()["education"] == []
    assert fetched.json()["personal_info"] == replaced_payload["personal_info"]


def test_profile_endpoints_are_isolated_by_authenticated_user() -> None:
    first_headers = auth_headers("first-profile@example.com")
    second_headers = auth_headers("second-profile@example.com")

    first = client.post("/profile", headers=first_headers, json=profile_payload("First User"))
    second = client.post("/profile", headers=second_headers, json=profile_payload("Second User"))
    assert first.status_code == second.status_code == 201
    assert first.json()["user_id"] != second.json()["user_id"]

    first_read = client.get("/profile", headers=first_headers)
    second_read = client.get("/profile", headers=second_headers)
    assert first_read.json()["id"] == first.json()["id"]
    assert second_read.json()["id"] == second.json()["id"]

    first_update = client.patch("/profile", headers=first_headers, json={"full_name": "First Updated"})
    assert first_update.status_code == 200
    assert client.get("/profile", headers=second_headers).json()["full_name"] == "Second User"

    assert client.delete("/profile", headers=first_headers).status_code == 204
    assert client.get("/profile", headers=first_headers).status_code == 404
    assert client.get("/profile", headers=second_headers).status_code == 200


def test_profile_requires_authentication_and_valid_payload() -> None:
    assert client.get("/profile").status_code == 401

    headers = auth_headers("validation@example.com")
    invalid = client.post(
        "/profile",
        headers=headers,
        json={**profile_payload("Valid Name"), "education": ["not-an-object"]},
    )
    assert invalid.status_code == 422

    null_education = client.patch("/profile", headers=headers, json={"education": None})
    assert null_education.status_code == 422
