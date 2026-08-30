from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.graphs.cv_graph import run_cv_graph_with_progress
from app.schemas.cv_generation import CVGenerationStartRequest, CVGenerationStartResponse, CVGenerationStatusResponse
from app.services.cv_progress import cv_progress_store
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.llm_credentials import LLMCredentialMissing, load_llm_service

router = APIRouter(prefix="/cv-generation", tags=["cv-generation"])
logger = logging.getLogger(__name__)


def get_llm_service(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> LLMService:
    # Every run is billed to the account that started it, so the key comes from
    # that user's own credential rather than a shared server key.
    try:
        return load_llm_service(db, current_user.id)
    except LLMCredentialMissing as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def _progress_values_from_state(state: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {
        "job_id": state.get("job_id"),
        "generated_cv_id": state.get("generated_cv_id"),
        "ats_score": state.get("ats_score"),
    }

    selected_items = state.get("selected_pool_items") or []
    values["selected_pool_item_ids"] = [item.pool_item_id for item in selected_items if hasattr(item, "pool_item_id")]

    output_language = state.get("output_language")
    if output_language is not None:
        values["output_language"] = getattr(output_language, "value", str(output_language))

    requirements = state.get("job_requirements")
    if requirements is not None:
        summary = _job_summary_from_requirements(requirements)
        if summary:
            values["job_summary"] = summary

    evaluation = state.get("ats_evaluation")
    if evaluation is not None:
        values["ats_score"] = evaluation.ats_score
        values["missing_keywords"] = evaluation.missing_keywords
        values["ats_recommendations"] = evaluation.recommendations
        values["before_after_diff"] = [item.model_dump() for item in evaluation.before_after_diff]

    return {key: value for key, value in values.items() if value is not None}


def _job_summary_from_requirements(requirements: Any) -> str:
    summary = str(getattr(requirements, "summary", "") or "").strip()
    if summary:
        return summary

    required = [str(item).strip() for item in getattr(requirements, "required_skills", []) if str(item).strip()]
    preferred = [str(item).strip() for item in getattr(requirements, "preferred_skills", []) if str(item).strip()]
    key_terms = [str(item).strip() for item in getattr(requirements, "key_terms", []) if str(item).strip()]
    parts = []
    if required:
        parts.append(f"Required: {', '.join(required[:8])}.")
    if preferred:
        parts.append(f"Preferred: {', '.join(preferred[:8])}.")
    years = getattr(requirements, "years_experience", None)
    if years is not None:
        parts.append(f"Experience: {years}+ years.")
    if key_terms:
        parts.append(f"Signals: {', '.join(key_terms[:8])}.")
    return " ".join(parts)


async def _run_pipeline_background(
    *,
    pipeline_id: UUID,
    user_id: UUID,
    user_email: str,
    payload: CVGenerationStartRequest,
    llm_service: LLMService,
    embedding_service: EmbeddingService,
) -> None:
    source_url = str(payload.source_url) if payload.source_url else None
    raw_text = payload.raw_text or ""
    try:
        logger.info(
            "pipeline_started",
            extra={"event": "pipeline_started", "pipeline_id": str(pipeline_id), "user_id": str(user_id)},
        )
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http_client:
            with SessionLocal() as db:
                def mark_started(step: str) -> None:
                    cv_progress_store.mark_step_started(pipeline_id, step)
                    logger.info(
                        "pipeline_step_started",
                        extra={
                            "event": "pipeline_step_started",
                            "pipeline_id": str(pipeline_id),
                            "user_id": str(user_id),
                            "step": step,
                        },
                    )

                def mark_completed(step: str, state: dict[str, Any]) -> None:
                    cv_progress_store.mark_step_completed(
                        pipeline_id,
                        step,
                        **_progress_values_from_state(state),
                    )
                    progress = cv_progress_store.get(pipeline_id, user_id)
                    step_progress = next((item for item in progress.steps if item.name == step), None) if progress else None
                    logger.info(
                        "pipeline_step_completed",
                        extra={
                            "event": "pipeline_step_completed",
                            "pipeline_id": str(pipeline_id),
                            "user_id": str(user_id),
                            "step": step,
                            "duration_ms": step_progress.duration_ms if step_progress else None,
                        },
                    )

                result = await run_cv_graph_with_progress(
                    user_id=user_id,
                    user_email=user_email,
                    db=db,
                    llm_service=llm_service,
                    embedding_service=embedding_service,
                    raw_text=raw_text,
                    source_url=source_url,
                    http_client=http_client,
                    on_step_started=mark_started,
                    on_step_completed=mark_completed,
                )
                generated_cv_id = result.get("generated_cv_id")
                if isinstance(generated_cv_id, UUID):
                    cv_progress_store.complete(pipeline_id, generated_cv_id)
                    progress = cv_progress_store.get(pipeline_id, user_id)
                    logger.info(
                        "pipeline_completed",
                        extra={
                            "event": "pipeline_completed",
                            "pipeline_id": str(pipeline_id),
                            "user_id": str(user_id),
                            "generated_cv_id": str(generated_cv_id),
                            "duration_ms": progress.duration_ms if progress else None,
                        },
                    )
    except Exception as exc:
        cv_progress_store.fail(pipeline_id, str(exc))
        logger.exception(
            "pipeline_failed",
            extra={"event": "pipeline_failed", "pipeline_id": str(pipeline_id), "user_id": str(user_id)},
        )


@router.post("", response_model=CVGenerationStartResponse, status_code=status.HTTP_202_ACCEPTED)
def start_cv_generation(
    payload: CVGenerationStartRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    llm_service: Annotated[LLMService, Depends(get_llm_service)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> CVGenerationStartResponse:
    # A stale run is only reclassified when it is read, so refuse on the live
    # counts rather than letting a hung run block the account forever.
    mine, total = cv_progress_store.active_counts(current_user.id)
    if mine >= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zaten calisan bir CV uretimi var. Bitmesini bekleyin.",
        )
    if total >= settings.pipeline_max_concurrent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sunucu su anda kapasitede. Birazdan tekrar deneyin.",
        )

    progress = cv_progress_store.create(current_user.id)
    background_tasks.add_task(
        _run_pipeline_background,
        pipeline_id=progress.pipeline_id,
        user_id=current_user.id,
        user_email=current_user.email,
        payload=payload,
        llm_service=llm_service,
        embedding_service=embedding_service,
    )
    return CVGenerationStartResponse(
        pipeline_id=progress.pipeline_id,
        status=progress.status,
        status_url=f"/cv-generation/{progress.pipeline_id}",
    )


@router.get("/{pipeline_id}", response_model=CVGenerationStatusResponse)
def read_cv_generation_status(pipeline_id: UUID, current_user: CurrentUser) -> CVGenerationStatusResponse:
    progress = cv_progress_store.get(pipeline_id, current_user.id)
    if progress is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline bulunamadi")
    return CVGenerationStatusResponse.model_validate(progress.model_dump())
