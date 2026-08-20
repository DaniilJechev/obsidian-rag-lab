"""Direct persistence of dense embeddings in experimental pgvector Postgres."""

import re
from collections.abc import Sequence
from time import perf_counter, sleep

from pgvector.psycopg import register_vector
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from rag_based_on_obsidian.db.pgvector_schema import (
    DEFAULT_PGVECTOR_TABLE,
    chunk_embeddings_table,
)
from rag_based_on_obsidian.embeddings.pipeline import (
    ChunkRow,
    EmbeddedChunk,
    SinkWriteError,
    SinkWriteResult,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import stable_point_key

_REGISTERED_ENGINE_IDS: set[int] = set()
_HNSW_INDEX_SUFFIX = "embedding_hnsw"


class PgvectorVectorSink:
    """Upsert validated dense batches into one versioned pgvector table."""

    def __init__(
        self,
        engine: Engine,
        *,
        index_generation: str,
        vector_size: int,
        table_name: str = DEFAULT_PGVECTOR_TABLE,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.0,
    ) -> None:
        if not index_generation.strip():
            raise ValueError("index_generation must not be empty")
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        if not table_name.strip():
            raise ValueError("table_name must not be empty")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")
        self.engine = engine
        self.index_generation = index_generation
        self.vector_size = vector_size
        self.table_name = table_name
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._table = chunk_embeddings_table(
            vector_size,
            table_name=table_name,
        )
        _register_vector_on_engine(engine)
        self.ensure_schema()

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        index_generation: str,
        vector_size: int,
        table_name: str = DEFAULT_PGVECTOR_TABLE,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.0,
    ) -> "PgvectorVectorSink":
        """Create a sink connected to the experimental pgvector database."""
        return cls(
            create_engine(url),
            index_generation=index_generation,
            vector_size=vector_size,
            table_name=table_name,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    def ensure_schema(self) -> None:
        """Create the vector extension, table and HNSW index if missing."""
        with self.engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            existing_dimension = _existing_vector_dimension(
                connection,
                table_name=self.table_name,
            )
            if existing_dimension is not None and existing_dimension != self.vector_size:
                raise ValueError(
                    "pgvector table dimension mismatch: "
                    f"expected {self.vector_size}, got {existing_dimension}; "
                    "recreate the experimental table before upsert"
                )
            self._table.create(connection, checkfirst=True)
            connection.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS {self._hnsw_index_name()} "
                    f"ON {self.table_name} "
                    "USING hnsw (embedding vector_cosine_ops)"
                )
            )

    def delete_generation(self) -> None:
        """Remove only the target index generation; keep the table."""
        with self.engine.begin() as connection:
            connection.execute(
                self._table.delete().where(
                    self._table.c.index_generation == self.index_generation
                )
            )

    def upsert_batch(
        self,
        embeddings: Sequence[EmbeddedChunk],
        chunks: Sequence[ChunkRow],
    ) -> SinkWriteResult:
        """Upsert one validated dense batch with chunk metadata columns."""
        if len(embeddings) != len(chunks):
            raise ValueError("embedding and chunk batch sizes must match")
        if not embeddings:
            return SinkWriteResult(
                points_written=0,
                duration_seconds=0.0,
                attempts=0,
                vector_bytes=0,
            )
        rows = [
            _row_for_chunk(
                embedded,
                chunk,
                index_generation=self.index_generation,
                vector_size=self.vector_size,
            )
            for embedded, chunk in zip(embeddings, chunks, strict=True)
        ]
        statement = insert(self._table).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=["index_generation", "point_key"],
            set_={
                column.name: statement.excluded[column.name]
                for column in self._table.columns
                if column.name not in {"index_generation", "point_key"}
            },
        )
        started_at = perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                with self.engine.begin() as connection:
                    connection.execute(statement)
                return SinkWriteResult(
                    points_written=len(rows),
                    duration_seconds=perf_counter() - started_at,
                    attempts=attempt,
                    vector_bytes=len(rows) * self.vector_size * 4,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt <= self.max_retries:
                    sleep(self.retry_backoff_seconds)
        assert last_error is not None
        raise SinkWriteError(
            f"pgvector upsert failed after {self.max_retries + 1} attempts: "
            f"{last_error}",
            attempts=self.max_retries + 1,
        ) from last_error

    def count_points(self) -> int:
        """Return how many rows belong to the current index generation."""
        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    f"SELECT COUNT(*) FROM {self.table_name} "
                    "WHERE index_generation = :index_generation"
                ),
                {"index_generation": self.index_generation},
            )
            return int(result.scalar_one())

    def _hnsw_index_name(self) -> str:
        return f"ix_{self.table_name}_{_HNSW_INDEX_SUFFIX}"


