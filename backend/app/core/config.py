from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EMBEDDING_DIMENSION = 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://cv_tailor:cv_tailor_dev@localhost:5432/cv_tailor"
    jwt_secret: str = Field(default="development-only-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    llm_api_key: str | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    embedding_model: str = "intfloat/multilingual-e5-large"
    pdf_import_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    github_oauth_redirect_uri: str = "http://localhost:8000/github/oauth/callback"
    github_token_encryption_key: str | None = None
    github_api_timeout_seconds: float = Field(default=20.0, gt=0)
    typst_binary: str = "typst"
    typst_render_timeout_seconds: float = Field(default=5.0, gt=0)
    render_output_dir: str = "storage/generated_cvs"
    log_level: str = "INFO"
    log_format: str = "json"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
