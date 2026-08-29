from collections.abc import Generator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem
from app.graphs.nodes.evaluator import evaluator_node, semantic_keyword_lemmas
from app.graphs.nodes.selector import SelectedPoolItem
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.job import JobRequirementExtraction


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


def create_job(
    db: Session,
    user: User,
    *,
    raw_text: str,
    language: ContentLanguage,
    requirements: JobRequirementExtraction,
) -> Job:
    job = Job(
        user_id=user.id,
        raw_text=raw_text,
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
    technologies: list[str],
    language: ContentLanguage = ContentLanguage.EN,
) -> PoolItem:
    item = PoolItem(
        user_id=user.id,
        source=PoolItemSource.MANUAL,
        type=PoolItemType.PROJECT,
        title=title,
        raw_content=raw_content,
        tags=[],
        technologies=technologies,
        language=language,
        embedding=None,
        verified_by_user=True,
    )
    db.add(item)
    db.flush()
    return item


@pytest.mark.asyncio
async def test_evaluator_scores_good_match_high_and_outputs_diff() -> None:
    with SessionLocal() as db:
        user = create_user(db, "evaluator-good@example.com")
        job = create_job(
            db,
            user,
            raw_text="Backend engineer with FastAPI, PostgreSQL, and API experience.",
            language=ContentLanguage.EN,
            requirements=JobRequirementExtraction(
                required_skills=["FastAPI", "PostgreSQL"],
                preferred_skills=["Docker"],
                key_terms=["API"],
            ),
        )
        item = create_pool_item(
            db,
            user,
            title="Backend API",
            raw_content="Built API services with FastAPI and PostgreSQL.",
            technologies=["FastAPI", "PostgreSQL", "Docker"],
        )
        tailored = TailoredCVContent(
            output_language=ContentLanguage.EN,
            summary="Backend engineer with FastAPI, PostgreSQL, Docker, and API delivery.",
            projects=[
                TailoredCVItem(
                    source_pool_item_id=item.id,
                    title="Backend API",
                    content="Delivered API services using FastAPI, PostgreSQL, and Docker.",
                    technologies=["FastAPI", "PostgreSQL", "Docker"],
                )
            ],
        )
        db.commit()

        state = await evaluator_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.95)],
                "tailored_cv": tailored,
            }
        )

        evaluation = state["ats_evaluation"]
        assert evaluation.ats_score == 100.0
        assert state["ats_score"] == 100.0
        assert evaluation.missing_keywords == []
        assert evaluation.before_after_diff[0].before == item.raw_content
        assert "Delivered API services" in evaluation.before_after_diff[0].after
        assert "--- pool_item" in evaluation.before_after_diff[0].diff


@pytest.mark.asyncio
async def test_evaluator_lists_missing_keywords_for_absent_skills() -> None:
    with SessionLocal() as db:
        user = create_user(db, "evaluator-missing@example.com")
        job = create_job(
            db,
            user,
            raw_text="We need FastAPI, Kubernetes, and React experience.",
            language=ContentLanguage.EN,
            requirements=JobRequirementExtraction(
                required_skills=["FastAPI", "Kubernetes"],
                preferred_skills=["React"],
            ),
        )
        item = create_pool_item(
            db,
            user,
            title="FastAPI service",
            raw_content="Built FastAPI services.",
            technologies=["FastAPI"],
        )
        tailored = TailoredCVContent(
            output_language=ContentLanguage.EN,
            summary="FastAPI backend service experience.",
            projects=[
                TailoredCVItem(
                    source_pool_item_id=item.id,
                    title="FastAPI service",
                    content="Built FastAPI services for backend APIs.",
                    technologies=["FastAPI"],
                )
            ],
        )
        db.commit()

        state = await evaluator_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.9)],
                "tailored_cv": tailored,
            }
        )

        evaluation = state["ats_evaluation"]
        assert evaluation.ats_score < 100.0
        assert evaluation.missing_keywords == ["Kubernetes", "React"]
        assert state["missing_keywords"] == ["Kubernetes", "React"]


@pytest.mark.asyncio
async def test_evaluator_matches_turkish_root_variants_without_exact_string() -> None:
    with SessionLocal() as db:
        user = create_user(db, "evaluator-tr@example.com")
        job = create_job(
            db,
            user,
            raw_text="Backend gelistirici araniyor.",
            language=ContentLanguage.TR,
            requirements=JobRequirementExtraction(required_skills=["geli\u015ftirici"], key_terms=["backend"]),
        )
        item = create_pool_item(
            db,
            user,
            title="Backend deneyimi",
            raw_content="Backend servisleri gelistiren ekipte calistim.",
            technologies=[],
            language=ContentLanguage.TR,
        )
        tailored = TailoredCVContent(
            output_language=ContentLanguage.TR,
            summary="Backend servisleri geli\u015ftiren deneyim.",
            experience=[
                TailoredCVItem(
                    source_pool_item_id=item.id,
                    title="Backend deneyimi",
                    content="Backend servisleri geli\u015ftiren projelerde gorev aldi.",
                    technologies=[],
                )
            ],
        )
        db.commit()

        state = await evaluator_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.91)],
                "tailored_cv": tailored,
            }
        )

        evaluation = state["ats_evaluation"]
        assert evaluation.ats_score == 100.0
        assert evaluation.missing_keywords == []
        assert "gelistirici" not in tailored.experience[0].content.casefold()
        assert semantic_keyword_lemmas("geli\u015ftirici") & semantic_keyword_lemmas("geli\u015ftiren")
