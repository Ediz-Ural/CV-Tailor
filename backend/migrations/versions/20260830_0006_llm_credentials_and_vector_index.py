"""Store per-user LLM credentials and index the embedding column.

Revision ID: 20260830_0006
Revises: 20260830_0005
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0006"
down_revision: str = "20260830_0005"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_table(
        "llm_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("key_hint", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_llm_credentials_user_id"),
    )
    op.create_index("ix_llm_credentials_user_id", "llm_credentials", ["user_id"])

    # The selector ranks a user's whole pool by cosine distance on every run. An
    # HNSW index keeps that from degrading into a full scan as pools grow.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pool_items_embedding_cosine "
        "ON pool_items USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pool_items_embedding_cosine")
    op.drop_index("ix_llm_credentials_user_id", table_name="llm_credentials")
    op.drop_table("llm_credentials")
