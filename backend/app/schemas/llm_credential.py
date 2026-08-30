from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LLMCredentialUpsert(BaseModel):
    provider: Literal["openai", "anthropic"] = "openai"
    model: str = Field(min_length=1, max_length=128)
    api_key: str = Field(min_length=8, max_length=512)

    @field_validator("model", "api_key")
    @classmethod
    def strip_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("deger bos olamaz")
        return normalized


class LLMCredentialResponse(BaseModel):
    """What the browser is allowed to know about a stored key."""

    provider: str
    model: str
    key_hint: str
    updated_at: datetime
