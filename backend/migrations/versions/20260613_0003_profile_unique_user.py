"""Ensure each user has at most one profile.

Revision ID: 20260613_0003
Revises: 20260613_0002
Create Date: 2026-06-13
"""

from alembic import op

revision: str = "20260613_0003"
down_revision: str = "20260613_0002"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
