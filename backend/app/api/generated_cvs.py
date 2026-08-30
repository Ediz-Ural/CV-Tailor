from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, Tenant
from app.db.session import get_db
from app.models.generated_cv import GeneratedCV
from app.models.job import Job
from app.models.profile import Profile
from app.render.typst import build_typst_source
from app.schemas.generated_cv import GeneratedCVRenderRequest, GeneratedCVResponse
from app.services.render_queue import render_generated_cv_task

router = APIRouter(prefix="/generated-cvs", tags=["generated-cvs"])
DbSession = Annotated[Session, Depends(get_db)]


def _contact_values(profile: Profile | None, fallback_email: str) -> list[str]:
    contact = profile.contact if profile and isinstance(profile.contact, dict) else {}
    values = [contact.get(key) for key in ("email", "phone", "location", "website", "github", "linkedin")]
    result = [str(value).strip() for value in values if str(value or "").strip()]
    return result or [fallback_email]


def _display_name(profile: Profile | None, fallback_email: str) -> str:
    if profile and profile.full_name:
        return profile.full_name
    return fallback_email.split("@", 1)[0]


@router.post("/render", response_model=GeneratedCVResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_generated_cv_render(
    payload: GeneratedCVRenderRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
    tenant: Tenant,
    current_user: CurrentUser,
) -> GeneratedCV:
    job = db.scalar(tenant.apply(select(Job).where(Job.id == payload.job_id), Job))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="İlan bulunamadı")

    profile = db.scalar(tenant.apply(select(Profile), Profile))
    typst_source = build_typst_source(
        tailored_cv=payload.tailored_cv,
        name=_display_name(profile, current_user.email),
        contact=_contact_values(profile, current_user.email),
        education=profile.education if profile else [],
    )
    generated_cv = GeneratedCV(
        user_id=current_user.id,
        job_id=job.id,
        selected_pool_item_ids=payload.selected_pool_item_ids,
        output_language=payload.tailored_cv.output_language,
        typst_source=typst_source,
        ats_score=payload.ats_score,
    )
    db.add(generated_cv)
    db.commit()
    db.refresh(generated_cv)

    background_tasks.add_task(render_generated_cv_task, generated_cv.id)
    return generated_cv


@router.get("", response_model=list[GeneratedCVResponse])
def list_generated_cvs(
    db: DbSession,
    tenant: Tenant,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[GeneratedCV]:
    statement = (
        tenant.apply(
            select(GeneratedCV).order_by(GeneratedCV.created_at.desc(), GeneratedCV.id.desc()),
            GeneratedCV,
        )
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


@router.get("/{generated_cv_id}/download")
def download_generated_cv(generated_cv_id: UUID, db: DbSession, tenant: Tenant) -> FileResponse:
    generated_cv = db.scalar(tenant.apply(select(GeneratedCV).where(GeneratedCV.id == generated_cv_id), GeneratedCV))
    if generated_cv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV bulunamadı")
    if not generated_cv.pdf_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PDF henüz hazır değil")

    pdf_path = Path(generated_cv.pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF dosyası bulunamadı")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{generated_cv.id}.pdf")
