from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType
from app.models.pool_item import PoolItem
from app.services.embeddings import EmbeddingService, detect_language


@dataclass(frozen=True)
class ExtractedPoolItem:
    source: PoolItemSource
    type: PoolItemType
    raw_content: str
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)


def normalize_string_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if clean and clean not in seen:
            normalized.append(clean)
            seen.add(clean)
    return normalized


def normalize_extracted_item(
    user_id: UUID,
    item: ExtractedPoolItem,
    embedding_service: EmbeddingService,
) -> PoolItem:
    raw_content = item.raw_content.strip()
    title = item.title.strip() if item.title else None
    return PoolItem(
        user_id=user_id,
        source=item.source,
        type=item.type,
        title=title or None,
        raw_content=raw_content,
        tags=normalize_string_list(item.tags),
        technologies=normalize_string_list(item.technologies),
        language=ContentLanguage(detect_language(raw_content)),
        embedding=embedding_service.embed(raw_content),
        verified_by_user=False,
    )


def create_unverified_pool_items(
    user_id: UUID,
    items: list[ExtractedPoolItem],
    embedding_service: EmbeddingService,
) -> list[PoolItem]:
    return [normalize_extracted_item(user_id, item, embedding_service) for item in items if item.raw_content.strip()]


def pending_pool_items_query(user_id: UUID):
    return (
        select(PoolItem)
        .where(
            PoolItem.user_id == user_id,
            PoolItem.verified_by_user.is_(False),
            PoolItem.source.in_([PoolItemSource.PDF, PoolItemSource.GITHUB]),
        )
        .order_by(PoolItem.created_at, PoolItem.id)
    )


def approve_pending_pool_items(db: Session, user_id: UUID, item_ids: list[UUID]) -> list[PoolItem]:
    if not item_ids:
        return []
    items = list(db.scalars(pending_pool_items_query(user_id).where(PoolItem.id.in_(item_ids))))
    for item in items:
        item.verified_by_user = True
    return items


def reject_pending_pool_items(db: Session, user_id: UUID, item_ids: list[UUID]) -> int:
    if not item_ids:
        return 0
    items = list(db.scalars(pending_pool_items_query(user_id).where(PoolItem.id.in_(item_ids))))
    count = len(items)
    for item in items:
        db.delete(item)
    return count
