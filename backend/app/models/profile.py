from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    full_name: Mapped[str | None] = mapped_column(String(255))
    contact: Mapped[dict | None] = mapped_column(JSONB)
    education: Mapped[list[dict]] = mapped_column(ARRAY(JSONB), default=list, nullable=False)
    personal_info: Mapped[dict | None] = mapped_column(JSONB)
