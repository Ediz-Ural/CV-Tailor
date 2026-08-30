from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType


class PoolItemFields(BaseModel):
    type: PoolItemType
    title: str | None = Field(default=None, max_length=255)
    raw_content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=50)
    technologies: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("raw_content")
    @classmethod
    def normalize_raw_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("raw_content boş olamaz")
        return normalized

    @field_validator("tags", "technologies")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for item in value:
            clean = item.strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized


class PoolItemCreate(PoolItemFields):
    pass


class PoolItemReplace(PoolItemFields):
    pass


class PoolItemPatch(BaseModel):
    type: PoolItemType | None = None
    title: str | None = Field(default=None, max_length=255)
    raw_content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = Field(default=None, max_length=50)
    technologies: list[str] | None = Field(default=None, max_length=50)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("raw_content")
    @classmethod
    def normalize_raw_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("raw_content boş olamaz")
        return normalized

    @field_validator("tags", "technologies")
    @classmethod
    def normalize_string_list(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = []
        seen = set()
        for item in value:
            clean = item.strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized


class PoolItemResponse(PoolItemFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    source: PoolItemSource
    language: ContentLanguage
    verified_by_user: bool
    created_at: datetime
    embedding_dimensions: int


class PoolItemIdList(BaseModel):
    ids: list[UUID] = Field(default_factory=list, max_length=100)


class PoolApprovalResponse(BaseModel):
    updated_count: int
    items: list[PoolItemResponse]


class PoolRejectResponse(BaseModel):
    deleted_count: int
