from collections.abc import Generator

from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.graphs.nodes.cvtailor import (
    CVTailorFabricationError,
    TailoredCVContent,
    TailoredCVDraft,
    TailoredCVDraftItem,
    TailoredCVItem,
    cvtailor_node,
    validate_no_fabrication,
)
from app.graphs.nodes.selector import SelectedPoolItem
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.job import JobRequirementExtraction
from app.db.session import SessionLocal


class FakeCVTailorLLM:
    def __init__(self, draft: TailoredCVDraft) -> None:
        self.draft = draft
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []

    async def structured(
        self,
        prompt: str,
        response_model: type[TailoredCVDraft],
        *,
        system_prompt: str | None = None,
    ) -> TailoredCVDraft:
        assert response_model is TailoredCVDraft
        assert system_prompt is not None
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        return self.draft


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
    item_type: PoolItemType,
    language: ContentLanguage,
    technologies: list[str],
    verified: bool = True,
) -> PoolItem:
    item = PoolItem(
        user_id=user.id,
        source=PoolItemSource.MANUAL,
        type=item_type,
        title=title,
        raw_content=raw_content,
        tags=[],
        technologies=technologies,
        language=language,
        embedding=None,
        verified_by_user=verified,
    )
    db.add(item)
    db.flush()
    return item


@pytest.mark.asyncio
async def test_cvtailor_outputs_english_for_english_job_and_preserves_technical_terms() -> None:
    with SessionLocal() as db:
        user = create_user(db, "tailor-en@example.com")
        job = create_job(
            db,
            user,
            raw_text="We need a backend engineer with FastAPI and machine learning experience.",
            language=ContentLanguage.EN,
            requirements=JobRequirementExtraction(required_skills=["FastAPI"], key_terms=["machine learning"]),
        )
        item = create_pool_item(
            db,
            user,
            title="Backend API",
            raw_content="Built FastAPI services and machine learning inference endpoints.",
            item_type=PoolItemType.PROJECT,
            language=ContentLanguage.EN,
            technologies=["FastAPI", "machine learning"],
        )
        db.commit()

        llm = FakeCVTailorLLM(
            TailoredCVDraft(
                output_language=ContentLanguage.EN,
                summary="Backend engineer with FastAPI and machine learning project experience.",
                projects=[
                    TailoredCVDraftItem(
                        source_index=1,
                        title="Backend API",
                        content="Built FastAPI services and machine learning inference endpoints for API workloads.",
                        technologies=["FastAPI", "machine learning"],
                    )
                ],
            )
        )

        state = await cvtailor_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "llm_service": llm,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.96)],
            }
        )

        tailored = state["tailored_cv"]
        assert tailored.output_language == ContentLanguage.EN
        assert "FastAPI" in tailored.projects[0].content
        assert "machine learning" in tailored.projects[0].content
        assert "Never add facts absent from sources" in llm.system_prompts[0]


@pytest.mark.asyncio
async def test_cvtailor_outputs_turkish_for_turkish_job_with_untranslated_technical_terms() -> None:
    with SessionLocal() as db:
        user = create_user(db, "tailor-tr@example.com")
        job = create_job(
            db,
            user,
            raw_text="FastAPI bilen backend gelistirici ariyoruz.",
            language=ContentLanguage.TR,
            requirements=JobRequirementExtraction(required_skills=["FastAPI"], key_terms=["backend"]),
        )
        item = create_pool_item(
            db,
            user,
            title="API Gelistirme",
            raw_content="FastAPI ile backend API gelistirme yaptim.",
            item_type=PoolItemType.EXPERIENCE,
            language=ContentLanguage.TR,
            technologies=["FastAPI"],
        )
        db.commit()

        llm = FakeCVTailorLLM(
            TailoredCVDraft(
                output_language=ContentLanguage.TR,
                summary="FastAPI odakli backend API gelistirme deneyimi.",
                experience=[
                    TailoredCVDraftItem(
                        source_index=1,
                        title="API Gelistirme",
                        content="FastAPI ile backend API gelistirme deneyimini ilana uygun sekilde one cikardi.",
                        technologies=["FastAPI"],
                    )
                ],
            )
        )

        state = await cvtailor_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "llm_service": llm,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.91)],
            }
        )

        tailored = state["tailored_cv"]
        assert tailored.output_language == ContentLanguage.TR
        assert "FastAPI" in tailored.experience[0].content
        assert "Turkish" in llm.prompts[0]


