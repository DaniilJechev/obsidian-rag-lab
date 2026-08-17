"""PostgreSQL persistence for versioned ChunkRecord generations."""

from collections.abc import Iterator, Sequence

from sqlalchemy import Connection, delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from rag_based_on_obsidian.chunking.records import ChunkRecord
from rag_based_on_obsidian.db.schema import chunks, notes


class ChunkRepository:
    """Persist and query chunks by explicit note/version identity."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def upsert_generation(self, records: Sequence[ChunkRecord]) -> int:
        """Idempotently write one generation without deleting older versions."""
        if not records:
            return 0

        self._validate_generation(records)
        with self.connection.begin_nested():
            self._insert_generation(records)
        return len(records)

    def clear_all(self) -> int:
        """Delete every stored chunk before a full corpus materialization."""
        result = self.connection.execute(delete(chunks))
        return result.rowcount or 0

    def replace_generation(self, records: Sequence[ChunkRecord]) -> int:
        """Atomically regenerate one version without leaving stale rows."""
        if not records:
            return 0

        self._validate_generation(records)
        note_id = records[0].note_id
        chunking_version = records[0].chunking_version
        with self.connection.begin_nested():
            self.connection.execute(
                delete(chunks).where(
                    chunks.c.note_id == note_id,
                    chunks.c.chunking_version == chunking_version,
                )
            )
            self._insert_generation(records)
        return len(records)

    def _insert_generation(self, records: Sequence[ChunkRecord]) -> None:
        values = [_chunk_values(record) for record in records]
        statement = postgres_insert(chunks).values(values)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in chunks.columns
            if column.name not in {"chunk_id", "note_id", "chunk_index", "chunking_version"}
        }
        statement = statement.on_conflict_do_update(
            constraint="uq_chunks_note_version_index",
            set_=update_columns,
        )
        self.connection.execute(statement)

    @staticmethod
    def _validate_generation(records: Sequence[ChunkRecord]) -> None:
        identity = {(record.note_id, record.chunking_version) for record in records}
        if len(identity) != 1:
            raise ValueError("one generation must contain one note and version")

    def list_generation(self, *, note_id: int, chunking_version: str) -> list[dict]:
        """Read only the explicitly requested chunking version."""
        rows = self.connection.execute(
            select(chunks)
            .where(
                chunks.c.note_id == note_id,
                chunks.c.chunking_version == chunking_version,
            )
            .order_by(chunks.c.chunk_index)
        ).mappings()
        return [dict(row) for row in rows]

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> Iterator[list[dict[str, object]]]:
        """Stream one explicit chunking version in stable bounded batches."""
        if not chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        result = self.connection.execution_options(stream_results=True).execute(
            select(
                chunks,
                notes.c.relative_path.label("source_path"),
            )
            .select_from(chunks.join(notes, chunks.c.note_id == notes.c.note_id))
            .where(chunks.c.chunking_version == chunking_version)
            .order_by(
                chunks.c.note_id,
                chunks.c.chunk_index,
                chunks.c.chunk_id,
            )
        )
        mapping_result = result.mappings()
        try:
            while rows := mapping_result.fetchmany(batch_size):
                yield [dict(row) for row in rows]
        finally:
            result.close()

    def count_by_version(self, *, chunking_version: str) -> int:
        """Count chunks for one explicit version before starting inference."""
        if not chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        return int(
            self.connection.scalar(
                select(func.count())
                .select_from(chunks)
                .where(chunks.c.chunking_version == chunking_version)
            )
            or 0
        )

    def delete_generation(self, *, note_id: int, chunking_version: str) -> int:
        """Delete one generation explicitly; callers must opt into this action."""
        result = self.connection.execute(
            delete(chunks).where(
                chunks.c.note_id == note_id,
                chunks.c.chunking_version == chunking_version,
            )
        )
        return result.rowcount or 0


def _chunk_values(record: ChunkRecord) -> dict[str, object]:
    return {
        "note_id": record.note_id,
        "chunk_index": record.chunk_index,
        "text": record.text,
        "section_title": record.section_title,
        "section_level": record.section_level,
        "section_path": list(record.section_path),
        "section_type": record.section_type,
        "start_offset": record.start_offset,
        "end_offset": record.end_offset,
        "word_count": record.word_count,
        "token_count": record.token_count,
        "parser_version": record.parser_version,
        "source_content_hash": record.source_content_hash,
        "chunking_version": record.chunking_version,
    }
