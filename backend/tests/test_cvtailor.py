from collections.abc import Generator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem, cvtailor_node
from app.graphs.nodes.selector import SelectedPoolItem
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.models.user import User
from app.schemas.job import JobRequirementExtraction
from app.db.session import SessionLocal


class FakeCVTailorLLM:
    def __init__(self, content: TailoredCVContent) -> None:
        self.content = content
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []

    async def structured(
        self,
        prompt: str,
        response_model: type[TailoredCVContent],
        *,
        system_prompt: str | None = None,
    ) -> TailoredCVContent:
        assert response_model is TailoredCVContent
        assert system_prompt is not None
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        return self.content


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
            TailoredCVContent(
                output_language=ContentLanguage.EN,
                summary="Backend engineer with FastAPI and machine learning project experience.",
                projects=[
                    TailoredCVItem(
                        source_pool_item_id=item.id,
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
            TailoredCVContent(
                output_language=ContentLanguage.TR,
                summary="FastAPI odakli backend API gelistirme deneyimi.",
                experience=[
                    TailoredCVItem(
                        source_pool_item_id=item.id,
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
            TailoredCVContent(
                output_language=ContentLanguage.EN,
                summary="FastAPI and Kubernetes backend experience.",
                projects=[
                    TailoredCVItem(
                        source_pool_item_id=item.id,
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