@pytest.mark.asyncio
async def test_cvtailor_blocks_unsupported_job_skill_and_falls_back_to_source_only_content() -> None:
    with SessionLocal() as db:
        user = create_user(db, "tailor-no-fabrication@example.com")
        job = create_job(
            db,
            user,
            raw_text="We need FastAPI and Kubernetes experience.",
            language=ContentLanguage.EN,
            requirements=JobRequirementExtraction(required_skills=["FastAPI", "Kubernetes"]),
        )
        item = create_pool_item(
            db,
            user,
            title="FastAPI service",
            raw_content="Built FastAPI services for internal APIs.",
            item_type=PoolItemType.PROJECT,
            language=ContentLanguage.EN,
            technologies=["FastAPI"],
        )
        db.commit()

        llm = FakeCVTailorLLM(
            TailoredCVDraft(
                output_language=ContentLanguage.EN,
                summary="FastAPI and Kubernetes backend experience.",
                projects=[
                    TailoredCVDraftItem(
                        source_index=1,
                        title="FastAPI service",
                        content="Built FastAPI and Kubernetes services for internal APIs.",
                        technologies=["FastAPI"],
                    )
                ],
            )
        )

        state = await cvtailor_node(
            {
                "user_id": user.id,
                "job_id": job.id,
                "db": db,
                "llm_service": llm,
                "selected_pool_items": [SelectedPoolItem(pool_item_id=item.id, score=0.9)],
            }
        )

        tailored = state["tailored_cv"]
        rendered_text = "\n".join([tailored.summary, *[project.content for project in tailored.projects]])
        assert "Kubernetes" not in rendered_text
        assert "Built FastAPI services for internal APIs." in rendered_text


def _guard_job(requirements: dict[str, list[str]], raw_text: str) -> Job:
    return Job(
        id=uuid4(),
        user_id=uuid4(),
        raw_text=raw_text,
        detected_language=ContentLanguage.EN,
        parsed_requirements_json=requirements,
    )


def _guard_source(
    raw_content: str,
    technologies: list[str],
    language: ContentLanguage = ContentLanguage.TR,
) -> PoolItem:
    return PoolItem(
        id=uuid4(),
        user_id=uuid4(),
        source=PoolItemSource.MANUAL,
        type=PoolItemType.EXPERIENCE,
        title="Odeme Platformu",
        raw_content=raw_content,
        tags=[],
        technologies=technologies,
        language=language,
        verified_by_user=True,
    )


def test_english_rendering_of_a_turkish_source_is_not_fabrication() -> None:
    """The guard and the ATS scorer must agree on what "present" means.

    Writing up a Turkish pool item in English is the product's main use case.
    Comparing raw substrings rejected it as fabrication, and the tailored CV was
    silently replaced by the untouched source text.
    """
    job = _guard_job(
        {"required_skills": ["REST APIs"], "preferred_skills": [], "key_terms": []},
        "Senior Backend Engineer building REST APIs.",
    )
    source = _guard_source("Gunluk 1.2 milyon istegi tasiyan REST API'leri gelistirdim.", ["FastAPI"])
    content = TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Backend engineer building REST APIs at scale.",
        experience=[
            TailoredCVItem(
                source_pool_item_id=source.id,
                title="Payments Platform",
                content="Built REST APIs serving 1.2 million requests a day.",
                technologies=["FastAPI"],
            )
        ],
    )

    validate_no_fabrication(content, job, [source])


def test_a_term_absent_from_the_sources_is_still_rejected() -> None:
    """Same language on both sides, so a missing term really is an invention."""
    job = _guard_job(
        {"required_skills": ["React"], "preferred_skills": [], "key_terms": []},
        "Senior Frontend Engineer.",
    )
    source = _guard_source("Built services with Python and FastAPI.", ["FastAPI"], ContentLanguage.EN)
    content = TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Frontend engineer working with React.",
        experience=[
            TailoredCVItem(
                source_pool_item_id=source.id,
                title="Payments Platform",
                content="Built interfaces with React.",
                technologies=["FastAPI"],
            )
        ],
    )

    with pytest.raises(CVTailorFabricationError, match="React"):
        validate_no_fabrication(content, job, [source])


def test_cross_language_write_up_is_not_policed_by_the_term_check() -> None:
    """Across languages the check cannot separate translation from invention.

    "servis" never matches "service", so enforcing it rejected honest work and
    the fallback replaced the tailored CV with the untouched source text.
    Invented tools remain blocked by the technologies check.
    """
    job = _guard_job(
        {"required_skills": ["service reliability"], "preferred_skills": [], "key_terms": []},
        "Senior Backend Engineer who will own service reliability.",
    )
    source = _guard_source("Odeme servislerini calistirdim.", ["FastAPI"], ContentLanguage.TR)
    content = TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Backend engineer who owned service reliability.",
        experience=[
            TailoredCVItem(
                source_pool_item_id=source.id,
                title="Payments Platform",
                content="Ran payment services and owned service reliability.",
                technologies=["FastAPI"],
            )
        ],
    )

    validate_no_fabrication(content, job, [source])


def test_invented_tools_are_blocked_even_across_languages() -> None:
    job = _guard_job({"required_skills": [], "preferred_skills": [], "key_terms": []}, "Any job.")
    source = _guard_source("Odeme servislerini calistirdim.", ["FastAPI"], ContentLanguage.TR)
    content = TailoredCVContent(
        output_language=ContentLanguage.EN,
        summary="Backend engineer.",
        experience=[
            TailoredCVItem(
                source_pool_item_id=source.id,
                title="Payments Platform",
                content="Ran payment services.",
                technologies=["FastAPI", "Kubernetes"],
            )
        ],
    )

    with pytest.raises(CVTailorFabricationError, match="kubernetes"):
        validate_no_fabrication(content, job, [source])
