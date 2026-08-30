from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, Tenant
from app.db.session import get_db
from app.models.enums import ContentLanguage
from app.models.job import Job
from app.schemas.job import JobCreate, JobResponse
from app.services.job_parser import JobFetchError, JobParser, fetch_single_job_page
from app.services.llm import LLMService, LLMError
from app.services.llm_credentials import LLMCredentialMissing, load_llm_service

router = APIRouter(prefix="/jobs", tags=["jobs"])
DbSession = Annotated[Session, Depends(get_db)]


def get_llm_service(current_user: CurrentUser, db: DbSession) -> LLMService:
    try:
        return load_llm_service(db, current_user.id)
    except LLMCredentialMissing as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


async def get_job_fetch_client():
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        yield client


LLMDependency = Annotated[LLMService, Depends(get_llm_service)]
FetchClient = Annotated[httpx.AsyncClient, Depends(get_job_fetch_client)]


def get_own_job(job_id: UUID, db: Session, tenant: Tenant) -> Job:
    job = db.scalar(tenant.apply(select(Job).where(Job.id == job_id), Job))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="İlan bulunamadı")
    return job


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: DbSession,
    current_user: CurrentUser,
    llm_service: LLMDependency,
    fetch_client: FetchClient,
) -> Job:
    source_url = str(payload.source_url) if payload.source_url else None
    if source_url:
        try:
            raw_text = await fetch_single_job_page(source_url, fetch_client)
        except JobFetchError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        raw_text = payload.raw_text or ""

    try:
        language, requirements = await JobParser(llm_service).parse(raw_text)
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="İlan parse edilemedi") from exc

    job = Job(
        user_id=current_user.id,
        source_url=source_url,
        raw_text=raw_text,
        detected_language=ContentLanguage(language),
        parsed_requirements_json=requirements.model_dump(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: DbSession,
    tenant: Tenant,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Job]:
    statement = (
        tenant.apply(select(Job).order_by(Job.created_at.desc(), Job.id), Job).limit(limit).offset(offset)
    )
    return list(db.scalars(statement))


@router.get("/{job_id}", response_model=JobResponse)
def read_job(job_id: UUID, db: DbSession, tenant: Tenant) -> Job:
    return get_own_job(job_id, db, tenant)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: UUID, db: DbSession, tenant: Tenant) -> Response:
    job = get_own_job(job_id, db, tenant)
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
