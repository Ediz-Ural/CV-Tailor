from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.session import get_db
from app.models.pool_item import PoolItem
from app.schemas.pool_item import PoolApprovalResponse, PoolItemIdList, PoolItemResponse, PoolRejectResponse
from app.services.item_extractor import approve_pending_pool_items, pending_pool_items_query, reject_pending_pool_items

router = APIRouter(prefix="/pool", tags=["pool"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/pending", response_model=list[PoolItemResponse])
def list_pending_pool_items(db: DbSession, current_user: CurrentUser) -> list[PoolItem]:
    return list(db.scalars(pending_pool_items_query(current_user.id)))


@router.post("/approve", response_model=PoolApprovalResponse)
def approve_pool_items(payload: PoolItemIdList, db: DbSession, current_user: CurrentUser) -> PoolApprovalResponse:
    items = approve_pending_pool_items(db, current_user.id, payload.ids)
    db.commit()
    for item in items:
        db.refresh(item)
    return PoolApprovalResponse(updated_count=len(items), items=items)


@router.post("/reject", response_model=PoolRejectResponse)
def reject_pool_items(payload: PoolItemIdList, db: DbSession, current_user: CurrentUser) -> PoolRejectResponse:
    deleted_count = reject_pending_pool_items(db, current_user.id, payload.ids)
    db.commit()
    return PoolRejectResponse(deleted_count=deleted_count)
