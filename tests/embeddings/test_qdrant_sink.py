"""Unit tests for direct Qdrant batch persistence."""

from typing import Any

from rag_based_on_obsidian.embeddings.pipeline import EmbeddedChunk
from rag_based_on_obsidian.embeddings.qdrant_sink import (
    QdrantVectorSink,
    versioned_collection_name,
)


class FakeQdrantClient:
    """Small Qdrant client double that records collection and upsert calls."""

    def __init__(self) -> None:
        self.collections: set[str] = set()
        self.created: list[dict[str, Any]] = []
        self.upserts: list[dict[str, Any]] = []

    def collection_exists(self, *, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, **kwargs: Any) -> None:
        self.collections.add(kwargs["collection_name"])
        self.created.append(kwargs)

    def upsert(self, **kwargs: Any) -> None:
        self.upserts.append(kwargs)


def test_versioned_collection_name_is_stable() -> None:
    assert (
        versioned_collection_name("rag_chunks", "sprint9-policy-512-v2")
        == "rag_chunks__sprint9-policy-512-v2"
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
            }
        ],
    )

    assert len(client.created) == 1
    assert client.created[0]["collection_name"] == "rag_chunks__chunk-v1"
    assert len(client.upserts) == 1
    point = client.upserts[0]["points"][0]
    assert point.id == 7
    assert point.vector == [0.6, 0.8]
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
