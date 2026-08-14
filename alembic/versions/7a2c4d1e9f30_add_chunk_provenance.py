"""add parser and source provenance to chunks

Revision ID: 7a2c4d1e9f30
Revises: c4f8a0d6e2b1
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7a2c4d1e9f30"
down_revision: str | Sequence[str] | None = "c4f8a0d6e2b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store provenance needed to audit regenerated chunks."""
    op.add_column("chunks", sa.Column("parser_version", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("source_content_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove Sprint 8 provenance columns."""
    op.drop_column("chunks", "source_content_hash")
    op.drop_column("chunks", "parser_version")
