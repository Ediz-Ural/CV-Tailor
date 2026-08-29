from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.enums import ContentLanguage


class JobRequirementExtraction(BaseModel):
    summary: str = Field(default="", max_length=1200)
    required_skills: list[str] = Field(default_factory=list, max_length=80)
    preferred_skills: list[str] = Field(default_factory=list, max_length=80)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    key_terms: list[str] = Field(default_factory=list, max_length=120)

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("required_skills", "preferred_skills", "key_terms")
    @classmethod
    def normalize_terms(cls, value: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for item in value:
            clean = item.strip()
            if clean and clean.casefold() not in seen:
                normalized.append(clean)
                seen.add(clean.casefold())
        return normalized


class JobCreate(BaseModel):
    raw_text: str | None = Field(default=None, min_length=1)
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "JobCreate":
        raw_text = self.raw_text.strip() if self.raw_text else None
        if bool(raw_text) == bool(self.source_url):
            raise ValueError("raw_text veya source_url alanlarindan tam olarak biri verilmeli")
        self.raw_text = raw_text
        return self


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    source_url: str | None
    raw_text: str
    detected_language: ContentLanguage
    parsed_requirements_json: dict
    created_at: datetime
