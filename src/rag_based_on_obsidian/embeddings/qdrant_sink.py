"""Direct persistence of validated embedding batches in Qdrant."""

import re
from collections.abc import Sequence
from time import perf_counter, sleep

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from rag_based_on_obsidian.embeddings.pipeline import (
    ChunkRow,
    EmbeddedChunk,
    SinkWriteError,
    SinkWriteResult,
)
from rag_based_on_obsidian.storage_identity import point_id_from_key
from rag_based_on_obsidian.storage_identity import (
    stable_point_key as build_stable_point_key,
)


class QdrantVectorSink:
    """Upsert validated embedding batches into one versioned collection."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        vector_size: int,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.0,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.ensure_collection()

    @classmethod
    def from_url(
        cls,
        url: str,
        *,
        collection_name: str,
        vector_size: int,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.0,
    ) -> "QdrantVectorSink":
        """Create a sink connected to a local or remote Qdrant endpoint."""
        return cls(
            QdrantClient(url=url),
            collection_name=collection_name,
            vector_size=vector_size,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    def ensure_collection(self) -> None:
        """Create the collection once, preserving an existing compatible one."""
        if self.client.collection_exists(collection_name=self.collection_name):
            collection = self.client.get_collection(
                collection_name=self.collection_name
            )
            actual_vectors = collection.config.params.vectors
            actual_size = getattr(actual_vectors, "size", None)
            if actual_size != self.vector_size:
                raise ValueError(
                    f"Qdrant collection dimension mismatch: "
                    f"expected {self.vector_size}, got {actual_size}"
                )
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
    ) -> SinkWriteResult:
        """Upsert one validated batch with chunk metadata as payload."""
        if len(embeddings) != len(chunks):
            raise ValueError("embedding and chunk batch sizes must match")
        if not embeddings:
            return SinkWriteResult(
                points_written=0,
                duration_seconds=0.0,
                attempts=0,
                vector_bytes=0,
            )

        points = [
            PointStruct(
                id=point_id_for_chunk(embedded, chunk),
                vector=list(embedded.vector),
                payload=_payload_for_chunk(embedded, chunk),
            )
            for embedded, chunk in zip(embeddings, chunks, strict=True)
        ]
        started_at = perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,
                )
                return SinkWriteResult(
                    points_written=len(points),
                    duration_seconds=perf_counter() - started_at,
                    attempts=attempt,
                    vector_bytes=len(points) * self.vector_size * 4,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt <= self.max_retries:
                    sleep(self.retry_backoff_seconds)

        assert last_error is not None
        raise SinkWriteError(
            f"Qdrant upsert failed after {self.max_retries + 1} attempts: "
            f"{last_error}",
            attempts=self.max_retries + 1,
        ) from last_error

    def count_points(self) -> int:
        """Return the exact number of points currently in the collection."""
        return int(
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        )


def versioned_collection_name(
    base_name: str,
    chunking_version: str,
    *,
    model_name: str,
    model_revision: str,
    vector_size: int,
) -> str:
    """Return a collection name for one complete embedding index generation."""
    if vector_size <= 0:
        raise ValueError("vector_size must be positive")
    normalized_base = _normalize_name(base_name)
    normalized_chunking = _normalize_name(chunking_version)
    normalized_model = _normalize_name(model_name)
    normalized_revision = _normalize_name(model_revision)
    return (
        f"{normalized_base}__{normalized_chunking}__{normalized_model}"
        f"__{normalized_revision}__{vector_size}"
    )


def _payload_for_chunk(
    embedded: EmbeddedChunk,
    chunk: ChunkRow,
) -> dict[str, object]:
    """Build a retrieval payload without persisting the vector itself."""
    return {
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


def stable_point_key(embedded: EmbeddedChunk, chunk: ChunkRow) -> str:
    """Build an identity independent of PostgreSQL identity sequences."""
    source_path = chunk.get("source_path")
    source_hash = chunk.get("source_content_hash")
    if not isinstance(source_path, str) or not source_path.strip():
        raise ValueError("chunk source_path must be a non-empty string")
    if not isinstance(source_hash, str) or not source_hash.strip():
        raise ValueError("chunk source_content_hash must be a non-empty string")
    return build_stable_point_key(
        source_path=source_path,
        source_content_hash=source_hash,
        chunking_version=embedded.chunking_version,
        chunk_index=embedded.chunk_index,
    )


def point_id_for_chunk(embedded: EmbeddedChunk, chunk: ChunkRow) -> str:
    """Return the deterministic UUID used as the Qdrant point ID."""
    return point_id_from_key(stable_point_key(embedded, chunk))


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    normalized = normalized.strip("-_")
    if not normalized:
        raise ValueError("collection name component must not be empty")
    return normalized.lower()
