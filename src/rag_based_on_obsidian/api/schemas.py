"""Pydantic request and response models for the retriever HTTP API."""

from datetime import datetime
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


class GenerateRequest(SearchRequest):
    """JSON body for ``POST /generate``. Same query fields as ``/search``.

    ``model`` overrides the process default from ``configs/llm/openrouter.yaml``
    for this request only (bake-off / rag-cli ``--generate-model``).
    """

    model: str | None = None

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("model must not be empty when set")
        return stripped


class GenerateCitation(BaseModel):
    """One chunk the model cited. ``note_path`` is filled from retrieval."""

    chunk_id: int
    note_path: str


class PackedContext(BaseModel):
    """One chunk actually packed into the generate prompt."""

    chunk_id: int
    note_path: str
    text: str


class GenerateUsage(BaseModel):
    """Token counts from the LLM provider for this call."""

    prompt_tokens: int
    generated_tokens: int


class GenerateResponse(BaseModel):
    """Structured RAG answer, or a refusal that never called the LLM."""

    query: str
    method: RetrievalMethod
    top_k: int
    answer: str | None
    citations: list[GenerateCitation]
    contexts: list[PackedContext] = Field(default_factory=list)
    confidence: float
    refused: bool
    refusal_reason: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    usage: GenerateUsage | None = None


class PinnedModels(BaseModel):
    """Model pins this stack is configured to use.

    ``judge`` and ``evaluation_embedding`` are applied by ``rag-cli ragas``,
    not by ``POST /generate``. They still come from configs baked into this
    process (Docker image until ``--build``).
    """

    retrieval_embedding: str | None = None
    generate: str | None = None
    judge: str | None = None
    evaluation_embedding: str | None = None


class HealthResponse(BaseModel):
    """Liveness plus whether the warm model, Qdrant, and Postgres can serve."""

    status: str
    model_loaded: bool
    qdrant: str
    postgres: str
    models: PinnedModels


class IngestAccepted(BaseModel):
    """Immediate ack for ``POST /ingest``. Work continues in the background."""

    run_id: int
    status: str


class IngestStatus(BaseModel):
    """One ``ingestion_runs`` row for ``GET /ingest/{run_id}``."""

    run_id: int
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    corpus_scope: str | None = None
    documents_total: int | None = None
    documents_succeeded: int | None = None
    documents_failed: int | None = None
    documents_skipped: int | None = None
