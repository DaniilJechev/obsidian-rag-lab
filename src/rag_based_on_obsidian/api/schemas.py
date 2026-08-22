"""Pydantic request and response models for the retriever HTTP API."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)


class SearchRequest(BaseModel):
    """JSON body for ``POST /search``. Kitchen (Qdrant, e5) stays inside."""

    query: str
    method: RetrievalMethod = RetrievalMethod.HYBRID
    top_k: int | None = Field(default=None, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only questions before retrieval runs."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped


class SearchHit(BaseModel):
    """One ranked chunk as JSON. No Qdrant point or SQLAlchemy types."""

    chunk_id: int
    text: str
    score: float
    rank: int
    retrieval_method: RetrievalMethod
    chunking_version: str
    point_key: str | None = None
    dense_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_chunk(cls, chunk: RetrievedChunk) -> "SearchHit":
        """Project the internal retrieval contract onto the HTTP schema."""
        return cls(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            score=chunk.score,
            rank=chunk.rank,
            retrieval_method=chunk.retrieval_method,
            chunking_version=chunk.chunking_version,
            point_key=chunk.point_key,
            dense_score=chunk.dense_score,
            bm25_score=chunk.bm25_score,
            rrf_score=chunk.rrf_score,
            metadata=dict(chunk.metadata),
        )


class SearchResponse(BaseModel):
    """Ranked hits plus the method and cutoff actually used."""

    query: str
    method: RetrievalMethod
    top_k: int
    results: list[SearchHit]


class HealthResponse(BaseModel):
    """Liveness plus whether the warm model and Qdrant can serve search."""

    status: str
    model_loaded: bool
    qdrant: str
