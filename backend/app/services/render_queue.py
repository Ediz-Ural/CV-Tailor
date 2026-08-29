from pathlib import Path
from threading import RLock
from time import perf_counter
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.generated_cv import GeneratedCV
from app.render.typst import TypstRenderer


class RenderQueueMetrics:
    def __init__(self) -> None:
        self._lock = RLock()
        self.queued_total = 0
        self.running = 0
        self.completed_total = 0
        self.failed_total = 0
        self.duration_ms: list[float] = []

    def start(self) -> float:
        with self._lock:
            self.queued_total += 1
            self.running += 1
        return perf_counter()

    def complete(self, started_at: float) -> None:
        with self._lock:
            self.running = max(0, self.running - 1)
            self.completed_total += 1
            self.duration_ms.append(round((perf_counter() - started_at) * 1000, 2))

    def fail(self, started_at: float) -> None:
        with self._lock:
            self.running = max(0, self.running - 1)
            self.failed_total += 1
            self.duration_ms.append(round((perf_counter() - started_at) * 1000, 2))

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            values = list(self.duration_ms)
            return {
                "queued_total": self.queued_total,
                "running": self.running,
                "completed_total": self.completed_total,
                "failed_total": self.failed_total,
                "duration_ms": {
                    "count": len(values),
                    "avg": round(sum(values) / len(values), 2) if values else None,
                    "max": round(max(values), 2) if values else None,
                },
            }


render_queue_metrics = RenderQueueMetrics()


def render_generated_cv_task(generated_cv_id: UUID, *, renderer: TypstRenderer | None = None) -> None:
    started_at = render_queue_metrics.start()
    renderer = renderer or TypstRenderer()
    try:
        with SessionLocal() as db:
            generated_cv = db.scalar(select(GeneratedCV).where(GeneratedCV.id == generated_cv_id))
            if generated_cv is None or not generated_cv.typst_source:
                render_queue_metrics.complete(started_at)
                return

            pdf_path = renderer.render_pdf(
                typst_source=generated_cv.typst_source,
                generated_cv_id=generated_cv.id,
            )
            generated_cv.pdf_path = str(Path(pdf_path))
            db.commit()
        render_queue_metrics.complete(started_at)
    except Exception:
        render_queue_metrics.fail(started_at)
        raise
