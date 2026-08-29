from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from time import perf_counter
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


CV_GRAPH_STEPS = ["job_parser", "selector", "cvtailor", "evaluator", "typst_renderer"]


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


@dataclass
class CVProgressStore:
    _items: dict[UUID, CVGenerationProgress] = field(default_factory=dict)
    _started_monotonic: dict[UUID, float] = field(default_factory=dict)
    _step_started_monotonic: dict[tuple[UUID, str], float] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def create(self, user_id: UUID) -> CVGenerationProgress:
        progress = CVGenerationProgress(
            pipeline_id=uuid4(),
            user_id=user_id,
            status="queued",
            steps=[CVStepProgress(name=name) for name in CV_GRAPH_STEPS],
        )
        with self._lock:
            self._items[progress.pipeline_id] = progress
        return progress

    def get(self, pipeline_id: UUID, user_id: UUID) -> CVGenerationProgress | None:
        with self._lock:
            progress = self._items.get(pipeline_id)
            if progress is None or progress.user_id != user_id:
                return None
            return progress.model_copy(deep=True)

    def mark_step_started(self, pipeline_id: UUID, step: str) -> None:
        now = datetime.now(UTC)
        with self._lock:
            progress = self._items.get(pipeline_id)
            if progress is None:
                return
            if progress.started_at is None:
                progress.started_at = now
                self._started_monotonic[pipeline_id] = perf_counter()
            progress.status = "running"
            progress.current_step = step
            self._step_started_monotonic[(pipeline_id, step)] = perf_counter()
            for item in progress.steps:
                if item.name == step:
                    item.status = "running"
                    item.started_at = item.started_at or now
                    break

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
        with self._lock:
            statuses: dict[str, int] = {}
            step_durations: dict[str, list[float]] = {step: [] for step in CV_GRAPH_STEPS}
            for progress in self._items.values():
                statuses[progress.status] = statuses.get(progress.status, 0) + 1
                for step in progress.steps:
                    if step.duration_ms is not None:
                        step_durations.setdefault(step.name, []).append(step.duration_ms)

            return {
                "pipelines_total": len(self._items),
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

    def _update(
        self,
        pipeline_id: UUID,
        *,
        step_status: tuple[str, str] | None = None,
        step_duration_ms: float | None = None,
        **values: object,
    ) -> None:
        with self._lock:
            progress = self._items.get(pipeline_id)
            if progress is None:
                return
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
