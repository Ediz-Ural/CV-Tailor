"""Per-user provider credentials.

Generation is billed to whoever asked for it, so the API key comes from the
user's own account rather than a shared server key. The server key is only
consulted when an operator explicitly opts in with ALLOW_SHARED_LLM_KEY, which
exists for single-user local setups and is off by default.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.llm_credential import LLMCredential
from app.services.llm import LLMService

SUPPORTED_PROVIDERS = ("openai", "anthropic")
KEY_HINT_LENGTH = 4


class LLMCredentialMissing(RuntimeError):
    """The user has not stored an API key, so nothing can be generated."""


def key_hint(api_key: str) -> str:
    return api_key.strip()[-KEY_HINT_LENGTH:]


def store_credential(db: Session, user_id: UUID, *, provider: str, model: str, api_key: str) -> LLMCredential:
    credential = db.scalar(select(LLMCredential).where(LLMCredential.user_id == user_id))
    if credential is None:
        credential = LLMCredential(user_id=user_id)
        db.add(credential)

    credential.provider = provider
    credential.model = model
    credential.api_key_encrypted = encrypt_secret(api_key)
    credential.key_hint = key_hint(api_key)
    db.commit()
    db.refresh(credential)
    return credential


def read_credential(db: Session, user_id: UUID) -> LLMCredential | None:
    return db.scalar(select(LLMCredential).where(LLMCredential.user_id == user_id))


def delete_credential(db: Session, user_id: UUID) -> bool:
    credential = read_credential(db, user_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def build_llm_config(db: Session, user_id: UUID, config: Settings = settings) -> Settings:
    """Return settings carrying this user's provider, model and key."""
    credential = read_credential(db, user_id)
    if credential is not None:
        return config.model_copy(
            update={
                "llm_provider": credential.provider,
                "llm_model": credential.model,
                "llm_api_key": decrypt_secret(credential.api_key_encrypted, label="LLM API key"),
            }
        )

    if config.allow_shared_llm_key and config.llm_api_key:
        return config

    raise LLMCredentialMissing(
        "Bu hesap için bir LLM API anahtarı kayıtlı değil. Hesap ekranından kendi "
        "anahtarınızı ekleyin."
    )


def load_llm_service(db: Session, user_id: UUID, config: Settings = settings) -> LLMService:
    return LLMService(build_llm_config(db, user_id, config))
