"""Direct persistence of validated embedding batches in Qdrant."""

import re
from collections.abc import Mapping, Sequence
from time import perf_counter, sleep

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Document,
    Modifier,
    PointStruct,
    SparseVectorParams,
    VectorParams,
)

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

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"
BM25_MODEL_NAME = "Qdrant/bm25"
DEFAULT_BM25_AVG_LEN = 191.0


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
        bm25_avg_len: float = DEFAULT_BM25_AVG_LEN,
        bm25_model: str = BM25_MODEL_NAME,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative")
        if bm25_avg_len <= 0:
            raise ValueError("bm25_avg_len must be positive")
        if not bm25_model.strip():
            raise ValueError("bm25_model must not be empty")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.bm25_avg_len = bm25_avg_len
        self.bm25_model = bm25_model
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
        bm25_avg_len: float = DEFAULT_BM25_AVG_LEN,
        bm25_model: str = BM25_MODEL_NAME,
    ) -> "QdrantVectorSink":
        """Create a sink connected to a local or remote Qdrant endpoint."""
        return cls(
            QdrantClient(url=url),
            collection_name=collection_name,
            vector_size=vector_size,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            bm25_avg_len=bm25_avg_len,
            bm25_model=bm25_model,
        )

    def ensure_collection(self) -> None:
        """Create the named dense+sparse collection or verify a compatible one."""
        if self.client.collection_exists(collection_name=self.collection_name):
            collection = self.client.get_collection(
                collection_name=self.collection_name
            )
            params = collection.config.params
            actual_size = _dense_vector_size(
                getattr(params, "vectors", None),
                name=DENSE_VECTOR_NAME,
            )
            if actual_size != self.vector_size:
                raise ValueError(
                    f"Qdrant collection dimension mismatch: "
                    f"expected {self.vector_size}, got {actual_size}"
                )
            if not _has_sparse_slot(
                getattr(params, "sparse_vectors", None),
                name=SPARSE_VECTOR_NAME,
            ):
                raise ValueError(
                    "Qdrant collection is missing the bm25 sparse vector slot; "
                    "recreate it with --recreate before sparse search"
                )
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                DENSE_VECTOR_NAME: VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF),
            },
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
                vector=_named_vectors_for_chunk(
                    embedded,
                    chunk,
                    bm25_model=self.bm25_model,
                    bm25_avg_len=self.bm25_avg_len,
                ),
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


def _named_vectors_for_chunk(
    embedded: EmbeddedChunk,
    chunk: ChunkRow,
    *,
    bm25_model: str,
    bm25_avg_len: float,
) -> dict[str, object]:
    """Store dense cosine and BM25 inference input on the same Qdrant point."""
    text = chunk.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("chunk text must be a non-empty string")
    return {
        DENSE_VECTOR_NAME: list(embedded.vector),
        SPARSE_VECTOR_NAME: Document(
            text=text,
            model=bm25_model,
            options={"avg_len": bm25_avg_len},
        ),
    }


def _dense_vector_size(vectors: object, *, name: str) -> int:
    """Read the named dense slot or reject an unnamed legacy collection."""
    if isinstance(vectors, Mapping):
        named = vectors.get(name)
        size = getattr(named, "size", None)
        if isinstance(size, int):
            return size
        raise ValueError(
            f"Qdrant collection is missing the {name} dense vector slot; "
            "recreate it with --recreate before search"
        )
    size = getattr(vectors, "size", None)
    if isinstance(size, int):
        raise TypeError(
            "Qdrant collection uses unnamed dense vectors; "
            "recreate it with --recreate so dense and bm25 share one point"
        )
    raise ValueError("Qdrant collection is missing dense vector configuration")


def _has_sparse_slot(sparse_vectors: object, *, name: str) -> bool:
    """Return whether the collection exposes the BM25 sparse vector slot."""
    return isinstance(sparse_vectors, Mapping) and name in sparse_vectors


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
