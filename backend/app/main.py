from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable

from fastapi import FastAPI, Request, Response
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.cv_generation import router as cv_generation_router
from app.api.github import router as github_router
from app.api.generated_cvs import router as generated_cvs_router
from app.api.jobs import router as jobs_router
from app.api.kvkk import router as kvkk_router
from app.api.pool import router as pool_router
from app.api.pdf_import import router as pdf_import_router
from app.api.pool_items import router as pool_items_router
from app.api.profile import router as profile_router
from app.core.config import settings
from app.core.logging import configure_sensitive_logging
from app.db.session import SessionLocal
from app.services.cv_progress import cv_progress_store
from app.services.render_queue import render_queue_metrics

configure_sensitive_logging(json_logs=settings.log_format == "json", log_level=settings.log_level)
app = FastAPI(title="CV-Tailor API")
logger = logging.getLogger(__name__)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round((perf_counter() - started_at) * 1000, 2)
    logger.info(
        "request_completed",
        extra={
            "event": "request_completed",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


app.include_router(kvkk_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(pool_router)
app.include_router(pool_items_router)
app.include_router(pdf_import_router)
app.include_router(github_router)
app.include_router(jobs_router)
app.include_router(generated_cvs_router)
app.include_router(cv_generation_router)


@app.get("/health")
def health() -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        logger.exception("health_check_failed", extra={"event": "health_check_failed", "check": "database"})

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


@app.get("/metrics")
def metrics() -> dict[str, object]:
    return {
        "status": "ok",
        "pipelines": cv_progress_store.metrics(),
        "render_queue": render_queue_metrics.snapshot(),
    }
