"""add query_logs for HTTP /search

Revision ID: e3a9c1b7d4f2
Revises: b7e4a91c2d80
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3a9c1b7d4f2"
down_revision: str | Sequence[str] | None = "b7e4a91c2d80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store one row per attempted HTTP search (not 422 validation)."""
    op.create_table(
        "query_logs",
        sa.Column(
            "query_log_id",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "result_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "char_length(query) > 0",
            name="query_logs_query_not_empty_check",
        ),
        sa.CheckConstraint(
            "method IN ('dense', 'bm25', 'hybrid')",
            name="query_logs_method_check",
        ),
        sa.CheckConstraint("top_k > 0", name="query_logs_top_k_positive_check"),
        sa.CheckConstraint(
            "latency_ms >= 0",
            name="query_logs_latency_ms_check",
        ),
        sa.CheckConstraint(
            "result_count >= 0",
            name="query_logs_result_count_check",
        ),
        sa.PrimaryKeyConstraint("query_log_id"),
    )


def downgrade() -> None:
    """Remove HTTP search logs."""
    op.drop_table("query_logs")
