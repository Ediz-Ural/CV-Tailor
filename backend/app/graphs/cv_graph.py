from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict
from uuid import UUID

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graphs.nodes.cvtailor import TailoredCVContent, cvtailor_node
from app.graphs.nodes.evaluator import ATSEvaluation, evaluator_node
from app.graphs.nodes.selector import SelectedPoolItem, SelectorCandidate, selector_node
from app.models.enums import ContentLanguage
from app.models.generated_cv import GeneratedCV
from app.models.job import Job
from app.models.profile import Profile
from app.render.typst import build_typst_source
from app.services.embeddings import EmbeddingService
from app.schemas.job import JobRequirementExtraction
from app.services.job_parser import JobParser, fetch_single_job_page
from app.services.llm import LLMService
from app.services.render_queue import render_generated_cv_task


class CVGraphState(TypedDict, total=False):
    user_id: UUID
    user_email: str
    raw_text: str
    source_url: str | None
    job_id: UUID
    db: Session
    llm_service: LLMService
    embedding_service: EmbeddingService
    http_client: httpx.AsyncClient
    render_enqueue: Callable[[UUID], None]
    selected_pool_items: list[SelectedPoolItem]
    semantic_candidates: list[SelectorCandidate]
    job_requirements: JobRequirementExtraction
    tailored_cv: TailoredCVContent | None
    output_language: ContentLanguage
    ats_evaluation: ATSEvaluation
    ats_score: float
    generated_cv_id: UUID
    generated_cv: GeneratedCV


def _contact_values(profile: Profile | None, fallback_email: str) -> list[str]:
    contact = profile.contact if profile and isinstance(profile.contact, dict) else {}
    values = [contact.get(key) for key in ("email", "phone", "location", "website", "github", "linkedin")]
    result = [str(value).strip() for value in values if str(value or "").strip()]
    return result or [fallback_email]


def _display_name(profile: Profile | None, fallback_email: str) -> str:
    if profile and profile.full_name:
        return profile.full_name
    return fallback_email.split("@", 1)[0]


async def job_parser_node(state: CVGraphState) -> dict[str, object]:
    source_url = state.get("source_url")
    raw_text = state.get("raw_text") or ""
    if source_url:
        raw_text = await fetch_single_job_page(source_url, state["http_client"])

    language, requirements = await JobParser(state["llm_service"]).parse(raw_text)
    job = Job(
        user_id=state["user_id"],
        source_url=source_url,
        raw_text=raw_text,
        detected_language=ContentLanguage(language),
        parsed_requirements_json=requirements.model_dump(),
    )
    db = state["db"]
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "raw_text": raw_text,
        "job_id": job.id,
        "job_requirements": requirements,
    }


async def typst_renderer_node(state: CVGraphState) -> dict[str, object]:
    db = state["db"]
    profile = db.scalar(select(Profile).where(Profile.user_id == state["user_id"]))
    tailored_cv = state.get("tailored_cv")
    if tailored_cv is None:
        tailored_cv = TailoredCVContent(output_language=state.get("output_language") or ContentLanguage.EN)

    typst_source = build_typst_source(
        tailored_cv=tailored_cv,
        name=_display_name(profile, state["user_email"]),
        contact=_contact_values(profile, state["user_email"]),
        education=profile.education if profile else [],
    )
    generated_cv = GeneratedCV(
        user_id=state["user_id"],
        job_id=state["job_id"],
        selected_pool_item_ids=[item.pool_item_id for item in state.get("selected_pool_items", [])],
        output_language=tailored_cv.output_language,
        typst_source=typst_source,
        ats_score=state.get("ats_score"),
    )
    db.add(generated_cv)
    db.commit()
    db.refresh(generated_cv)

    render_enqueue = state.get("render_enqueue") or render_generated_cv_task
    render_enqueue(generated_cv.id)
    db.refresh(generated_cv)
    return {"generated_cv_id": generated_cv.id, "generated_cv": generated_cv}


def build_cv_graph() -> Any:
    graph = StateGraph(CVGraphState)
    graph.add_node("job_parser", job_parser_node)
    graph.add_node("selector", selector_node)
    graph.add_node("cvtailor", cvtailor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("typst_renderer", typst_renderer_node)

    graph.set_entry_point("job_parser")
    graph.add_edge("job_parser", "selector")
    graph.add_edge("selector", "cvtailor")
    graph.add_edge("cvtailor", "evaluator")
    graph.add_edge("evaluator", "typst_renderer")
    graph.add_edge("typst_renderer", END)
    return graph.compile()


cv_graph = build_cv_graph()


async def run_cv_graph(
    *,
    user_id: UUID,
    user_email: str,
    db: Session,
    llm_service: LLMService,
    embedding_service: EmbeddingService,
    raw_text: str = "",
    source_url: str | None = None,
    http_client: httpx.AsyncClient,
    render_enqueue: Callable[[UUID], None] | None = None,
) -> CVGraphState:
    initial_state: CVGraphState = {
        "user_id": user_id,
        "user_email": user_email,
        "raw_text": raw_text,
        "source_url": source_url,
        "db": db,
        "llm_service": llm_service,
        "embedding_service": embedding_service,
        "http_client": http_client,
    }
    if render_enqueue is not None:
        initial_state["render_enqueue"] = render_enqueue
    return await cv_graph.ainvoke(initial_state)


async def run_cv_graph_with_progress(
    *,
    user_id: UUID,
    user_email: str,
    db: Session,
    llm_service: LLMService,
    embedding_service: EmbeddingService,
    raw_text: str = "",
    source_url: str | None = None,
    http_client: httpx.AsyncClient,
    render_enqueue: Callable[[UUID], None] | None = None,
    on_step_started: Callable[[str], None] | None = None,
    on_step_completed: Callable[[str, CVGraphState], None] | None = None,
) -> CVGraphState:
    initial_state: CVGraphState = {
        "user_id": user_id,
        "user_email": user_email,
        "raw_text": raw_text,
        "source_url": source_url,
        "db": db,
        "llm_service": llm_service,
        "embedding_service": embedding_service,
        "http_client": http_client,
    }
    if render_enqueue is not None:
        initial_state["render_enqueue"] = render_enqueue

    ordered_steps = ["job_parser", "selector", "cvtailor", "evaluator", "typst_renderer"]
    state: CVGraphState = dict(initial_state)
    if on_step_started is not None:
        on_step_started(ordered_steps[0])

    async for update in cv_graph.astream(initial_state, stream_mode="updates"):
        for step_name, partial in update.items():
            if isinstance(partial, dict):
                state.update(partial)
            if on_step_completed is not None:
                on_step_completed(step_name, state)
            step_index = ordered_steps.index(step_name)
            if on_step_started is not None and step_index + 1 < len(ordered_steps):
                on_step_started(ordered_steps[step_index + 1])

    return state
