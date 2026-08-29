from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    local_part, separator, domain = email.rpartition("@")
    if not separator or not local_part or "." not in domain:
        raise ValueError("gecerli bir email adresi girilmelidir")
    return email


def validate_bcrypt_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("parola en fazla 72 bayt olabilir")
    return value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8)
    kvkk_consent: bool

    _normalize_email = field_validator("email")(normalize_email)
    _validate_password = field_validator("password")(validate_bcrypt_password)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)

    _normalize_email = field_validator("email")(normalize_email)
    _validate_password = field_validator("password")(validate_bcrypt_password)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DeleteAccountRequest(BaseModel):
    confirmation: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    created_at: datetime
    kvkk_consent_at: datetime
