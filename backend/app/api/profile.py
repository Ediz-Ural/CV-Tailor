from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, Tenant
from app.db.session import get_db
from app.graphs.pool_graph import run_pool_graph_for_user
from app.models.profile import Profile
from app.schemas.pool_graph import PoolGraphTriggerResponse
from app.schemas.profile import ProfileCreate, ProfilePatch, ProfileReplace, ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])
DbSession = Annotated[Session, Depends(get_db)]
PoolGraphScheduler = Callable[[BackgroundTasks, UUID, bytes | None, bool], None]


def schedule_pool_graph(
    background_tasks: BackgroundTasks,
    user_id: UUID,
    pdf_bytes: bytes | None = None,
    include_github: bool = True,
) -> None:
    background_tasks.add_task(run_pool_graph_for_user, user_id, pdf_bytes, include_github)


def get_pool_graph_scheduler() -> PoolGraphScheduler:
    return schedule_pool_graph


PoolGraphSchedulerDependency = Annotated[PoolGraphScheduler, Depends(get_pool_graph_scheduler)]


def get_own_profile(db: Session, tenant: Tenant) -> Profile:
    profile = db.scalar(tenant.apply(select(Profile), Profile))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil bulunamadi")
    return profile


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    tenant: Tenant,
    pool_graph_scheduler: PoolGraphSchedulerDependency,
) -> Profile:
    existing = db.scalar(tenant.apply(select(Profile.id), Profile))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profil zaten mevcut")

    profile = Profile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profil zaten mevcut",
        ) from None
    db.refresh(profile)
    pool_graph_scheduler(background_tasks, current_user.id, None, True)
    return profile


@router.get("", response_model=ProfileResponse)
def read_profile(db: DbSession, tenant: Tenant) -> Profile:
    return get_own_profile(db, tenant)


@router.put("", response_model=ProfileResponse)
def replace_profile(
    payload: ProfileReplace,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    tenant: Tenant,
    pool_graph_scheduler: PoolGraphSchedulerDependency,
) -> Profile:
    profile = get_own_profile(db, tenant)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    pool_graph_scheduler(background_tasks, current_user.id, None, True)
    return profile


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfilePatch,
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    tenant: Tenant,
    pool_graph_scheduler: PoolGraphSchedulerDependency,
) -> Profile:
    profile = get_own_profile(db, tenant)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    pool_graph_scheduler(background_tasks, current_user.id, None, True)
    return profile


@router.post("/pool-refresh", response_model=PoolGraphTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_profile_pool_refresh(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    pool_graph_scheduler: PoolGraphSchedulerDependency,
    file: Annotated[UploadFile | None, File()] = None,
    include_github: Annotated[bool, Form()] = True,
) -> PoolGraphTriggerResponse:
    pdf_bytes: bytes | None = None
    if file is not None:
        filename = file.filename or ""
        if (file.content_type or "").lower() != "application/pdf" or not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Yalnizca PDF dosyasi yuklenebilir")
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="PDF dosyasi bos")

    pool_graph_scheduler(background_tasks, current_user.id, pdf_bytes, include_github)
    return PoolGraphTriggerResponse(queued=True, include_github=include_github, has_pdf=pdf_bytes is not None)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(db: DbSession, tenant: Tenant) -> Response:
    profile = get_own_profile(db, tenant)
    db.delete(profile)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
