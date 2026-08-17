"""Manual synthetic smoke test against a real local Qdrant service."""

from uuid import uuid4

import pytest
from qdrant_client import QdrantClient

from rag_based_on_obsidian.embeddings.pipeline import EmbeddedChunk
from rag_based_on_obsidian.embeddings.qdrant_sink import QdrantVectorSink
from rag_based_on_obsidian.vector_store.settings import QdrantConfig


@pytest.mark.manual
def test_qdrant_direct_upsert_smoke() -> None:
    """Create, upsert, read and clean up one synthetic Qdrant point."""
    config = QdrantConfig(
        url="http://localhost:6333",
        collection=f"rag_smoke__{uuid4().hex}",
    )
    client = QdrantClient(url=config.url)
    sink = QdrantVectorSink(
        client,
        collection_name=config.collection,
        vector_size=2,
        max_retries=1,
    )
    try:
        result = sink.upsert_batch(
            [
                EmbeddedChunk(
                    chunk_id=1,
                    note_id=1,
                    chunk_index=0,
                    chunking_version="smoke-v1",
                    vector=(0.6, 0.8),
                )
            ],
            [
                {
                    "text": "synthetic qdrant smoke",
                    "section_path": ["Smoke"],
                    "source_path": "synthetic/smoke.md",
                    "source_content_hash": "synthetic-hash",
                }
            ],
        )
        points, _ = client.scroll(
            collection_name=config.collection,
            limit=10,
            with_payload=True,
            with_vectors=True,
        )
        assert result.points_written == 1
        assert len(points) == 1
        assert points[0].id == 1
        assert points[0].payload["text"] == "synthetic qdrant smoke"
    finally:
        client.delete_collection(collection_name=config.collection)
