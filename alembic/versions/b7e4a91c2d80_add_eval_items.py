"""add eval_items gold evaluation table

Revision ID: b7e4a91c2d80
Revises: 7a2c4d1e9f30
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7e4a91c2d80"
down_revision: str | Sequence[str] | None = "7a2c4d1e9f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store Phase 7 gold questions with note-level labels."""
    op.create_table(
        "eval_items",
        sa.Column("eval_item_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("corpus_scope", sa.Text(), nullable=False),
        sa.Column(
            "relevant_note_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "relevant_chunk_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("dataset_version", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default="now()",
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(question) > 0",
            name="eval_items_question_not_empty_check",
        ),
        sa.CheckConstraint(
            "char_length(dataset_version) > 0",
            name="eval_items_dataset_version_not_empty_check",
        ),
        sa.CheckConstraint(
            "char_length(corpus_scope) > 0",
            name="eval_items_corpus_scope_not_empty_check",
        ),
        sa.PrimaryKeyConstraint("eval_item_id"),
        sa.UniqueConstraint(
            "dataset_version",
            "question",
            name="uq_eval_items_dataset_question",
        ),
    )


def downgrade() -> None:
    """Remove the Sprint 17 gold table."""
    op.drop_table("eval_items")
