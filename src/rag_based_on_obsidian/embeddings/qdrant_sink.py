"""Direct persistence of validated embedding batches in Qdrant."""

import re
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from rag_based_on_obsidian.embeddings.pipeline import (
    ChunkRow,
    EmbeddedChunk,
)


class QdrantVectorSink:
    """Upsert validated embedding batches into one versioned collection."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        vector_size: int,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.ensure_collection()

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        collection_name: str,
        vector_size: int,
    ) -> "QdrantVectorSink":
        """Create a sink connected to a local or remote Qdrant endpoint."""
        return cls(
            QdrantClient(url=url),
            collection_name=collection_name,
            vector_size=vector_size,
        )

    def ensure_collection(self) -> None:
        """Create the collection once, preserving an existing compatible one."""
        if self.client.collection_exists(collection_name=self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    def upsert_batch(
        self,
        embeddings: Sequence[EmbeddedChunk],
        chunks: Sequence[ChunkRow],
    ) -> None:
        """Upsert one validated batch with chunk metadata as payload."""
        if len(embeddings) != len(chunks):
            raise ValueError("embedding and chunk batch sizes must match")

        points = [
            PointStruct(
                id=embedded.chunk_id,
                vector=list(embedded.vector),
                payload=_payload_for_chunk(embedded, chunk),
            )
            for embedded, chunk in zip(embeddings, chunks, strict=True)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )


def versioned_collection_name(base_name: str, version: str) -> str:
    """Return a stable Qdrant collection name for one index generation."""
    normalized_base = _normalize_name(base_name)
    normalized_version = _normalize_name(version)
    return f"{normalized_base}__{normalized_version}"


def _payload_for_chunk(
    embedded: EmbeddedChunk,
    chunk: ChunkRow,
) -> dict[str, object]:
    """Build a retrieval payload without persisting the vector itself."""
    return {
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


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    normalized = normalized.strip("-_")
    if not normalized:
        raise ValueError("collection name component must not be empty")
    return normalized.lower()