def _row_for_chunk(
    embedded: EmbeddedChunk,
    chunk: ChunkRow,
    *,
    index_generation: str,
    vector_size: int,
) -> dict[str, object]:
    """Build one SQL row using the same identity as the Qdrant payload."""
    if len(embedded.vector) != vector_size:
        raise ValueError(
            "embedding dimension mismatch: "
            f"expected {vector_size}, got {len(embedded.vector)}"
        )
    payload = {
        "point_key": stable_point_key(embedded, chunk),
        "chunk_id": embedded.chunk_id,
        "note_id": embedded.note_id,
        "chunk_index": embedded.chunk_index,
        "chunking_version": embedded.chunking_version,
        "text": chunk.get("text"),
        "section_title": chunk.get("section_title"),
        "section_level": chunk.get("section_level"),
        "section_path": chunk.get("section_path"),
        "source_path": chunk.get("source_path"),
        "start_offset": chunk.get("start_offset"),
        "end_offset": chunk.get("end_offset"),
    }
    text_value = payload.get("text")
    if not isinstance(text_value, str) or not text_value.strip():
        raise ValueError("chunk text must be a non-empty string")
    section_path = payload.get("section_path")
    if section_path is None:
        section_path = []
    return {
        "index_generation": index_generation,
        "point_key": stable_point_key(embedded, chunk),
        "chunk_id": embedded.chunk_id,
        "note_id": embedded.note_id,
        "chunk_index": embedded.chunk_index,
        "chunking_version": embedded.chunking_version,
        "text": text_value,
        "section_title": payload.get("section_title"),
        "section_level": payload.get("section_level"),
        "section_path": section_path,
        "source_path": payload.get("source_path"),
        "start_offset": payload.get("start_offset"),
        "end_offset": payload.get("end_offset"),
        "vector_dimension": vector_size,
        "embedding": list(embedded.vector),
    }


def _existing_vector_dimension(connection: object, *, table_name: str) -> int | None:
    """Read the table's declared vector dimension, or None if missing."""
    inspector = inspect(connection)
    if not inspector.has_table(table_name):
        return None
    result = connection.execute(  # type: ignore[union-attr]
        text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname = current_schema()
              AND c.relname = :table_name
              AND a.attname = 'embedding'
              AND NOT a.attisdropped
            """
        ),
        {"table_name": table_name},
    )
    type_name = result.scalar_one_or_none()
    if not isinstance(type_name, str):
        return None
    return dimension_from_pgvector_type(type_name)


def dimension_from_pgvector_type(type_name: str) -> int | None:
    """Parse ``vector(384)`` from ``format_type``. Do not use atttypmod-4.

    ``varchar(n)`` stores ``atttypmod = n + 4``. pgvector stores the dimension
    itself, so subtracting 4 turns a real 384-d table into a fake 380.
    """
    match = re.search(r"vector\((\d+)\)", type_name)
    if match is None:
        return None
    dimension = int(match.group(1))
    if dimension <= 0:
        return None
    return dimension


def _register_vector_on_engine(engine: Engine) -> None:
    """Create the vector extension, then register adapters on each connection.

    ``register_vector`` looks up the ``vector`` type in pg_catalog. The type
    exists only after ``CREATE EXTENSION vector``, so the extension must be
    created on the same connection first.
    """
    if engine.dialect.name != "postgresql":
        return
    engine_id = id(engine)
    if engine_id in _REGISTERED_ENGINE_IDS:
        return

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: object, _connection_record: object) -> None:
        _ensure_vector_extension(dbapi_connection)
        register_vector(dbapi_connection)

    _REGISTERED_ENGINE_IDS.add(engine_id)


def _ensure_vector_extension(dbapi_connection: object) -> None:
    """Create ``vector`` before pgvector adapters query pg_type."""
    execute = getattr(dbapi_connection, "execute", None)
    if callable(execute):
        execute("CREATE EXTENSION IF NOT EXISTS vector")
        return
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        cursor.close()
