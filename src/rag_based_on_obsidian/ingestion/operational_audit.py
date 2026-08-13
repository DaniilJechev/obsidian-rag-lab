"""Read-only operational audit helpers for the Sprint 6 test drive."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, func, select

from rag_based_on_obsidian.db.schema import (
    index_versions,
    ingestion_runs,
    ingestion_states,
    notes,
)
from rag_based_on_obsidian.ingestion.contracts import RunCounters


@dataclass(frozen=True)
class RunMetrics:
    """Observed metrics calculated from one persisted ingestion run."""

    run_id: int
    duration_seconds: float | None
    success_rate: float
    counters: RunCounters


@dataclass(frozen=True)
class ConsistencyReport:
    """Results of read-only relational consistency checks."""

    run_id: int
    notes_in_scope: int
    states_in_run: int
    duplicate_note_paths: int
    duplicate_note_run_states: int
    orphan_note_states: int
    orphan_run_states: int
    orphan_index_states: int

    @property
    def passed(self) -> bool:
        """Return whether all checked relational invariants hold."""
        return all(
            value == 0
            for value in (
                self.duplicate_note_paths,
                self.duplicate_note_run_states,
                self.orphan_note_states,
                self.orphan_run_states,
                self.orphan_index_states,
            )
        )


def calculate_run_metrics(
    connection: Connection,
    run_id: int,
) -> RunMetrics:
    """Calculate duration, success rate, and counters from persisted rows."""
    run = connection.execute(
        select(
            ingestion_runs.c.started_at,
            ingestion_runs.c.finished_at,
            ingestion_runs.c.documents_total,
            ingestion_runs.c.documents_succeeded,
            ingestion_runs.c.documents_failed,
            ingestion_runs.c.documents_skipped,
        ).where(ingestion_runs.c.run_id == run_id)
    ).mappings().one()
    duration_seconds = _duration_seconds(
        run["started_at"],
        run["finished_at"],
    )
    counters = _run_counters(connection, run_id, run)
    processed = counters.new + counters.changed + counters.unchanged
    success_rate = processed / counters.total if counters.total else 0.0
    return RunMetrics(
        run_id=run_id,
        duration_seconds=duration_seconds,
        success_rate=success_rate,
        counters=counters,
    )


def audit_run_consistency(
    connection: Connection,
    run_id: int,
    *,
    corpus_scope: str,
) -> ConsistencyReport:
    """Run read-only checks for one persisted ingestion run."""
    directories = tuple(
        directory.strip()
        for directory in corpus_scope.split(",")
        if directory.strip()
    )
    duplicate_paths = connection.execute(
        select(func.count())
        .select_from(
            select(notes.c.relative_path)
            .where(notes.c.source_directory.in_(directories))
            .group_by(notes.c.relative_path)
            .having(func.count() > 1)
            .subquery()
        )
    ).scalar_one()
    duplicate_states = connection.execute(
        select(func.count())
        .select_from(
            select(ingestion_states.c.note_id)
            .where(ingestion_states.c.run_id == run_id)
            .group_by(ingestion_states.c.note_id)
            .having(func.count() > 1)
            .subquery()
        )
    ).scalar_one()
    orphan_notes = connection.scalar(
        select(func.count())
        .select_from(ingestion_states)
        .outerjoin(notes, ingestion_states.c.note_id == notes.c.note_id)
        .where(
            ingestion_states.c.run_id == run_id,
            notes.c.note_id.is_(None),
        )
    )
    orphan_runs = connection.scalar(
        select(func.count())
        .select_from(ingestion_states)
        .outerjoin(
            ingestion_runs,
            ingestion_states.c.run_id == ingestion_runs.c.run_id,
        )
        .where(
            ingestion_states.c.run_id == run_id,
            ingestion_runs.c.run_id.is_(None),
        )
    )
    orphan_indexes = connection.scalar(
        select(func.count())
        .select_from(ingestion_states)
        .outerjoin(
            index_versions,
            ingestion_states.c.index_version_id
            == index_versions.c.index_version_id,
        )
        .where(
            ingestion_states.c.run_id == run_id,
            index_versions.c.index_version_id.is_(None),
        )
    )
    return ConsistencyReport(
        run_id=run_id,
        notes_in_scope=connection.scalar(
            select(func.count())
            .select_from(notes)
            .where(notes.c.source_directory.in_(directories))
        ),
        states_in_run=connection.scalar(
            select(func.count())
            .select_from(ingestion_states)
            .where(ingestion_states.c.run_id == run_id)
        ),
        duplicate_note_paths=duplicate_paths,
        duplicate_note_run_states=duplicate_states,
        orphan_note_states=orphan_notes,
        orphan_run_states=orphan_runs,
        orphan_index_states=orphan_indexes,
    )


def _run_counters(
    connection: Connection,
    run_id: int,
    run: Any,
) -> RunCounters:
    """Aggregate per-state outcomes without trusting only run counters."""
    rows = connection.execute(
        select(ingestion_states.c.status, func.count())
        .where(ingestion_states.c.run_id == run_id)
        .group_by(ingestion_states.c.status)
    ).all()
    counts = {status: count for status, count in rows}
    return RunCounters(
        total=run["documents_total"],
        new=counts.get("new", 0),
        changed=counts.get("changed", 0),
        unchanged=counts.get("unchanged", 0),
        stale=counts.get("stale", 0),
        failed=counts.get("failed", 0),
    )


def _duration_seconds(
    started_at: datetime,
    finished_at: datetime | None,
) -> float | None:
    """Return elapsed seconds only for a finished run."""
    if finished_at is None:
        return None
    return (finished_at - started_at).total_seconds()
