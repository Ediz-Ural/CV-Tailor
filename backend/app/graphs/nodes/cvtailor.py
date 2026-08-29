from typing import Protocol, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graphs.nodes.selector import SelectedPoolItem
from app.models.enums import ContentLanguage
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.services.job_parser import dominant_job_language
from app.services.llm import LLMError, LLMService


class TailoredCVItem(BaseModel):
    source_pool_item_id: UUID
    title: str | None = None
    content: str = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)

    @field_validator("technologies")
    @classmethod
    def dedupe_technologies(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in value:
            normalized = item.strip()
            key = normalized.casefold()
            if normalized and key not in seen:
                result.append(normalized)
                seen.add(key)
        return result


class TailoredCVContent(BaseModel):
    output_language: ContentLanguage
    summary: str = Field(default="")
    experience: list[TailoredCVItem] = Field(default_factory=list)
    projects: list[TailoredCVItem] = Field(default_factory=list)
    skills: list[TailoredCVItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_mixed_output_language(self) -> "TailoredCVContent":
        if self.output_language == ContentLanguage.MIXED:
            raise ValueError("output_language must be tr or en")
        return self


class CVTailorState(TypedDict, total=False):
    user_id: UUID
    job_id: UUID
    db: Session
    llm_service: LLMService
    selected_pool_items: list[SelectedPoolItem]
    tailored_cv: TailoredCVContent
    output_language: ContentLanguage


class StructuredLLM(Protocol):
    async def structured(
        self,
        prompt: str,
        response_model: type[TailoredCVContent],
        *,
        system_prompt: str | None = None,
    ) -> TailoredCVContent: ...


class CVTailorFabricationError(ValueError):
    pass


def output_language_for_job(job: Job) -> ContentLanguage:
    if job.detected_language in {ContentLanguage.TR, ContentLanguage.EN}:
        return job.detected_language
    dominant = dominant_job_language(job.raw_text)
    return ContentLanguage.TR if dominant == "tr" else ContentLanguage.EN


def _selected_ids(selected_pool_items: list[SelectedPoolItem]) -> list[UUID]:
    return [item.pool_item_id for item in selected_pool_items]


def load_selected_pool_items(
    db: Session,
    user_id: UUID,
    selected_pool_items: list[SelectedPoolItem],
) -> list[PoolItem]:
    selected_ids = _selected_ids(selected_pool_items)
    if not selected_ids:
        return []

    rows = db.scalars(
        select(PoolItem).where(
            PoolItem.user_id == user_id,
            PoolItem.id.in_(selected_ids),
            PoolItem.verified_by_user.is_(True),
        )
    ).all()
    by_id = {item.id: item for item in rows}
    return [by_id[item_id] for item_id in selected_ids if item_id in by_id]


def _requirements_terms(job: Job) -> set[str]:
    requirements = job.parsed_requirements_json or {}
    terms: set[str] = set()
    for key in ("required_skills", "preferred_skills", "key_terms"):
        values = requirements.get(key)
        if isinstance(values, list):
            terms.update(str(value).strip() for value in values if str(value).strip())
    return terms


def _source_text(items: list[PoolItem]) -> str:
    parts: list[str] = []
    for item in items:
        parts.extend(
            [
                item.title or "",
                item.raw_content,
                " ".join(item.tags),
                " ".join(item.technologies),
            ]
        )
    return "\n".join(parts).casefold()


def _all_tailored_items(content: TailoredCVContent) -> list[TailoredCVItem]:
    return [*content.experience, *content.projects, *content.skills]


def validate_no_fabrication(content: TailoredCVContent, job: Job, source_items: list[PoolItem]) -> None:
    source_by_id = {item.id: item for item in source_items}
    source_text = _source_text(source_items)
    output_text = "\n".join(
        [content.summary, *[item.title or "" for item in _all_tailored_items(content)], *[item.content for item in _all_tailored_items(content)]]
    ).casefold()

    for item in _all_tailored_items(content):
        source = source_by_id.get(item.source_pool_item_id)
        if source is None:
            raise CVTailorFabricationError(f"Unknown source_pool_item_id: {item.source_pool_item_id}")

        allowed_technologies = {technology.casefold() for technology in source.technologies}
        returned_technologies = {technology.casefold() for technology in item.technologies}
        if not returned_technologies <= allowed_technologies:
            unsupported = sorted(returned_technologies - allowed_technologies)
            raise CVTailorFabricationError(f"Unsupported technologies returned: {unsupported}")

    for term in _requirements_terms(job):
        normalized = term.casefold()
        if normalized in output_text and normalized not in source_text:
            raise CVTailorFabricationError(f"Unsupported job term returned: {term}")


def _item_payload(item: PoolItem, score: float | None) -> dict[str, object]:
    return {
        "pool_item_id": str(item.id),
        "selector_score": score,
        "type": item.type.value,
        "title": item.title,
        "language": item.language.value,
        "tags": item.tags,
        "technologies": item.technologies,
        "raw_content": item.raw_content[:1600],
    }


def _tailor_prompt(job: Job, source_items: list[PoolItem], selected_pool_items: list[SelectedPoolItem], output_language: ContentLanguage) -> str:
    score_by_id = {item.pool_item_id: item.score for item in selected_pool_items}
    payload = [_item_payload(item, score_by_id.get(item.id)) for item in source_items]
    return (
        "Tailor the selected verified CV pool items to the job posting. "
        f"Write the CV content in {'English' if output_language == ContentLanguage.EN else 'Turkish'}. "
        "Preserve technical terms exactly as they appear in the source items, for example FastAPI or machine learning. "
        "Do not invent skills, employers, metrics, responsibilities, dates, tools, certifications, or outcomes. "
        "Only emphasize or rephrase facts that are explicitly present in the selected source items. "
        "Every experience, project, and skill item must include the source_pool_item_id it came from. "
        "If a job requirement is not supported by the selected source items, omit it.\n\n"
        f"Output language enum: {output_language.value}\n"
        f"Job detected language: {job.detected_language.value}\n"
        f"Job requirements JSON: {job.parsed_requirements_json or {}}\n"
        f"Job posting:\n{job.raw_text[:2400]}\n\n"
        f"Selected source items:\n{payload}"
    )


def _fallback_tailored_cv(source_items: list[PoolItem], output_language: ContentLanguage) -> TailoredCVContent:
    summary = (
        "Selected verified experience aligned with the role."
        if output_language == ContentLanguage.EN
        else "Ilana uygun dogrulanmis deneyim ve beceriler secildi."
    )
    content = TailoredCVContent(output_language=output_language, summary=summary)
    for item in source_items:
        tailored_item = TailoredCVItem(
            source_pool_item_id=item.id,
            title=item.title,
            content=item.raw_content,
            technologies=item.technologies,
        )
        if item.type.value == "experience":
            content.experience.append(tailored_item)
        elif item.type.value == "project":
            content.projects.append(tailored_item)
        elif item.type.value == "skill":
            content.skills.append(tailored_item)
    return content


async def tailor_with_llm(
    llm_service: StructuredLLM,
    job: Job,
    source_items: list[PoolItem],
    selected_pool_items: list[SelectedPoolItem],
    output_language: ContentLanguage,
) -> TailoredCVContent:
    tailored = await llm_service.structured(
        _tailor_prompt(job, source_items, selected_pool_items, output_language),
        TailoredCVContent,
        system_prompt=(
            "You are CVTailor for CV-Tailor. Produce structured CV content only from selected verified source items. "
            "Use the requested output language. Keep technical terms untranslated. Never add facts absent from sources."
        ),
    )
    if tailored.output_language != output_language:
        raise CVTailorFabricationError("LLM returned the wrong output language")
    validate_no_fabrication(tailored, job, source_items)
    return tailored


async def cvtailor_node(state: CVTailorState) -> dict[str, object]:
    db = state["db"]
    user_id = state["user_id"]
    job = db.scalar(select(Job).where(Job.id == state["job_id"], Job.user_id == user_id))
    if job is None:
        return {"tailored_cv": None, "output_language": None}

    selected_pool_items = state.get("selected_pool_items", [])
    source_items = load_selected_pool_items(db, user_id, selected_pool_items)
    output_language = output_language_for_job(job)
    if not source_items:
        empty = TailoredCVContent(output_language=output_language)
        return {"tailored_cv": empty, "output_language": output_language}

    try:
        tailored = await tailor_with_llm(
            state["llm_service"],
            job,
            source_items,
            selected_pool_items,
            output_language,
        )
    except (LLMError, CVTailorFabricationError):
        tailored = _fallback_tailored_cv(source_items, output_language)

    return {"tailored_cv": tailored, "output_language": output_language}
