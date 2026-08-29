"""Add education pool item type."""

from alembic import op

revision = "20260621_0004"
down_revision = "20260613_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE pool_item_type ADD VALUE IF NOT EXISTS 'education'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely without rebuilding dependent columns.
    pass
