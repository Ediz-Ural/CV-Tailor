from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, Tenant
from app.db.session import get_db
from app.models.enums import ContentLanguage, PoolItemSource
from app.models.pool_item import PoolItem
from app.schemas.pool_item import PoolItemCreate, PoolItemPatch, PoolItemReplace, PoolItemResponse
from app.services.embeddings import EmbeddingService, detect_language

router = APIRouter(prefix="/pool-items", tags=["pool-items"])
DbSession = Annotated[Session, Depends(get_db)]


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


EmbeddingDependency = Annotated[EmbeddingService, Depends(get_embedding_service)]


def get_own_pool_item(item_id: UUID, db: Session, tenant: Tenant) -> PoolItem:
    item = db.scalar(tenant.apply(select(PoolItem).where(PoolItem.id == item_id), PoolItem))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Havuz öğesi bulunamadı")
    return item


def enrich_manual_item(item: PoolItem, embedding_service: EmbeddingService) -> None:
    item.source = PoolItemSource.MANUAL
    item.language = ContentLanguage(detect_language(item.raw_content))
    item.embedding = embedding_service.embed(item.raw_content)
    item.verified_by_user = True


@router.post("", response_model=PoolItemResponse, status_code=status.HTTP_201_CREATED)
def create_pool_item(
    payload: PoolItemCreate,
    db: DbSession,
    current_user: CurrentUser,
    tenant: Tenant,
    embedding_service: EmbeddingDependency,
) -> PoolItem:
    item = PoolItem(user_id=current_user.id, **payload.model_dump())
    enrich_manual_item(item, embedding_service)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PoolItemResponse])
def list_pool_items(
    db: DbSession,
    tenant: Tenant,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PoolItem]:
    statement = (
        tenant.apply(select(PoolItem).order_by(PoolItem.created_at, PoolItem.id), PoolItem)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


@router.get("/{item_id}", response_model=PoolItemResponse)
def read_pool_item(item_id: UUID, db: DbSession, tenant: Tenant) -> PoolItem:
    return get_own_pool_item(item_id, db, tenant)


@router.put("/{item_id}", response_model=PoolItemResponse)
def replace_pool_item(
    item_id: UUID,
    payload: PoolItemReplace,
    db: DbSession,
    tenant: Tenant,
    embedding_service: EmbeddingDependency,
) -> PoolItem:
    item = get_own_pool_item(item_id, db, tenant)
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    enrich_manual_item(item, embedding_service)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=PoolItemResponse)
def update_pool_item(
    item_id: UUID,
    payload: PoolItemPatch,
    db: DbSession,
    tenant: Tenant,
    embedding_service: EmbeddingDependency,
) -> PoolItem:
    item = get_own_pool_item(item_id, db, tenant)
    changes = payload.model_dump(exclude_unset=True)
    raw_content_changed = "raw_content" in changes
    for field, value in changes.items():
        setattr(item, field, value)
    if raw_content_changed:
        enrich_manual_item(item, embedding_service)
    else:
        item.source = PoolItemSource.MANUAL
        item.verified_by_user = True
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool_item(item_id: UUID, db: DbSession, tenant: Tenant) -> Response:
    item = get_own_pool_item(item_id, db, tenant)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
