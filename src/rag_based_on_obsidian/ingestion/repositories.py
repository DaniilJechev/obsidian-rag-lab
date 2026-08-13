"""SQLAlchemy Core repositories for idempotent ingestion."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from rag_based_on_obsidian.db.schema import (
    index_versions,
    ingestion_runs,
    ingestion_states,
    notes,
)
from rag_based_on_obsidian.ingestion.contracts import (
    IncomingNote,
    PreviousNoteState,
    RunCounters,
)


class NoteRepository:
    """Persistence operations for the current note projection."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_by_path(self, relative_path: str) -> PreviousNoteState | None:
        """Return the current identity fields for one relative path."""
        row = self.connection.execute(
            select(
                notes.c.note_id,
                notes.c.relative_path,
                notes.c.content_hash,
                notes.c.parser_version,
                select(ingestion_states.c.status)
                .where(ingestion_states.c.note_id == notes.c.note_id)
                .order_by(
                    ingestion_states.c.created_at.desc(),
                    ingestion_states.c.state_id.desc(),
                )
                .limit(1)
                .scalar_subquery()
                .label("last_status"),
            ).where(notes.c.relative_path == relative_path)
        ).mappings().one_or_none()
        if row is None:
            return None
        return PreviousNoteState(
            note_id=row["note_id"],
            relative_path=row["relative_path"],
            content_hash=row["content_hash"],
            parser_version=row["parser_version"],
            last_status=row["last_status"],
        )

    def upsert(self, incoming: IncomingNote) -> int:
        """Insert a new note or update its current projection."""
        values = _note_values(incoming)
        statement = postgres_insert(notes).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[notes.c.relative_path],
            set_={
                key: getattr(statement.excluded, key)
                for key in values
                if key != "relative_path"
            },
        ).returning(notes.c.note_id)
        return self.connection.execute(statement).scalar_one()

    def list_paths(
        self,
        *,
        source_directories: tuple[str, ...] | None = None,
    ) -> list[PreviousNoteState]:
        """Return current notes, optionally limited to ingestion scope."""
        conditions = (
            [notes.c.source_directory.in_(source_directories)]
            if source_directories
            else []
        )
        rows = self.connection.execute(
            select(
                notes.c.note_id,
                notes.c.relative_path,
                notes.c.content_hash,
                notes.c.parser_version,
                select(ingestion_states.c.status)
                .where(ingestion_states.c.note_id == notes.c.note_id)
                .order_by(
                    ingestion_states.c.created_at.desc(),
                    ingestion_states.c.state_id.desc(),
                )
                .limit(1)
                .scalar_subquery()
                .label("last_status"),
            )
            .where(*conditions)
            .order_by(notes.c.relative_path)
        ).mappings()
        return [
            PreviousNoteState(
                note_id=row["note_id"],
                relative_path=row["relative_path"],
                content_hash=row["content_hash"],
                parser_version=row["parser_version"],
                last_status=row["last_status"],
            )
            for row in rows
        ]


class IndexVersionRepository:
    """Persistence operations for parser/chunking/embedding identities."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_or_create(
        self,
        *,
        parser_version: str,
        chunking_version: str,
        embedding_model: str | None = None,
        embedding_version: str | None = None,
        embedding_parameters: Mapping[str, Any] | None = None,
    ) -> int:
        """Return one stable index version row for the pipeline configuration."""
        parameters = dict(embedding_parameters or {})
        identity = {
            "parser_version": parser_version,
            "chunking_version": chunking_version,
            "embedding_model": embedding_model,
            "embedding_version": embedding_version,
            "embedding_parameters": parameters,
        }
        row = self.connection.execute(
            select(index_versions.c.index_version_id).where(
                *(
                    column == value
                    for column, value in (
                        (index_versions.c.parser_version, parser_version),
                        (index_versions.c.chunking_version, chunking_version),
                        (index_versions.c.embedding_model, embedding_model),
                        (index_versions.c.embedding_version, embedding_version),
                        (index_versions.c.embedding_parameters, parameters),
                    )
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            return row
        statement = postgres_insert(index_versions).values(**identity)
        statement = statement.on_conflict_do_nothing(
            constraint="uq_index_versions_identity",
        )
        self.connection.execute(statement)
        return self.connection.execute(
            select(index_versions.c.index_version_id).where(
                *(
                    column == value
                    for column, value in (
                        (index_versions.c.parser_version, parser_version),
                        (index_versions.c.chunking_version, chunking_version),
                        (index_versions.c.embedding_model, embedding_model),
                        (index_versions.c.embedding_version, embedding_version),
                        (index_versions.c.embedding_parameters, parameters),
                    )
                )
            )
        ).scalar_one()


def acquire_ingestion_lock(connection: Connection) -> None:
    """Serialize runs so stale detection uses one consistent discovery snapshot."""
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "rag_based_on_obsidian:ingestion"},
    )


class IngestionRunRepository:
    """Create and finalize one ingestion run."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def create(self, corpus_scope: str) -> int:
        """Create a running batch record before processing documents."""
        return self.connection.execute(
            insert(ingestion_runs)
            .values(
                status="running",
                corpus_scope=corpus_scope,
                started_at=datetime.now(UTC),
            )
            .returning(ingestion_runs.c.run_id)
        ).scalar_one()

    def finish(
        self,
        run_id: int,
        counters: RunCounters,
        *,
        status: str,
    ) -> None:
        """Persist final status and aggregate counters."""
        self.connection.execute(
            update(ingestion_runs)
            .where(ingestion_runs.c.run_id == run_id)
            .values(
                status=status,
                finished_at=datetime.now(UTC),
                documents_total=counters.total,
                documents_succeeded=(
                    counters.new + counters.changed + counters.unchanged
                ),
                documents_failed=counters.failed,
                documents_skipped=counters.unchanged,
            )
        )


class IngestionStateRepository:
    """Append one per-note state row to an ingestion run."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def record(
        self,
        *,
        note_id: int,
        run_id: int,
        index_version_id: int,
        content_hash: str,
        parser_version: str,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> int:
        """Record the outcome while preserving one row per note and run."""
        return self.connection.execute(
            insert(ingestion_states)
            .values(
                note_id=note_id,
                run_id=run_id,
                index_version_id=index_version_id,
                content_hash=content_hash,
                parser_version=parser_version,
                status=status,
                error_type=error_type,
                error_message=error_message,
                processed_at=datetime.now(UTC),
            )
            .returning(ingestion_states.c.state_id)
        ).scalar_one()


def _note_values(incoming: IncomingNote) -> dict[str, Any]:
    """Translate the immutable contract into SQLAlchemy Core values."""
    return {
        "relative_path": incoming.relative_path,
        "source_directory": incoming.source_directory,
        "title": incoming.title,
        "content_hash": incoming.content_hash,
        "file_size_bytes": incoming.file_size_bytes,
        "character_count": incoming.character_count,
        "word_count": incoming.word_count,
        "language_statistics": incoming.language_statistics,
        "parse_status": incoming.parse_status,
        "anomalies": incoming.anomalies,
        "source_mtime": incoming.source_mtime,
        "parser_version": incoming.parser_version,
        "updated_at": datetime.now(UTC),
    }
