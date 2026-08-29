from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.pipeline_run import PipelineRun
from app.models.user import User
from app.services.cv_progress import CVProgressStore, cv_progress_store


@pytest.fixture(autouse=True)
def clean_users() -> Generator[None, None, None]:
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(User))
        db.commit()


def create_user(email: str = "pipeline-owner@example.com") -> User:
    with SessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password("strong-password"),
            kvkk_consent_at=datetime.now(UTC),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def test_progress_survives_a_new_store_instance() -> None:
    user = create_user()
    progress = cv_progress_store.create(user.id)

    cv_progress_store.mark_step_started(progress.pipeline_id, "job_parser")
    cv_progress_store.mark_step_completed(progress.pipeline_id, "job_parser", job_summary="Backend engineer")

    # A different instance stands in for another worker process or a restart:
    # nothing about the run may live only in the process that started it.
    other_worker = CVProgressStore()
    reloaded = other_worker.get(progress.pipeline_id, user.id)

    assert reloaded is not None
    assert reloaded.status == "running"
    assert reloaded.job_summary == "Backend engineer"
    assert [step.status for step in reloaded.steps if step.name == "job_parser"] == ["completed"]


def test_progress_is_scoped_to_its_owner() -> None:
    owner = create_user("owner@example.com")
    intruder = create_user("intruder@example.com")
    progress = cv_progress_store.create(owner.id)

    assert cv_progress_store.get(progress.pipeline_id, intruder.id) is None
    assert cv_progress_store.get(uuid4(), owner.id) is None


def test_completion_and_failure_are_persisted() -> None:
    user = create_user()
    completed = cv_progress_store.create(user.id)
    failed = cv_progress_store.create(user.id)
    generated_cv_id = uuid4()

    cv_progress_store.complete(completed.pipeline_id, generated_cv_id)
    cv_progress_store.fail(failed.pipeline_id, "LLM saglayicisi yanit vermedi")

    stored_completed = cv_progress_store.get(completed.pipeline_id, user.id)
    stored_failed = cv_progress_store.get(failed.pipeline_id, user.id)

    assert stored_completed is not None
    assert stored_completed.status == "completed"
    assert stored_completed.generated_cv_id == generated_cv_id
    assert stored_failed is not None
    assert stored_failed.status == "failed"
    assert stored_failed.error == "LLM saglayicisi yanit vermedi"


def test_abandoned_run_is_reported_as_failed() -> None:
    user = create_user()
    progress = cv_progress_store.create(user.id)
    cv_progress_store.mark_step_started(progress.pipeline_id, "job_parser")

    stale_moment = datetime.now(UTC) - timedelta(seconds=settings.pipeline_stale_after_seconds + 60)
    with SessionLocal() as db:
        # Raw SQL so the column's onupdate default does not stamp "now" back over it.
        db.execute(
            text("UPDATE pipeline_runs SET updated_at = :updated_at WHERE id = :id"),
            {"updated_at": stale_moment, "id": progress.pipeline_id},
        )
        db.commit()

    stored = cv_progress_store.get(progress.pipeline_id, user.id)

    assert stored is not None
    assert stored.status == "failed"
    assert stored.error


def test_runs_are_removed_with_their_owner() -> None:
    user = create_user()
    progress = cv_progress_store.create(user.id)

    with SessionLocal() as db:
        db.execute(delete(User).where(User.id == user.id))
        db.commit()

    with SessionLocal() as db:
        assert db.scalar(select(PipelineRun).where(PipelineRun.id == progress.pipeline_id)) is None
