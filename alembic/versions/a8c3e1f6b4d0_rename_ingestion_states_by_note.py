"""rename ingestion_states to ingestion_states_by_note

Revision ID: a8c3e1f6b4d0
Revises: e3a9c1b7d4f2
Create Date: 2026-08-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a8c3e1f6b4d0"
down_revision: str | Sequence[str] | None = "e3a9c1b7d4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINTS: tuple[tuple[str, str], ...] = (
    ("ingestion_states_pkey", "ingestion_states_by_note_pkey"),
    ("uq_ingestion_states_note_run", "uq_ingestion_states_by_note_note_run"),
    ("ingestion_states_status_check", "ingestion_states_by_note_status_check"),
    ("ingestion_states_note_id_fkey", "ingestion_states_by_note_note_id_fkey"),
    ("ingestion_states_run_id_fkey", "ingestion_states_by_note_run_id_fkey"),
    (
        "ingestion_states_index_version_id_fkey",
        "ingestion_states_by_note_index_version_id_fkey",
    ),
)


def _rename_constraint_if_exists(
    table: str,
    old_name: str,
    new_name: str,
) -> None:
    """Skip names that this database never created."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{old_name}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old_name} TO {new_name};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    """Keep per-note rows; make the table name match that grain."""
    op.rename_table("ingestion_states", "ingestion_states_by_note")
    for old_name, new_name in _CONSTRAINTS:
        _rename_constraint_if_exists(
            "ingestion_states_by_note",
            old_name,
            new_name,
        )
    op.execute(
        "ALTER SEQUENCE IF EXISTS ingestion_states_state_id_seq "
        "RENAME TO ingestion_states_by_note_state_id_seq"
    )


def downgrade() -> None:
    """Restore the original table and constraint names."""
    op.execute(
        "ALTER SEQUENCE IF EXISTS ingestion_states_by_note_state_id_seq "
        "RENAME TO ingestion_states_state_id_seq"
    )
    for old_name, new_name in reversed(_CONSTRAINTS):
        _rename_constraint_if_exists(
            "ingestion_states_by_note",
            new_name,
            old_name,
        )
    op.rename_table("ingestion_states_by_note", "ingestion_states")
