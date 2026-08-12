"""expand ingestion state statuses for idempotent ingestion

Revision ID: c4f8a0d6e2b1
Revises: 909bce321e14
Create Date: 2026-08-12
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "c4f8a0d6e2b1"
down_revision: str | Sequence[str] | None = "909bce321e14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STATUS_CHECK = "ingestion_states_status_check"
_STATUS_EXPRESSION = (
    "status IN ('discovered', 'parsed', 'new', 'changed', "
    "'unchanged', 'failed', 'stale')"
)


def upgrade() -> None:
    """Allow application-level idempotency decisions in ingestion states."""
    op.drop_constraint(
        _OLD_STATUS_CHECK,
        "ingestion_states",
        type_="check",
    )
    op.create_check_constraint(
        _OLD_STATUS_CHECK,
        "ingestion_states",
        _STATUS_EXPRESSION,
    )


def downgrade() -> None:
    """Restore the Sprint 4 contract only when no Sprint 5 states remain."""
    connection = op.get_bind()
    sprint_five_states = connection.execute(
        text(
            "SELECT COUNT(*) FROM ingestion_states "
            "WHERE status IN ('new', 'changed', 'unchanged')"
        )
    ).scalar_one()
    if sprint_five_states:
        raise RuntimeError(
            "Cannot downgrade while ingestion_states contains Sprint 5 "
            f"statuses ({sprint_five_states} rows); preserve the audit trail "
            "or migrate those rows explicitly first."
        )
    op.drop_constraint(
        _OLD_STATUS_CHECK,
        "ingestion_states",
        type_="check",
    )
    op.create_check_constraint(
        _OLD_STATUS_CHECK,
        "ingestion_states",
        "status IN ('discovered', 'parsed', 'failed', 'stale')",
    )
