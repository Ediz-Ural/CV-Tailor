from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from jose import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("ascii"))
    except (TypeError, ValueError):
        return False


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_github_oauth_state(user_id: UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=10)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires_at, "typ": "github_oauth_state"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_github_oauth_state(state: str) -> UUID:
    payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("typ") != "github_oauth_state":
        raise ValueError("invalid state token type")
    return UUID(payload["sub"])


def _github_token_cipher() -> Fernet:
    if not settings.github_token_encryption_key:
        raise ValueError("GITHUB_TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(settings.github_token_encryption_key.encode("ascii"))


def encrypt_github_token(token: str) -> str:
    return _github_token_cipher().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_github_token(encrypted_token: str) -> str:
    try:
        return _github_token_cipher().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("GitHub token cannot be decrypted") from exc
