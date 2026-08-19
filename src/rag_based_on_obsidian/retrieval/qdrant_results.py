"""Shared Qdrant query helpers for dense and sparse retrieval."""

from collections.abc import Mapping

from qdrant_client.models import FieldCondition, Filter, MatchValue

from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)

# Keep these names identical to embeddings.qdrant_sink named vector slots.
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"
BM25_MODEL_NAME = "Qdrant/bm25"


def build_payload_filter(
    filters: Mapping[str, object] | None,
) -> Filter | None:
    """Translate scalar metadata filters into a Qdrant Filter."""
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


def point_to_retrieved_chunk(
    point: object,
    *,
    rank: int,
    method: RetrievalMethod,
) -> RetrievedChunk:
    """Map one Qdrant point onto the backend-independent retrieval contract."""
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
    numeric_score = float(score)
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=numeric_score,
        retrieval_method=method,
        metadata=dict(payload),
        chunking_version=chunking_version,
        rank=rank,
        point_key=point_key,
        dense_score=numeric_score if method is RetrievalMethod.DENSE else None,
        bm25_score=numeric_score if method is RetrievalMethod.BM25 else None,
    )
