"""Dense Qdrant retrieval using the existing embedding provider contract."""

from collections.abc import Mapping

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingProvider,
    EmbeddingVector,
)
from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)


class QdrantDenseRetriever:
    """Search one versioned Qdrant collection and map payloads to chunks."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        provider: EmbeddingProvider,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        self.client = client
        self.collection_name = collection_name
        self.provider = provider

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Embed one query and execute dense search."""
        return self.search_vector(
            self.provider.embed_query(query),
            top_k=top_k,
            filters=filters,
        )

    def search_vector(
        self,
        vector: EmbeddingVector,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Search with a precomputed query vector for hybrid fan-out."""
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        expected_dimension = self.provider.metadata.dimension
        if len(vector) != expected_dimension:
            raise ValueError(
                f"query vector dimension mismatch: expected "
                f"{expected_dimension}, got {len(vector)}"
            )
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=list(vector),
            query_filter=_build_filter(filters),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        points = getattr(response, "points", response)
        return [
            _point_to_chunk(point, rank=rank)
            for rank, point in enumerate(points, start=1)
        ]


def _build_filter(
    filters: Mapping[str, object] | None,
) -> Filter | None:
    if not filters:
        return None
    conditions = [
        FieldCondition(
            key=key,
            match=MatchValue(value=value),
        )
        for key, value in filters.items()
        if isinstance(value, str | int | float | bool)
    ]
    if len(conditions) != len(filters):
        raise TypeError("Qdrant filters must contain scalar values")
    return Filter(must=conditions)


def _point_to_chunk(point: object, *, rank: int) -> RetrievedChunk:
    payload = getattr(point, "payload", None) or {}
    if not isinstance(payload, Mapping):
        raise TypeError("Qdrant point payload must be a mapping")
    chunk_id = payload.get("chunk_id")
    text = payload.get("text")
    chunking_version = payload.get("chunking_version")
    point_key = payload.get("point_key")
    score = getattr(point, "score", None)
    if not isinstance(chunk_id, int):
        raise TypeError("Qdrant payload chunk_id must be an integer")
    if not isinstance(text, str):
        raise TypeError("Qdrant payload text must be a string")
    if not isinstance(chunking_version, str):
        raise TypeError("Qdrant payload chunking_version must be a string")
    if not isinstance(point_key, str):
        raise TypeError("Qdrant payload point_key must be a string")
    if not isinstance(score, int | float):
        raise TypeError("Qdrant point score must be numeric")
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=float(score),
        retrieval_method=RetrievalMethod.DENSE,
        metadata=dict(payload),
        chunking_version=chunking_version,
        rank=rank,
        point_key=point_key,
        dense_score=float(score),
    )
