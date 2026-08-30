from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import EMBEDDING_DIMENSION
from app.db.session import SessionLocal
from app.graphs.nodes.selector import (
    SelectedPoolItem,
    SelectorCandidate,
    SelectorRanking,
    rerank_candidates_with_llm,
    selector_node,
    turkish_light_lemmas,
)
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.job import JobRequirementExtraction


def unit_vector(index: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSION
    vector[index] = 1.0
    return vector


class FakeEmbeddingService:
    def embed(self, text: str) -> list[float]:
        normalized = text.casefold()
        if any(term in normalized for term in ("gelistirici", "geliştirici", "fastapi", "backend")):
            return unit_vector(0)
        if "react" in normalized:
            return unit_vector(1)
        return unit_vector(2)


class FakeLLMService:
    def __init__(self) -> None:
        self.seen_prompts: list[str] = []

    async def structured(
        self,
        prompt: str,
        response_model: type[SelectorRanking],
        *,
        system_prompt: str | None = None,
    ) -> SelectorRanking:
        assert response_model is SelectorRanking
        assert system_prompt is not None
        self.seen_prompts.append(prompt)
        candidates = []
        for marker in prompt.split("'pool_item_id': '")[1:]:
            candidates.append(UUID(marker.split("'", 1)[0]))
        return SelectorRanking(
            selected_items=[
                SelectedPoolItem(pool_item_id=candidate_id, score=0.95 - index * 0.1)
                for index, candidate_id in enumerate(candidates[:3])
            ]
        )


@pytest.fixture(autouse=True)
def clean_users() -> Generator[None, None, None]:
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def create_user(db: Session, email: str) -> User:
    user = User(email=email, hashed_password="unused")
    db.add(user)
    db.flush()
    return user


def create_job(db: Session, user: User, requirements: JobRequirementExtraction, language: ContentLanguage) -> Job:
    job = Job(
        user_id=user.id,
        raw_text="Backend gelistirici araniyor. FastAPI ve API gelistirme deneyimi gerekli.",
        detected_language=language,
        parsed_requirements_json=requirements.model_dump(),
    )
    db.add(job)
    db.flush()
    return job


def create_pool_item(
    db: Session,
    user: User,
    *,
    title: str,
    raw_content: str,
    embedding: list[float],
    verified: bool,
    language: ContentLanguage,
) -> PoolItem:
    item = PoolItem(
        user_id=user.id,
        source=PoolItemSource.MANUAL,
        type=PoolItemType.PROJECT,
        title=title,
        raw_content=raw_content,
        tags=[],
        technologies=["FastAPI"] if "FastAPI" in raw_content else [],
        language=language,
        embedding=embedding,
        verified_by_user=verified,
    )
    db.add(item)
    db.flush()
    return item


@pytest.mark.asyncio
async def test_selector_returns_ranked_ids_and_scores_for_verified_pool_items_only() -> None:
    with SessionLocal() as db:
        user = create_user(db, "selector@example.com")
        job = create_job(
            db,
            user,
            JobRequirementExtraction(required_skills=["FastAPI"], key_terms=["backend"]),
            ContentLanguage.EN,
        )
        verified = create_pool_item(
            db,
            user,
            title="Verified backend",
            raw_content="FastAPI backend API gelistirme projesi.",
            embedding=unit_vector(0),
            verified=True,
            language=ContentLanguage.TR,
        )
        unverified = create_pool_item(
            db,
            user,
            title="Unverified backend",
            raw_content="FastAPI backend API gelistirme projesi.",
            embedding=unit_vector(0),
            verified=False,
            language=ContentLanguage.TR,
        )
        unrelated = create_pool_item(
            db,
            user,
            title="Frontend",
            raw_content="React UI work.",
            embedding=unit_vector(1),
            verified=True,
            language=ContentLanguage.EN,
        )
        db.commit()

        state = await selector_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "llm_service": FakeLLMService(),
                "embedding_service": FakeEmbeddingService(),
                "candidate_limit": 3,
                "selection_limit": 2,
            }
        )

        selected = state["selected_pool_items"]
        selected_ids = [item.pool_item_id for item in selected]
        assert selected_ids[0] == verified.id
        assert unverified.id not in selected_ids
        assert all(0.0 <= item.score <= 1.0 for item in selected)
        assert {candidate.pool_item_id for candidate in state["semantic_candidates"]} == {verified.id, unrelated.id}


