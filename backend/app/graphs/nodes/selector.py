import re
from typing import Any, Protocol, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.pool_item import PoolItem
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMError, LLMService


class SelectedPoolItem(BaseModel):
    pool_item_id: UUID
    score: float = Field(ge=0.0, le=1.0)


class SelectorRanking(BaseModel):
    selected_items: list[SelectedPoolItem] = Field(default_factory=list, max_length=20)

    @field_validator("selected_items")
    @classmethod
    def keep_first_score_per_item(cls, value: list[SelectedPoolItem]) -> list[SelectedPoolItem]:
        seen: set[UUID] = set()
        deduped: list[SelectedPoolItem] = []
        for item in value:
            if item.pool_item_id not in seen:
                deduped.append(item)
                seen.add(item.pool_item_id)
        return deduped


class SelectorCandidate(BaseModel):
    pool_item_id: UUID
    semantic_score: float = Field(ge=0.0, le=1.0)
    title: str | None
    raw_content: str
    language: str
    technologies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SelectorState(TypedDict, total=False):
    user_id: UUID
    job_id: UUID
    db: Session
    llm_service: LLMService
    embedding_service: EmbeddingService
    candidate_limit: int
    selection_limit: int
    semantic_candidates: list[SelectorCandidate]
    selected_pool_items: list[SelectedPoolItem]


class StructuredLLM(Protocol):
    async def structured(
        self,
        prompt: str,
        response_model: type[SelectorRanking],
        *,
        system_prompt: str | None = None,
    ) -> SelectorRanking: ...


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


def selector_query_text(job: Job) -> str:
    requirements = job.parsed_requirements_json or {}
    parts: list[str] = []
    for key in ("required_skills", "preferred_skills", "key_terms"):
        values = requirements.get(key)
        if isinstance(values, list):
            parts.extend(str(value) for value in values if str(value).strip())
    years = requirements.get("years_experience")
    if years is not None:
        parts.append(f"{years} years experience")

    if not parts:
        parts.append(job.raw_text)
    return "\n".join(parts)


def turkish_light_lemmas(text: str) -> set[str]:
    """Small Turkish fallback stemmer for explanations/tests; ranking stays semantic."""
    normalized = text.casefold().translate(str.maketrans("çğıöşü", "cgiosu"))
    stems: set[str] = set()
    suffixes = (
        "lerinin",
        "larinin",
        "lerinin",
        "lerinden",
        "lardan",
        "lerden",
        "lari",
        "leri",
        "ici",
        "ici",
        "ci",
        "ci",
        "me",
        "ma",
        "mek",
        "mak",
        "en",
        "an",
    )
    for word in re.findall(r"[a-z]+", normalized):
        stem = word
        for suffix in suffixes:
            if len(stem) > len(suffix) + 3 and stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        stems.add(stem)
    return stems


def _semantic_statement(user_id: UUID, query_embedding: list[float], limit: int) -> Select[tuple[PoolItem, float]]:
    distance = PoolItem.embedding.cosine_distance(query_embedding).label("distance")
    return (
        select(PoolItem, distance)
        .where(
            PoolItem.user_id == user_id,
            PoolItem.verified_by_user.is_(True),
            PoolItem.embedding.is_not(None),
        )
        .order_by(distance, PoolItem.created_at, PoolItem.id)
        .limit(limit)
    )


def _semantic_score(distance: Any) -> float:
    value = 1.0 - float(distance)
    return max(0.0, min(1.0, value))


def semantic_candidates_for_job(
    db: Session,
    user_id: UUID,
    job: Job,
    embedding_service: EmbeddingProvider,
    *,
    limit: int = 12,
) -> list[SelectorCandidate]:
    query_embedding = embedding_service.embed(selector_query_text(job))
    rows = db.execute(_semantic_statement(user_id, query_embedding, limit)).all()
    return [
        SelectorCandidate(
            pool_item_id=item.id,
            semantic_score=_semantic_score(distance),
            title=item.title,
            raw_content=item.raw_content,
            language=item.language.value,
            technologies=item.technologies,
            tags=item.tags,
        )
        for item, distance in rows
    ]


def _selection_prompt(job: Job, candidates: list[SelectorCandidate], selection_limit: int) -> str:
    requirements = job.parsed_requirements_json or {}
    candidate_lines = []
    for candidate in candidates:
        candidate_lines.append(
            {
                "pool_item_id": str(candidate.pool_item_id),
                "semantic_score": round(candidate.semantic_score, 4),
                "title": candidate.title,
                "language": candidate.language,
                "technologies": candidate.technologies,
                "tags": candidate.tags,
                "raw_content": candidate.raw_content[:1200],
            }
        )
    return (
        "Rank the most relevant verified pool items for this job. "
        "Use semantic relevance, not exact keyword matching. Language differences must not disqualify an item. "
        "Return at most "
        f"{selection_limit} items, with scores from 0 to 1.\n\n"
        f"Job language: {job.detected_language.value}\n"
        f"Job requirements JSON: {requirements}\n"
        f"Candidates: {candidate_lines}"
    )


async def rerank_candidates_with_llm(
    llm_service: StructuredLLM,
    job: Job,
    candidates: list[SelectorCandidate],
    *,
    selection_limit: int = 5,
) -> list[SelectedPoolItem]:
    if not candidates:
        return []

    ranking = await llm_service.structured(
        _selection_prompt(job, candidates, selection_limit),
        SelectorRanking,
        system_prompt=(
            "You are the Selector node for CV-Tailor. Select only from candidate IDs. "
            "Prefer factual relevance to the job requirements. Do not require matching language."
        ),
    )
    candidate_scores = {candidate.pool_item_id: candidate.semantic_score for candidate in candidates}
    selected = []
    for item in ranking.selected_items:
        if item.pool_item_id in candidate_scores:
            selected.append(
                SelectedPoolItem(
                    pool_item_id=item.pool_item_id,
                    score=max(0.0, min(1.0, (item.score + candidate_scores[item.pool_item_id]) / 2)),
                )
            )
        if len(selected) >= selection_limit:
            break
    return selected


async def selector_node(state: SelectorState) -> dict[str, object]:
    db = state["db"]
    user_id = state["user_id"]
    job = db.scalar(select(Job).where(Job.id == state["job_id"], Job.user_id == user_id))
    if job is None:
        return {"semantic_candidates": [], "selected_pool_items": []}

    candidate_limit = state.get("candidate_limit", 12)
    selection_limit = state.get("selection_limit", 5)
    candidates = semantic_candidates_for_job(
        db,
        user_id,
        job,
        state["embedding_service"],
        limit=candidate_limit,
    )
    try:
        selected = await rerank_candidates_with_llm(
            state["llm_service"],
            job,
            candidates,
            selection_limit=selection_limit,
        )
    except LLMError:
        selected = [
            SelectedPoolItem(pool_item_id=candidate.pool_item_id, score=candidate.semantic_score)
            for candidate in candidates[:selection_limit]
        ]

    return {"semantic_candidates": candidates, "selected_pool_items": selected}
