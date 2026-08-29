from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import EMBEDDING_DIMENSION
from app.db.base import Base
from app.models.enums import ContentLanguage, PoolItemSource, PoolItemType


class PoolItem(Base):
    __tablename__ = "pool_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[PoolItemSource] = mapped_column(
        SQLEnum(PoolItemSource, name="pool_item_source", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    type: Mapped[PoolItemType] = mapped_column(
        SQLEnum(PoolItemType, name="pool_item_type", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String()), default=list, nullable=False)
    technologies: Mapped[list[str]] = mapped_column(ARRAY(String()), default=list, nullable=False)
    language: Mapped[ContentLanguage] = mapped_column(
        SQLEnum(ContentLanguage, name="content_language", values_callable=lambda enum: [item.value for item in enum]),
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSION))
    verified_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def embedding_dimensions(self) -> int:
        if self.embedding is None:
            return 0
        return len(self.embedding)