@pytest.mark.asyncio
async def test_selector_matches_cross_language_turkish_root_variants_semantically_not_exact_string() -> None:
    with SessionLocal() as db:
        user = create_user(db, "selector-mixed@example.com")
        other_user = create_user(db, "selector-other@example.com")
        job = create_job(
            db,
            user,
            JobRequirementExtraction(required_skills=["backend gelistirici"], key_terms=["FastAPI"]),
            ContentLanguage.EN,
        )
        turkish_pool_item = create_pool_item(
            db,
            user,
            title="TR API project",
            raw_content="FastAPI ile odeme API gelistirme ve PostgreSQL entegrasyonu yaptim.",
            embedding=unit_vector(0),
            verified=True,
            language=ContentLanguage.TR,
        )
        other_user_item = create_pool_item(
            db,
            other_user,
            title="Other tenant backend",
            raw_content="FastAPI backend gelistirme.",
            embedding=unit_vector(0),
            verified=True,
            language=ContentLanguage.TR,
        )
        db.commit()

        state = await selector_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "llm_service": FakeLLMService(),
                "embedding_service": FakeEmbeddingService(),
                "candidate_limit": 5,
                "selection_limit": 3,
            }
        )

        selected_ids = [item.pool_item_id for item in state["selected_pool_items"]]
        assert selected_ids == [turkish_pool_item.id]
        assert other_user_item.id not in selected_ids
        assert "gelistirici" not in turkish_pool_item.raw_content.casefold()
        assert turkish_light_lemmas("gelistirici") & turkish_light_lemmas("gelistirme")


@pytest.mark.asyncio
async def test_selector_returns_empty_for_missing_or_other_users_job() -> None:
    with SessionLocal() as db:
        first = create_user(db, "selector-first@example.com")
        second = create_user(db, "selector-second@example.com")
        job = create_job(
            db,
            first,
            JobRequirementExtraction(required_skills=["FastAPI"]),
            ContentLanguage.EN,
        )
        db.commit()

        state = await selector_node(
            {
                "user_id": second.id,
                "job_id": job.id,
                "db": db,
                "llm_service": FakeLLMService(),
                "embedding_service": FakeEmbeddingService(),
            }
        )

        assert state == {"semantic_candidates": [], "selected_pool_items": []}


class RankingLLM:
    def __init__(self, ranking: SelectorRanking) -> None:
        self.ranking = ranking

    async def structured(self, prompt: str, response_model, *, system_prompt: str | None = None):
        assert response_model is SelectorRanking
        self.prompt = prompt
        return self.ranking


def _candidate(score: float) -> SelectorCandidate:
    return SelectorCandidate(
        pool_item_id=uuid4(),
        semantic_score=score,
        title="Project",
        language="en",
        technologies=[],
        tags=[],
        raw_content="Some work.",
    )


@pytest.mark.asyncio
async def test_off_field_items_are_dropped_instead_of_filling_the_slots() -> None:
    """The limit is a cap, not a quota.

    With a portfolio spanning several fields the model happily returned five
    items for every posting, so an AI role came back with frontend projects
    attached.
    """
    relevant = [_candidate(0.9), _candidate(0.88)]
    filler = [_candidate(0.86), _candidate(0.85), _candidate(0.84)]
    llm = RankingLLM(
        SelectorRanking(
            selected_items=[
                SelectedPoolItem(pool_item_id=relevant[0].pool_item_id, score=0.95),
                SelectedPoolItem(pool_item_id=relevant[1].pool_item_id, score=0.80),
                SelectedPoolItem(pool_item_id=filler[0].pool_item_id, score=0.20),
                SelectedPoolItem(pool_item_id=filler[1].pool_item_id, score=0.15),
                SelectedPoolItem(pool_item_id=filler[2].pool_item_id, score=0.10),
            ]
        )
    )

    selected = await rerank_candidates_with_llm(
        llm, _selector_job(), [*relevant, *filler], selection_limit=5, min_relevance=0.45
    )

    assert [item.pool_item_id for item in selected] == [c.pool_item_id for c in relevant]


@pytest.mark.asyncio
async def test_the_best_item_is_kept_when_nothing_clears_the_floor() -> None:
    # An empty CV helps nobody; the ATS score is what reports the poor fit.
    candidates = [_candidate(0.7), _candidate(0.6)]
    llm = RankingLLM(
        SelectorRanking(
            selected_items=[
                SelectedPoolItem(pool_item_id=candidates[0].pool_item_id, score=0.20),
                SelectedPoolItem(pool_item_id=candidates[1].pool_item_id, score=0.10),
            ]
        )
    )

    selected = await rerank_candidates_with_llm(
        llm, _selector_job(), candidates, selection_limit=5, min_relevance=0.45
    )

    assert [item.pool_item_id for item in selected] == [candidates[0].pool_item_id]


def _selector_job() -> Job:
    return Job(
        id=uuid4(),
        user_id=uuid4(),
        raw_text="AI Engineer role.",
        detected_language=ContentLanguage.EN,
        parsed_requirements_json={"required_skills": ["Python"], "preferred_skills": [], "key_terms": []},
    )
