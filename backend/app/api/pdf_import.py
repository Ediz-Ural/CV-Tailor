from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import PoolItemSource, PoolItemType
from app.models.profile import Profile
from app.schemas.pdf_import import PDFExtractedItem, PDFExtractedProfile, PDFExtraction, PDFImportResponse
from app.services.embeddings import EmbeddingService
from app.services.item_extractor import ExtractedPoolItem, create_unverified_pool_items
from app.services.llm import LLMError, LLMService
from app.services.pdf_parser import PDFParseError, extract_pdf_text

router = APIRouter(prefix="/pool/import", tags=["pool-import"])
DbSession = Annotated[Session, Depends(get_db)]


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


def get_llm_service() -> LLMService:
    return LLMService()


EmbeddingDependency = Annotated[EmbeddingService, Depends(get_embedding_service)]
LLMDependency = Annotated[LLMService, Depends(get_llm_service)]


def validate_pdf_upload(file: UploadFile, data: bytes) -> None:
    filename = file.filename or ""
    content_type = (file.content_type or "").lower()
    if content_type != "application/pdf" or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Yalnizca PDF dosyasi yuklenebilir")
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PDF dosyasi bos")
    if len(data) > settings.pdf_import_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="PDF dosyasi boyut limitini asiyor")


def build_pdf_extraction_prompt(text: str) -> str:
    return (
        "Extract candidate profile data and CV pool items from the PDF text below. "
        "Return only factual items present in the text. Do not invent details. "
        "For profile, extract full_name, email, phone, location, summary, and education entries when present. "
        "Use kind='experience' for jobs/internships/projects described as work, "
        "kind='education' for schools/degrees/certificates, and kind='skill' for concrete skills. "
        "Keep Turkish and English technical terms as written. "
        "Each raw_content must be self-contained and concise.\n\n"
        f"PDF text:\n{text}"
    )


def pool_type_for_pdf_item(item: PDFExtractedItem) -> PoolItemType:
    if item.kind == "skill":
        return PoolItemType.SKILL
    if item.kind == "education":
        return PoolItemType.EDUCATION
    return PoolItemType.EXPERIENCE


def tags_for_pdf_item(item: PDFExtractedItem) -> list[str]:
    tags = list(item.tags)
    if item.kind == "education" and "education" not in tags:
        tags.insert(0, "education")
    return tags


def contact_from_pdf_profile(profile: PDFExtractedProfile) -> dict[str, str]:
    contact = {}
    if profile.email:
        contact["email"] = profile.email
    if profile.phone:
        contact["phone"] = profile.phone
    if profile.location:
        contact["location"] = profile.location
    return contact


def education_from_pdf_profile(profile: PDFExtractedProfile) -> list[dict[str, str]]:
    education = []
    for item in profile.education:
        entry = {}
        if item.school:
            entry["school"] = item.school
        if item.degree:
            entry["degree"] = item.degree
        if item.raw_content:
            entry["raw_content"] = item.raw_content
        if entry:
            education.append(entry)
    return education


def upsert_profile_from_pdf(db: Session, user_id, extracted: PDFExtractedProfile | None) -> Profile | None:
    if extracted is None:
        return None

    contact = contact_from_pdf_profile(extracted)
    education = education_from_pdf_profile(extracted)
    personal_info = {"summary": extracted.summary} if extracted.summary else {}
    has_profile_data = bool(extracted.full_name or contact or education or personal_info)
    if not has_profile_data:
        return None

    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        if not extracted.full_name:
            return None
        profile = Profile(
            user_id=user_id,
            full_name=extracted.full_name,
            contact=contact or None,
            education=education,
            personal_info=personal_info or None,
        )
        db.add(profile)
        return profile

    if extracted.full_name:
        profile.full_name = extracted.full_name
    if contact:
        profile.contact = {**(profile.contact or {}), **contact}
    if education:
        profile.education = education
    if personal_info:
        profile.personal_info = {**(profile.personal_info or {}), **personal_info}
    return profile


@router.post("/pdf", response_model=PDFImportResponse, status_code=status.HTTP_201_CREATED)
async def import_pdf_to_pool(
    file: Annotated[UploadFile, File()],
    db: DbSession,
    current_user: CurrentUser,
    llm_service: LLMDependency,
    embedding_service: EmbeddingDependency,
) -> PDFImportResponse:
    data = await file.read()
    validate_pdf_upload(file, data)

    try:
        text = extract_pdf_text(data)
    except PDFParseError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    try:
        extraction = await llm_service.structured(
            build_pdf_extraction_prompt(text),
            PDFExtraction,
            system_prompt="You extract structured, factual profile data and CV pool items from PDF CV text.",
        )
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM structured cikarim basarisiz") from exc

    if not extraction.items:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PDF icinden havuz ogesi cikarilamadi")

    pool_items = create_unverified_pool_items(
        current_user.id,
        [
            ExtractedPoolItem(
                source=PoolItemSource.PDF,
                type=pool_type_for_pdf_item(item),
                title=item.title,
                raw_content=item.raw_content,
                tags=tags_for_pdf_item(item),
                technologies=item.technologies,
            )
            for item in extraction.items
        ],
        embedding_service,
    )
    if not pool_items:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PDF icinden havuz ogesi cikarilamadi")
    profile = upsert_profile_from_pdf(db, current_user.id, extraction.profile)
    db.add_all(pool_items)
    db.commit()
    if profile is not None:
        db.refresh(profile)
    for item in pool_items:
        db.refresh(item)

    return PDFImportResponse(imported_count=len(pool_items), items=pool_items, profile=profile)
