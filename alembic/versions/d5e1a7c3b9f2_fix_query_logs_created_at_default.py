"""use SQL now() for query_logs.created_at

Revision ID: d5e1a7c3b9f2
Revises: a8c3e1f6b4d0
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d5e1a7c3b9f2"
down_revision: str | Sequence[str] | None = "a8c3e1f6b4d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the baked timestamptz constant with a live now() default."""
    op.alter_column(
        "query_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    """Restore the original string default (the buggy CREATE TABLE form)."""
    op.alter_column(
        "query_logs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default="now()",
    )
