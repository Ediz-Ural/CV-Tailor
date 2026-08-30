from collections.abc import Generator

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api import llm_credential as llm_credential_api
from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models.llm_credential import LLMCredential
from app.models.user import User
from app.services.llm import LLMService
from app.services.llm_credentials import LLMCredentialMissing, build_llm_config, load_llm_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_users_and_encryption_key() -> Generator[None, None, None]:
    original_key = settings.credential_encryption_key
    settings.credential_encryption_key = Fernet.generate_key().decode("ascii")
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    app.dependency_overrides.clear()
    settings.credential_encryption_key = original_key
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def _verification_service(status_code: int, body: dict[str, object]) -> LLMService:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    # The real dependency carries the submitted key; the suite only needs a
    # non-empty one so verification reaches the transport.
    config = settings.model_copy(update={"llm_provider": "openai", "llm_api_key": "sk-verification"})
    return LLMService(config, httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def accepting_verification() -> LLMService:
    return _verification_service(200, {"data": []})


def rejecting_verification() -> LLMService:
    return _verification_service(401, {"error": "invalid_api_key"})


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


def save_key(headers: dict[str, str], api_key: str = "sk-test-key-value-1234") -> httpx.Response:
    return client.put(
        "/llm-credential",
        headers=headers,
        json={"provider": "openai", "model": "gpt-4o-mini", "api_key": api_key},
    )


def test_stored_key_is_encrypted_and_never_returned() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    headers = auth_headers("keys@example.com")

    response = save_key(headers)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-4o-mini"
    assert body["key_hint"] == "1234"
    assert "api_key" not in body
    assert "sk-test-key-value-1234" not in response.text

    with SessionLocal() as db:
        credential = db.scalar(select(LLMCredential))
        assert credential is not None
        assert credential.api_key_encrypted != "sk-test-key-value-1234"
        assert "sk-test" not in credential.api_key_encrypted


def test_a_rejected_key_is_not_stored() -> None:
    # Otherwise the user only finds out minutes later, mid-pipeline.
    app.dependency_overrides[llm_credential_api.get_verification_service] = rejecting_verification
    headers = auth_headers("badkey@example.com")

    response = save_key(headers, "sk-wrong-key-0000")

    assert response.status_code == 400
    assert "401" in response.json()["detail"]
    with SessionLocal() as db:
        assert db.scalar(select(LLMCredential)) is None


def test_saving_again_replaces_the_previous_key() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    headers = auth_headers("rotate@example.com")

    assert save_key(headers, "sk-first-key-1111").status_code == 200
    assert save_key(headers, "sk-second-key-2222").status_code == 200

    with SessionLocal() as db:
        credentials = list(db.scalars(select(LLMCredential)))
        assert len(credentials) == 1
        assert credentials[0].key_hint == "2222"


def test_credentials_are_scoped_to_their_owner() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    owner = auth_headers("owner@example.com")
    other = auth_headers("other@example.com")
    assert save_key(owner, "sk-owner-key-9999").status_code == 200

    assert client.get("/llm-credential", headers=other).status_code == 404
    assert client.get("/llm-credential", headers=owner).json()["key_hint"] == "9999"


def test_key_can_be_removed() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    headers = auth_headers("remove@example.com")
    assert save_key(headers).status_code == 200

    assert client.delete("/llm-credential", headers=headers).status_code == 204
    assert client.get("/llm-credential", headers=headers).status_code == 404
    assert client.delete("/llm-credential", headers=headers).status_code == 404


def test_key_is_deleted_with_the_account() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    headers = auth_headers("erase@example.com")
    assert save_key(headers).status_code == 200

    deleted = client.request(
        "DELETE", "/account", headers=headers, json={"confirmation": "HESABIMI SIL"}
    )

    assert deleted.status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(LLMCredential)) is None


def test_generation_is_refused_without_a_key() -> None:
    headers = auth_headers("nokey@example.com")

    response = client.post(
        "/cv-generation",
        headers=headers,
        json={"raw_text": "We need a backend engineer with FastAPI experience."},
    )

    assert response.status_code == 400
    assert "anahtar" in response.json()["detail"].lower()


def test_pipeline_uses_the_users_own_key_not_the_server_key() -> None:
    app.dependency_overrides[llm_credential_api.get_verification_service] = accepting_verification
    headers = auth_headers("ownkey@example.com")
    assert save_key(headers, "sk-user-owned-7777").status_code == 200

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "ownkey@example.com"))
        assert user is not None
        config = build_llm_config(db, user.id, settings.model_copy(update={"llm_api_key": "sk-server-key"}))

    assert config.llm_api_key == "sk-user-owned-7777"
    assert config.llm_model == "gpt-4o-mini"


def test_shared_server_key_is_off_by_default() -> None:
    with SessionLocal() as db:
        user = User(
            email="shared@example.com",
            hashed_password="x" * 20,
            kvkk_consent_at=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        server_config = settings.model_copy(update={"llm_api_key": "sk-server-key"})
        with pytest.raises(LLMCredentialMissing):
            build_llm_config(db, user.id, server_config)

        # Operators of a single-user install can opt back in explicitly.
        opted_in = server_config.model_copy(update={"allow_shared_llm_key": True})
        assert build_llm_config(db, user.id, opted_in).llm_api_key == "sk-server-key"
        assert isinstance(load_llm_service(db, user.id, opted_in), LLMService)
