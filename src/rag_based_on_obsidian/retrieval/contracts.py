"""Backend-independent contracts for retrieval results."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class RetrievalMethod(StrEnum):
    """Supported retrieval paths exposed to callers."""

    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"


class LexicalIndex(Protocol):
    """Backend-independent lexical search contract."""

    chunking_version: str

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list["RetrievedChunk"]:
        """Return ranked chunks from one explicit corpus version."""


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked chunk without exposing backend-specific result types."""

    chunk_id: int
    text: str
    score: float
    retrieval_method: RetrievalMethod
    metadata: Mapping[str, object]
    chunking_version: str
    rank: int
    point_key: str | None = None
    dense_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None

    def __post_init__(self) -> None:
        """Reject incomplete or non-deterministic retrieval records."""
        if self.chunk_id <= 0:
            raise ValueError("chunk_id must be positive")
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if not self.chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        if self.rank <= 0:
            raise ValueError("rank must be positive")


def retrieval_key(chunk: RetrievedChunk) -> str:
    """Return the stable identity used for fusion and deduplication."""
    return chunk.point_key or (
        f"{chunk.chunk_id}:{chunk.chunking_version}"
    )
