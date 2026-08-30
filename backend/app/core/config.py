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
    frontend_base_url: str = "http://localhost:5173"
    cors_allow_origins: str = "http://localhost:5173,http://localhost:8080"
    jwt_secret: str = Field(default="development-only-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    llm_api_key: str | None = None
    llm_provider: str = "openai"
    # Users bring their own API key. Set this only for a single-user local
    # setup where falling back to the server LLM_API_KEY is intended.
    allow_shared_llm_key: bool = False
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    embedding_model: str = "intfloat/multilingual-e5-large"
    pdf_import_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    github_oauth_redirect_uri: str = "http://localhost:8000/github/oauth/callback"
    github_token_encryption_key: str | None = None
    # Encrypts every stored user secret (GitHub tokens, LLM API keys). Falls back
    # to the older GitHub-specific name so existing .env files keep working.
    credential_encryption_key: str | None = None
    github_api_timeout_seconds: float = Field(default=20.0, gt=0)
    # A run whose worker died is never going to advance; after this long an
    # unfinished run is reported as failed instead of polling forever.
    pipeline_stale_after_seconds: int = Field(default=900, gt=0)
    # Each run makes several provider calls and holds a database session, so
    # the number in flight is capped rather than growing with demand.
    pipeline_max_concurrent: int = Field(default=4, gt=0)
    typst_binary: str = "typst"
    typst_render_timeout_seconds: float = Field(default=5.0, gt=0)
    render_output_dir: str = "storage/generated_cvs"
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def secret_encryption_key(self) -> str | None:
        return self.credential_encryption_key or self.github_token_encryption_key

    @property
    def cors_allow_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_allow_origins.split(",") if origin.strip()]


# Values shipped in .env.example and the compose defaults. They are public, so a
# deployment still using one of them can have its tokens forged by anyone.
PLACEHOLDER_JWT_SECRETS = frozenset(
    {
        "change-me-to-a-long-random-secret",
        "development-only-change-me",
    }
)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
