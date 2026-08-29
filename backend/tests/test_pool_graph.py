import asyncio
import time
from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import delete, select

from app.api.profile import get_pool_graph_scheduler
from app.core.config import EMBEDDING_DIMENSION, settings
from app.core.security import encrypt_github_token
from app.db.session import SessionLocal
from app.graphs.pool_graph import build_pool_graph
from app.main import app
from app.models.enums import PoolItemSource
from app.models.github_connection import GitHubConnection
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.github import GitHubRepoAnalysis
from app.schemas.pdf_import import PDFExtraction
from app.services.github import GitHubRepositorySignal

client = TestClient(app)


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        assert text.strip()
        return [0.75] * EMBEDDING_DIMENSION


class FakeLLMService:
    def __init__(self, events: list[tuple[str, float]]) -> None:
        self.events = events

    async def structured(self, prompt: str, response_model, *, system_prompt: str | None = None):
        assert system_prompt
        if response_model is PDFExtraction:
            self.events.append(("pdf_llm_start", time.perf_counter()))
            await asyncio.sleep(0.15)
            return response_model(
                items=[
                    {
                        "kind": "experience",
                        "title": "Backend Developer",
                        "raw_content": "Built FastAPI services with PostgreSQL.",
                        "tags": ["backend"],
                        "technologies": ["FastAPI", "PostgreSQL"],
                    }
                ]
            )

        return GitHubRepoAnalysis(
            area="backend",
            technologies=["FastAPI"],
            short_description="Built a FastAPI GitHub project.",
        )


class FakeGitHubClient:
    def __init__(self, token: str, events: list[tuple[str, float]]) -> None:
        assert token == "gho_graph_secret"
        self.events = events

    async def collect_repository_signals(self) -> list[GitHubRepositorySignal]:
        self.events.append(("github_collect_start", time.perf_counter()))
        await asyncio.sleep(0.15)
        return [
            GitHubRepositorySignal(
                name="cv-tailor-api",
                full_name="octocat/cv-tailor-api",
                html_url="https://github.com/octocat/cv-tailor-api",
                description="Production API",
                fork=False,
                topics=["fastapi"],
                languages={"Python": 1200},
                commit_count=7,
                readme="# API\nFastAPI project.",
            )
        ]


@pytest.fixture(autouse=True)
def clean_users_and_settings() -> Generator[None, None, None]:
    original_key = settings.github_token_encryption_key
    settings.github_token_encryption_key = Fernet.generate_key().decode("ascii")
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    app.dependency_overrides.clear()
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


def profile_payload(name: str) -> dict[str, object]:
    return {
        "full_name": name,
        "contact": {"email": f"{name.lower()}@example.com"},
        "education": [],
        "personal_info": {"summary": "Backend developer"},
    }


def sample_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 72 720 Td (Built FastAPI services with PostgreSQL.) Tj ET")
    page[NameObject("/Contents")] = content
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                        }
                    )
                }
            )
        }
    )
    from io import BytesIO

    data = BytesIO()
    writer.write(data)
    return data.getvalue()


@pytest.mark.asyncio
async def test_pool_graph_processes_pdf_and_github_in_parallel_to_pending_items() -> None:
    events: list[tuple[str, float]] = []
    with SessionLocal() as db:
        user = User(email="graph@example.com", hashed_password="unused")
        db.add(user)
        db.commit()
        db.add(
            GitHubConnection(
                user_id=user.id,
                github_username="octocat",
                access_token_encrypted=encrypt_github_token("gho_graph_secret"),
            )
        )
        db.commit()

        graph = build_pool_graph()
        state = await graph.ainvoke(
            {
                "user_id": user.id,
                "db": db,
                "llm_service": FakeLLMService(events),
                "embedding_service": FakeEmbeddingService(),
                "include_github": True,
                "pdf_bytes": sample_pdf_bytes(),
                "github_client_factory": lambda token: FakeGitHubClient(token, events),
            }
        )

        assert set(state["parallel_steps"]) == {"pdf_parser", "github_analyzer"}
        start_times = {name: started_at for name, started_at in events}
        assert abs(start_times["pdf_llm_start"] - start_times["github_collect_start"]) < 0.08
        assert state["pending_count"] == 2

        stored = db.scalars(select(PoolItem).order_by(PoolItem.source, PoolItem.title)).all()
        assert len(stored) == 2
        assert {item.source for item in stored} == {PoolItemSource.PDF, PoolItemSource.GITHUB}
        assert all(item.verified_by_user is False for item in stored)
        assert all(item.user_id == user.id for item in stored)
        assert all(item.embedding is not None and len(item.embedding) == EMBEDDING_DIMENSION for item in stored)


def test_profile_create_update_and_refresh_queue_pool_graph_background_job() -> None:
    queued: list[tuple[str, bool, bool]] = []

    def fake_scheduler(
        background_tasks: BackgroundTasks,
        user_id,
        pdf_bytes: bytes | None = None,
        include_github: bool = True,
    ) -> None:
        assert isinstance(background_tasks, BackgroundTasks)
        queued.append((str(user_id), pdf_bytes is not None, include_github))

    app.dependency_overrides[get_pool_graph_scheduler] = lambda: fake_scheduler
    headers = auth_headers("profile-graph@example.com")

    created = client.post("/profile", headers=headers, json=profile_payload("Graph User"))
    assert created.status_code == 201
    patched = client.patch("/profile", headers=headers, json={"full_name": "Graph Updated"})
    assert patched.status_code == 200
    refresh = client.post(
        "/profile/pool-refresh",
        headers=headers,
        data={"include_github": "true"},
        files={"file": ("cv.pdf", sample_pdf_bytes(), "application/pdf")},
    )
    assert refresh.status_code == 202
    assert refresh.json() == {"queued": True, "include_github": True, "has_pdf": True}

    assert len(queued) == 3
    assert queued[0][1:] == (False, True)
    assert queued[1][1:] == (False, True)
    assert queued[2][1:] == (True, True)
