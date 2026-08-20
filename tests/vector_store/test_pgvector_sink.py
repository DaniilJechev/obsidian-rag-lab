"""Unit tests for the experimental pgvector dense sink."""

from unittest.mock import MagicMock

import pytest

from rag_based_on_obsidian.embeddings.pipeline import EmbeddedChunk, SinkWriteError
from rag_based_on_obsidian.embeddings.qdrant_sink import stable_point_key
from rag_based_on_obsidian.vector_store.pgvector_sink import (
    PgvectorVectorSink,
    _row_for_chunk,
)


def _chunk_row() -> dict[str, object]:
    return {
        "text": "Attention context",
        "section_path": ["ML", "Attention"],
        "source_path": "DLS1/attention.md",
        "source_content_hash": "hash-1",
        "section_title": "Attention",
        "section_level": 2,
        "start_offset": 0,
        "end_offset": 18,
    }


def _embedded() -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=7,
        note_id=3,
        chunk_index=1,
        chunking_version="chunk-v1",
        vector=(0.6, 0.8),
    )


def test_row_uses_qdrant_stable_point_key() -> None:
    embedded = _embedded()
    chunk = _chunk_row()
    row = _row_for_chunk(
        embedded,
        chunk,
        index_generation="gen-1",
        vector_size=2,
    )
    assert row["point_key"] == stable_point_key(embedded, chunk)
    assert row["index_generation"] == "gen-1"
    assert row["embedding"] == [0.6, 0.8]
    assert row["chunk_id"] == 7
    assert row["vector_dimension"] == 2


def test_row_rejects_dimension_mismatch() -> None:
    with pytest.raises(ValueError, match="embedding dimension mismatch"):
        _row_for_chunk(
            _embedded(),
            _chunk_row(),
            index_generation="gen-1",
            vector_size=3,
        )


def _sink_with_mock_engine(monkeypatch: pytest.MonkeyPatch) -> tuple[PgvectorVectorSink, MagicMock]:
    engine = MagicMock()
    engine.dialect.name = "sqlite"
    monkeypatch.setattr(PgvectorVectorSink, "ensure_schema", lambda self: None)
    sink = PgvectorVectorSink(
        engine,
        index_generation="gen-1",
        vector_size=2,
    )
    return sink, engine


def test_upsert_batch_writes_on_conflict_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    sink, engine = _sink_with_mock_engine(monkeypatch)
    connection = MagicMock()
    engine.begin.return_value.__enter__.return_value = connection

    result = sink.upsert_batch([_embedded()], [_chunk_row()])

    assert result.points_written == 1
    assert result.attempts == 1
    connection.execute.assert_called_once()


def test_upsert_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sink, engine = _sink_with_mock_engine(monkeypatch)
    sink.max_retries = 1
    connection = MagicMock()
    connection.execute.side_effect = [RuntimeError("temp"), None]
    engine.begin.return_value.__enter__.return_value = connection

    result = sink.upsert_batch([_embedded()], [_chunk_row()])

    assert result.attempts == 2
    assert result.points_written == 1


def test_upsert_raises_after_retry_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    sink, engine = _sink_with_mock_engine(monkeypatch)
    sink.max_retries = 1
    connection = MagicMock()
    connection.execute.side_effect = RuntimeError("permanent")
    engine.begin.return_value.__enter__.return_value = connection

    with pytest.raises(SinkWriteError, match="after 2 attempts"):
        sink.upsert_batch([_embedded()], [_chunk_row()])


def test_sink_rejects_mismatched_batch_lengths(monkeypatch: pytest.MonkeyPatch) -> None:
    sink, _engine = _sink_with_mock_engine(monkeypatch)
    with pytest.raises(ValueError, match="batch sizes must match"):
        sink.upsert_batch([_embedded()], [])


def test_pgvector_config_rejects_unsafe_table_name() -> None:
    from rag_based_on_obsidian.vector_store.pgvector_settings import PgvectorConfig

    with pytest.raises(ValueError, match="plain SQL identifier"):
        PgvectorConfig(table="chunk; drop")


def test_pgvector_dimension_is_read_from_format_type_not_varchar_typmod() -> None:
    from rag_based_on_obsidian.vector_store.pgvector_sink import (
        dimension_from_pgvector_type,
    )

    assert dimension_from_pgvector_type("vector(384)") == 384
    assert dimension_from_pgvector_type("public.vector(384)") == 384
    assert dimension_from_pgvector_type("vector") is None


def test_connect_hook_creates_extension_before_register() -> None:
    from rag_based_on_obsidian.vector_store.pgvector_sink import (
        _ensure_vector_extension,
    )

    class FakeConnection:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, statement: str) -> None:
            self.statements.append(statement)

    connection = FakeConnection()
    _ensure_vector_extension(connection)
    assert connection.statements == ["CREATE EXTENSION IF NOT EXISTS vector"]
