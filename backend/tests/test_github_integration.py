from collections.abc import Generator
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.github import get_github_oauth_client, get_github_sync_scheduler
from app.core.config import EMBEDDING_DIMENSION, settings
from app.core.security import decrypt_github_token
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import PoolItemSource
from app.models.github_connection import GitHubConnection
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.github import GitHubRepoAnalysis
from app.services.github import GitHubRepositorySignal, analyze_repositories_to_pool_items, is_eligible_repository

client = TestClient(app)


class FakeGitHubOAuthClient:
    def __init__(self) -> None:
        self.token: str | None = None

    async def exchange_code_for_token(self, code: str) -> str:
        assert code == "oauth-code"
        return "gho_plain_secret"

    async def get_authenticated_username(self) -> str:
        assert self.token == "gho_plain_secret"
        return "octocat"


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.5] * EMBEDDING_DIMENSION


class FakeLLMService:
    async def structured(
        self,
        prompt: str,
        response_model: type[GitHubRepoAnalysis],
        *,
        system_prompt: str | None = None,
    ) -> GitHubRepoAnalysis:
        assert "README" in prompt
        assert "Commit count" in prompt
        assert system_prompt
        return response_model(
            area="backend",
            technologies=["FastAPI", "PostgreSQL"],
            short_description="Built a FastAPI service with PostgreSQL persistence.",
        )


class FakeGitHubAnalyzerClient:
    async def collect_repository_signals(self) -> list[GitHubRepositorySignal]:
        return [signal for signal in sample_signals() if is_eligible_repository(signal)]


@pytest.fixture(autouse=True)
def clean_users_and_settings() -> Generator[None, None, None]:
    original_client_id = settings.github_oauth_client_id
    original_secret = settings.github_oauth_client_secret
    original_redirect = settings.github_oauth_redirect_uri
    original_key = settings.github_token_encryption_key
    settings.github_oauth_client_id = "client-id"
    settings.github_oauth_client_secret = "client-secret"
    settings.github_oauth_redirect_uri = "http://testserver/github/oauth/callback"
    settings.github_token_encryption_key = Fernet.generate_key().decode("ascii")
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    app.dependency_overrides.clear()
    settings.github_oauth_client_id = original_client_id
    settings.github_oauth_client_secret = original_secret
    settings.github_oauth_redirect_uri = original_redirect
    settings.github_token_encryption_key = original_key
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def auth_headers(email: str) -> dict[str, str]:
    password = "strong-password"
    register = client.post(
        "/auth/register",
        json={"email": email, "password": password, "kvkk_consent": True},
    )
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def sample_signals() -> list[GitHubRepositorySignal]:
    return [
        GitHubRepositorySignal(
            name="cv-tailor-api",
            full_name="octocat/cv-tailor-api",
            html_url="https://github.com/octocat/cv-tailor-api",
            description="Production API",
            fork=False,
            topics=["fastapi", "postgres"],
            languages={"Python": 15000},
            commit_count=12,
            readme="# API\nFastAPI service with PostgreSQL.",
        ),
        GitHubRepositorySignal(
            name="forked-api",
            full_name="octocat/forked-api",
            html_url="https://github.com/octocat/forked-api",
            description=None,
            fork=True,
            topics=[],
            languages={"Python": 1},
            commit_count=3,
            readme="# Fork",
        ),
        GitHubRepositorySignal(
            name="empty-api",
            full_name="octocat/empty-api",
            html_url="https://github.com/octocat/empty-api",
            description=None,
            fork=False,
            topics=[],
            languages={},
            commit_count=0,
            readme="# Empty",
        ),
        GitHubRepositorySignal(
            name="fastapi-tutorial",
            full_name="octocat/fastapi-tutorial",
            html_url="https://github.com/octocat/fastapi-tutorial",
            description="Tutorial repo",
            fork=False,
            topics=["tutorial"],
            languages={"Python": 100},
            commit_count=5,
            readme="# Tutorial",
        ),
    ]


def test_github_oauth_callback_encrypts_token_and_queues_background_sync() -> None:
    headers = auth_headers("github-owner@example.com")
    start = client.post("/github/oauth/start", headers=headers)
    assert start.status_code == 200
    state = start.json()["state"]
    assert "github.com/login/oauth/authorize" in start.json()["authorization_url"]

    queued: list[UUID] = []

    def fake_scheduler(background_tasks: BackgroundTasks, user_id: UUID) -> None:
        assert isinstance(background_tasks, BackgroundTasks)
        queued.append(user_id)

    app.dependency_overrides[get_github_oauth_client] = lambda: FakeGitHubOAuthClient()
    app.dependency_overrides[get_github_sync_scheduler] = lambda: fake_scheduler

    callback = client.get(f"/github/oauth/callback?code=oauth-code&state={state}", follow_redirects=False)

    # The user agent lands here from GitHub, so the response has to take the
    # browser back into the app rather than render a JSON body.
    assert callback.status_code == 303
    location = callback.headers["location"]
    assert location.startswith(f"{settings.frontend_base_url.rstrip('/')}/pool?")
    assert "github=connected" in location
    assert "username=octocat" in location
    assert len(queued) == 1

    with SessionLocal() as db:
        connection = db.scalar(select(GitHubConnection))
        assert connection is not None
        assert connection.github_username == "octocat"
        assert connection.access_token_encrypted != "gho_plain_secret"
        assert decrypt_github_token(connection.access_token_encrypted) == "gho_plain_secret"
        assert queued == [connection.user_id]


@pytest.mark.asyncio
async def test_github_analyzer_filters_repos_and_creates_unverified_pool_items() -> None:
    with SessionLocal() as db:
        user = User(email="github-analyzer@example.com", hashed_password="unused")
        db.add(user)
        db.commit()
        user_id = user.id

        items = await analyze_repositories_to_pool_items(
            user_id,
            db,
            FakeGitHubAnalyzerClient(),
            FakeLLMService(),
            FakeEmbeddingService(),
        )
        db.commit()

        assert len(items) == 1
        stored = db.scalars(select(PoolItem)).all()
        assert len(stored) == 1
        item = stored[0]
        assert item.user_id == user_id
        assert item.source == PoolItemSource.GITHUB
        assert item.verified_by_user is False
        assert item.title == "cv-tailor-api"
        assert item.embedding is not None
        assert len(item.embedding) == EMBEDDING_DIMENSION
        assert item.technologies == ["FastAPI", "PostgreSQL"]


def test_github_sync_endpoint_queues_background_job_without_running_it_inline() -> None:
    headers = auth_headers("github-sync@example.com")
    queued: list[UUID] = []

    def fake_scheduler(background_tasks: BackgroundTasks, user_id: UUID) -> None:
        queued.append(user_id)

    app.dependency_overrides[get_github_sync_scheduler] = lambda: fake_scheduler

    response = client.post("/github/sync", headers=headers)

    assert response.status_code == 202
    assert response.json() == {"queued": True}
    assert len(queued) == 1
