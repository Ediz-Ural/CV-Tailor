"""Create the multi-tenant application schema.

Revision ID: 20260613_0002
Revises: 20260613_0001
Create Date: 2026-06-13
"""

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260613_0002"
down_revision: str = "20260613_0001"
branch_labels: None = None
depends_on: None = None

pool_item_source = postgresql.ENUM(
    "pdf", "github", "manual", name="pool_item_source", create_type=False
)
pool_item_type = postgresql.ENUM(
    "experience", "project", "skill", name="pool_item_type", create_type=False
)
content_language = postgresql.ENUM(
    "tr", "en", "mixed", name="content_language", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    # pool_items.embedding needs pgvector. The compose stack seeds it through an
    # initdb script, but a plain Postgres instance would fail without this.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    pool_item_source.create(bind, checkfirst=True)
    pool_item_type.create(bind, checkfirst=True)
    content_language.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("kvkk_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("contact", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("education", postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=False),
        sa.Column("personal_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])
    op.create_table(
        "pool_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", pool_item_source, nullable=False),
        sa.Column("type", pool_item_type, nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("technologies", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("language", content_language, nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1024), nullable=True),
        sa.Column("verified_by_user", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pool_items_user_id", "pool_items", ["user_id"])
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("detected_language", content_language, nullable=False),
        sa.Column("parsed_requirements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_table(
        "generated_cvs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_pool_item_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("output_language", content_language, nullable=False),
        sa.Column("typst_source", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(length=2048), nullable=True),
        sa.Column("ats_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_cvs_user_id", "generated_cvs", ["user_id"])
    op.create_table(
        "github_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_username", sa.String(length=255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_github_connections_user_id", "github_connections", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_github_connections_user_id", table_name="github_connections")
    op.drop_table("github_connections")
    op.drop_index("ix_generated_cvs_user_id", table_name="generated_cvs")
    op.drop_table("generated_cvs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_pool_items_user_id", table_name="pool_items")
    op.drop_table("pool_items")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")
    op.drop_table("users")

    bind = op.get_bind()
    content_language.drop(bind, checkfirst=True)
    pool_item_type.drop(bind, checkfirst=True)
    pool_item_source.drop(bind, checkfirst=True)
