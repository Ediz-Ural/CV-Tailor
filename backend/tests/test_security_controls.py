import logging
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.logging import configure_sensitive_logging, redact_sensitive_data
from app.core.security import decrypt_github_token, encrypt_github_token, hash_password
from app.db.session import SessionLocal
from app.models.github_connection import GitHubConnection
from app.models.user import User


@pytest.fixture(autouse=True)
def clean_users_and_encryption_key():
    original_key = settings.github_token_encryption_key
    settings.github_token_encryption_key = Fernet.generate_key().decode("ascii")
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    settings.github_token_encryption_key = original_key
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def test_github_token_is_stored_encrypted_not_plaintext() -> None:
    plaintext_token = "gho_ip43_plaintext_fixture"
    encrypted_token = encrypt_github_token(plaintext_token)

    with SessionLocal() as db:
        user = User(email="ip43-security@example.com", hashed_password=hash_password("strong-password"))
        db.add(user)
        db.flush()
        db.add(
            GitHubConnection(
                user_id=user.id,
                github_username="octocat",
                access_token_encrypted=encrypted_token,
            )
        )
        db.commit()

        stored = db.scalar(select(GitHubConnection))
        assert stored is not None
        assert stored.access_token_encrypted != plaintext_token
        assert stored.access_token_encrypted.startswith("gAAAA")
        assert decrypt_github_token(stored.access_token_encrypted) == plaintext_token


def test_sensitive_redaction_masks_tokens_passwords_and_personal_data(caplog: pytest.LogCaptureFixture) -> None:
    configure_sensitive_logging()
    logger = logging.getLogger("cv_tailor.security_test")

    with caplog.at_level(logging.WARNING):
        logger.warning(
            "user=%s password=%s Authorization: Bearer %s github=%s",
            "owner@example.com",
            "plain-password",
            "eyJhbGciOiJIUzI1NiJ9.payload.signature",
            "gho_log_plaintext_fixture",
        )

    output = caplog.text
    assert "owner@example.com" not in output
    assert "plain-password" not in output
    assert "eyJhbGciOiJIUzI1NiJ9.payload.signature" not in output
    assert "gho_log_plaintext_fixture" not in output
    assert "<redacted>" in output


def test_redaction_handles_structured_payloads() -> None:
    redacted = redact_sensitive_data(
        {
            "access_token": "gho_structured_plaintext_fixture",
            "profile": {"email": "person@example.com", "note": "public"},
            "items": ["password=secret-value", "safe"],
        }
    )

    assert redacted["access_token"] == "<redacted>"
    assert redacted["profile"]["email"] == "<redacted>"
    assert redacted["profile"]["note"] == "public"
    assert redacted["items"][0] == "password=<redacted>"


def test_package_logs_do_not_contain_plaintext_token_fixtures() -> None:
    logs_dir = Path(__file__).resolve().parents[2] / "logs"
    logs_text = "\n".join(path.read_text(encoding="utf-8") for path in logs_dir.glob("*.md"))
    assert "gho_plain_secret" not in logs_text
    assert "gho_graph_secret" not in logs_text
