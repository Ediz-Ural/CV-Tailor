from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.pool_item import PoolItemResponse
from app.schemas.profile import ProfileResponse


PDFItemKind = Literal["experience", "education", "skill"]


class PDFExtractedItem(BaseModel):
    kind: PDFItemKind
    title: str | None = Field(default=None, max_length=255)
    raw_content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=30)

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


class PDFExtractedEducation(BaseModel):
    school: str | None = Field(default=None, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    raw_content: str | None = Field(default=None, max_length=1000)

    @field_validator("school", "degree", "raw_content")
    @classmethod
    def normalize_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PDFExtractedProfile(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, max_length=2000)
    education: list[PDFExtractedEducation] = Field(default_factory=list, max_length=20)

    @field_validator("full_name", "email", "phone", "location", "summary")
    @classmethod
    def normalize_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PDFExtraction(BaseModel):
    profile: PDFExtractedProfile | None = None
    items: list[PDFExtractedItem] = Field(default_factory=list, max_length=100)


class PDFImportResponse(BaseModel):
    imported_count: int
    items: list[PoolItemResponse]
    profile: ProfileResponse | None = None
