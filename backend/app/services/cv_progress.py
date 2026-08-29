from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import RLock
from time import perf_counter
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.pipeline_run import PipelineRun

CV_GRAPH_STEPS = ["job_parser", "selector", "cvtailor", "evaluator", "typst_renderer"]
# How many recent finished runs the step-duration aggregate looks at.
METRICS_SAMPLE_SIZE = 500


class CVStepProgress(BaseModel):
    name: str
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None


class CVGenerationProgress(BaseModel):
    pipeline_id: UUID
    user_id: UUID
    status: str
    current_step: str | None = None
    steps: list[CVStepProgress] = Field(default_factory=list)
    job_id: UUID | None = None
    generated_cv_id: UUID | None = None
    selected_pool_item_ids: list[UUID] = Field(default_factory=list)
    output_language: str | None = None
    job_summary: str | None = None
    ats_score: float | None = None
    missing_keywords: list[str] = Field(default_factory=list)
    ats_recommendations: list[str] = Field(default_factory=list)
    before_after_diff: list[dict[str, object]] = Field(default_factory=list)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None


class CVProgressStore:
    """Pipeline progress, persisted so a restart or a second worker can read it.

    The pipeline itself runs in a FastAPI background task, so the process that
    started a run is not necessarily the one that serves the status poll. Only
    the monotonic clocks used for duration measurement stay in memory; if a run
    is resumed elsewhere the durations are simply reported as unknown.
    """

    def __init__(self) -> None:
        self._started_monotonic: dict[UUID, float] = {}
        self._step_started_monotonic: dict[tuple[UUID, str], float] = {}
        self._lock = RLock()

    def create(self, user_id: UUID) -> CVGenerationProgress:
        progress = CVGenerationProgress(
            pipeline_id=uuid4(),
            user_id=user_id,
            status="queued",
            steps=[CVStepProgress(name=name) for name in CV_GRAPH_STEPS],
        )
        with SessionLocal() as db:
            db.add(
                PipelineRun(
                    id=progress.pipeline_id,
                    user_id=user_id,
                    status=progress.status,
                    state=progress.model_dump(mode="json"),
                )
            )
            db.commit()
        return progress

    def get(self, pipeline_id: UUID, user_id: UUID) -> CVGenerationProgress | None:
        with SessionLocal() as db:
            run = self._load(db, pipeline_id)
            if run is None or run.user_id != user_id:
                return None

            progress = CVGenerationProgress.model_validate(run.state)
            if self._is_stale(run):
                progress.status = "failed"
                progress.current_step = None
                progress.error = "Pipeline yaniti alinamadi, calisma yarida kesildi."
                progress.completed_at = datetime.now(UTC)
                self._save(db, run, progress)
            return progress

    def _is_stale(self, run: PipelineRun) -> bool:
        if run.status not in ("queued", "running"):
            return False
        updated_at = run.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - updated_at > timedelta(seconds=settings.pipeline_stale_after_seconds)

    def mark_step_started(self, pipeline_id: UUID, step: str) -> None:
        now = datetime.now(UTC)
        with SessionLocal() as db:
            run = self._load(db, pipeline_id)
            if run is None:
                return
            progress = CVGenerationProgress.model_validate(run.state)

            if progress.started_at is None:
                progress.started_at = now
                with self._lock:
                    self._started_monotonic[pipeline_id] = perf_counter()
            progress.status = "running"
            progress.current_step = step
            with self._lock:
                self._step_started_monotonic[(pipeline_id, step)] = perf_counter()
            for item in progress.steps:
                if item.name == step:
                    item.status = "running"
                    item.started_at = item.started_at or now
                    break

            self._save(db, run, progress)

    def mark_step_completed(self, pipeline_id: UUID, step: str, **values: object) -> None:
        duration_ms = self._step_duration_ms(pipeline_id, step)
        self._update(pipeline_id, step_status=(step, "completed"), step_duration_ms=duration_ms, **values)

    def complete(self, pipeline_id: UUID, generated_cv_id: UUID) -> None:
        duration_ms = self._pipeline_duration_ms(pipeline_id)
        self._update(
            pipeline_id,
            status="completed",
            current_step=None,
            generated_cv_id=generated_cv_id,
            completed_at=datetime.now(UTC),
            duration_ms=duration_ms,
        )

    def fail(self, pipeline_id: UUID, error: str) -> None:
        duration_ms = self._pipeline_duration_ms(pipeline_id)
        self._update(pipeline_id, status="failed", error=error, completed_at=datetime.now(UTC), duration_ms=duration_ms)

    def metrics(self) -> dict[str, object]:
        step_durations: dict[str, list[float]] = {step: [] for step in CV_GRAPH_STEPS}
        statuses: dict[str, int] = {}

        with SessionLocal() as db:
            for status, count in db.execute(
                select(PipelineRun.status, func.count()).group_by(PipelineRun.status)
            ):
                statuses[status] = count

            # Only finished runs carry step durations worth aggregating, and the
            # recent ones are what a metrics scrape is actually about.
            for (state,) in db.execute(
                select(PipelineRun.state)
                .where(PipelineRun.status.in_(("completed", "failed")))
                .order_by(PipelineRun.updated_at.desc())
                .limit(METRICS_SAMPLE_SIZE)
            ):
                for step in state.get("steps", []):
                    duration = step.get("duration_ms")
                    if duration is not None:
                        step_durations.setdefault(step["name"], []).append(duration)

        return {
            "pipelines_total": sum(statuses.values()),
            "pipelines_by_status": statuses,
            "step_duration_ms": {
                name: {
                    "count": len(values),
                    "avg": round(sum(values) / len(values), 2) if values else None,
                    "max": round(max(values), 2) if values else None,
                }
                for name, values in step_durations.items()
            },
        }

    def _load(self, db: Session, pipeline_id: UUID) -> PipelineRun | None:
        return db.scalar(select(PipelineRun).where(PipelineRun.id == pipeline_id))

    def _save(self, db: Session, run: PipelineRun, progress: CVGenerationProgress) -> None:
        run.status = progress.status
        run.state = progress.model_dump(mode="json")
        db.commit()

    def _update(
        self,
        pipeline_id: UUID,
        *,
        step_status: tuple[str, str] | None = None,
        step_duration_ms: float | None = None,
        **values: object,
    ) -> None:
        with SessionLocal() as db:
            run = self._load(db, pipeline_id)
            if run is None:
                return
            progress = CVGenerationProgress.model_validate(run.state)

            if step_status is not None:
                step_name, status = step_status
                for step in progress.steps:
                    if step.name == step_name:
                        step.status = status
                        if status == "completed":
                            step.completed_at = datetime.now(UTC)
                            step.duration_ms = step_duration_ms
                        break
            for key, value in values.items():
                setattr(progress, key, value)

            self._save(db, run, progress)

    def _step_duration_ms(self, pipeline_id: UUID, step: str) -> float | None:
        with self._lock:
            started = self._step_started_monotonic.pop((pipeline_id, step), None)
        if started is None:
            return None
        return round((perf_counter() - started) * 1000, 2)

    def _pipeline_duration_ms(self, pipeline_id: UUID) -> float | None:
        with self._lock:
            started = self._started_monotonic.pop(pipeline_id, None)
        if started is None:
            return None
        return round((perf_counter() - started) * 1000, 2)


cv_progress_store = CVProgressStore()
