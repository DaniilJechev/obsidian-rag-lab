"""Unit tests for direct Qdrant batch persistence."""

from types import SimpleNamespace
from typing import Any

import pytest
from qdrant_client.models import Document, Modifier

from rag_based_on_obsidian.embeddings.pipeline import (
    EmbeddedChunk,
    SinkWriteError,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    QdrantVectorSink,
    point_id_for_chunk,
    versioned_collection_name,
)


class FakeQdrantClient:
    """Small Qdrant client double that records collection and upsert calls."""

    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.created: list[dict[str, Any]] = []
        self.upserts: list[dict[str, Any]] = []
        self.failures_before_success = 0

    def collection_exists(self, *, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, **kwargs: Any) -> None:
        self.collections.add(kwargs["collection_name"])
        self.created.append(kwargs)

    def get_collection(self, *, collection_name: str) -> Any:
        created = next(
            item
            for item in self.created
            if item.get("collection_name") == collection_name
        )
        return SimpleNamespace(
            config=SimpleNamespace(
                params=SimpleNamespace(
                    vectors=created["vectors_config"],
                    sparse_vectors=created.get("sparse_vectors_config"),
                ),
            )
        )

    def upsert(self, **kwargs: Any) -> None:
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("temporary Qdrant failure")
        self.upserts.append(kwargs)


def test_versioned_collection_name_is_stable() -> None:
    assert (
        versioned_collection_name(
            "rag_chunks",
            "sprint9-policy-512-v2",
            model_name="intfloat/multilingual-e5-small",
            model_revision="main",
            vector_size=384,
        )
        == "rag_chunks__sprint9-policy-512-v2__intfloat-multilingual-e5-small"
        "__main__384"
    )


def test_sink_creates_collection_and_upserts_payload() -> None:
    client = FakeQdrantClient()
    sink = QdrantVectorSink(
        client,
        collection_name="rag_chunks__chunk-v1",
        vector_size=2,
    )

    embedded = EmbeddedChunk(
        chunk_id=7,
        note_id=3,
        chunk_index=1,
        chunking_version="chunk-v1",
        vector=(0.6, 0.8),
    )
    sink.upsert_batch(
        [embedded],
        [
            {
                "chunk_id": 7,
                "note_id": 3,
                "chunk_index": 1,
                "chunking_version": "chunk-v1",
                "text": "Attention context",
                "section_path": ["ML", "Attention"],
                "source_path": "DLS1/attention.md",
                "source_content_hash": "hash-1",
            }
        ],
    )

    assert len(client.created) == 1
    created = client.created[0]
    assert created["collection_name"] == "rag_chunks__chunk-v1"
    assert DENSE_VECTOR_NAME in created["vectors_config"]
    assert created["vectors_config"][DENSE_VECTOR_NAME].size == 2
    assert SPARSE_VECTOR_NAME in created["sparse_vectors_config"]
    assert created["sparse_vectors_config"][SPARSE_VECTOR_NAME].modifier == Modifier.IDF
    assert len(client.upserts) == 1
    point = client.upserts[0]["points"][0]
    assert point.id == point_id_for_chunk(
        embedded,
        {
            "source_path": "DLS1/attention.md",
            "source_content_hash": "hash-1",
        },
    )
    assert point.vector[DENSE_VECTOR_NAME] == [0.6, 0.8]
    assert isinstance(point.vector[SPARSE_VECTOR_NAME], Document)
    assert point.vector[SPARSE_VECTOR_NAME].text == "Attention context"
    assert point.payload["chunking_version"] == "chunk-v1"
    assert point.payload["section_path"] == ["ML", "Attention"]


def test_sink_rejects_mismatched_batch_lengths() -> None:
    sink = QdrantVectorSink(
        FakeQdrantClient(),
        collection_name="rag_chunks__chunk-v1",
        vector_size=2,
    )

    try:
        sink.upsert_batch(
            [
                EmbeddedChunk(
                    chunk_id=1,
                    note_id=1,
                    chunk_index=0,
                    chunking_version="chunk-v1",
                    vector=(0.6, 0.8),
                )
            ],
            [],
        )
    except ValueError as error:
        assert str(error) == "embedding and chunk batch sizes must match"
    else:
        raise AssertionError("expected mismatched batch lengths to fail")


def test_sink_retries_transient_upsert_failure() -> None:
    client = FakeQdrantClient()
    client.failures_before_success = 1
    sink = QdrantVectorSink(
        client,
        collection_name="rag_chunks__chunk-v1",
        vector_size=2,
        max_retries=1,
    )

    result = sink.upsert_batch(
        [
            EmbeddedChunk(
                chunk_id=1,
                note_id=1,
                chunk_index=0,
                chunking_version="chunk-v1",
                vector=(0.6, 0.8),
            )
        ],
            [
                {
                    "text": "retry",
                    "source_path": "DLS1/retry.md",
                    "source_content_hash": "hash-retry",
                }
            ],
    )

    assert result.attempts == 2
    assert result.points_written == 1


def test_sink_raises_after_retry_budget_is_exhausted() -> None:
    client = FakeQdrantClient()
    client.failures_before_success = 3
    sink = QdrantVectorSink(
        client,
        collection_name="rag_chunks__chunk-v1",
        vector_size=2,
        max_retries=1,
    )

    with pytest.raises(SinkWriteError, match="after 2 attempts"):
        sink.upsert_batch(
            [
                EmbeddedChunk(
                    chunk_id=1,
                    note_id=1,
                    chunk_index=0,
                    chunking_version="chunk-v1",
                    vector=(0.6, 0.8),
                )
            ],
            [
                {
                    "text": "failure",
                    "source_path": "DLS1/failure.md",
                    "source_content_hash": "hash-failure",
                }
            ],
        )


def test_sink_rejects_unnamed_legacy_collection() -> None:
    client = FakeQdrantClient()
    client.collections.add("legacy-unnamed")
    client.created.append(
        {
            "collection_name": "legacy-unnamed",
            "vectors_config": SimpleNamespace(size=2),
        }
    )

    with pytest.raises(TypeError, match="unnamed dense vectors"):
        QdrantVectorSink(
            client,
            collection_name="legacy-unnamed",
            vector_size=2,
        )


def test_sink_rejects_named_dense_without_sparse_slot() -> None:
    client = FakeQdrantClient()
    client.collections.add("dense-only")
    client.created.append(
        {
            "collection_name": "dense-only",
            "vectors_config": {
                DENSE_VECTOR_NAME: SimpleNamespace(size=2),
            },
        }
    )

    with pytest.raises(ValueError, match="missing the bm25 sparse vector slot"):
        QdrantVectorSink(
            client,
            collection_name="dense-only",
            vector_size=2,
        )
