from typing import TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

JsonObject: TypeAlias = dict[str, JsonValue]


class ProfileFields(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    contact: JsonObject | None
    education: list[JsonObject] = Field(max_length=50)
    personal_info: JsonObject | None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("full_name bos olamaz")
        return normalized


class ProfileCreate(ProfileFields):
    pass


class ProfileReplace(ProfileFields):
    pass


class ProfilePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact: JsonObject | None = None
    education: list[JsonObject] = Field(default_factory=list, max_length=50)
    personal_info: JsonObject | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("full_name bos olamaz")
        return normalized


class ProfileResponse(ProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
