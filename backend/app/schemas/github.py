from pydantic import BaseModel, Field, field_validator

from app.schemas.pool_item import PoolItemResponse


class GitHubOAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class GitHubRepoAnalysis(BaseModel):
    area: str = Field(min_length=1, max_length=120)
    technologies: list[str] = Field(default_factory=list, max_length=30)
    short_description: str = Field(min_length=1, max_length=500)

    @field_validator("area", "short_description")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("değer boş olamaz")
        return normalized

    @field_validator("technologies")
    @classmethod
    def normalize_technologies(cls, value: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for item in value:
            clean = item.strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized


class GitHubSyncResponse(BaseModel):
    queued: bool


class GitHubImportResult(BaseModel):
    imported_count: int
    items: list[PoolItemResponse]
