"""Backend-independent retrieval contracts and implementations."""

from rag_based_on_obsidian.retrieval.contracts import (
    LexicalIndex,
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.fusion import reciprocal_rank_fusion
from rag_based_on_obsidian.retrieval.lexical import InMemoryBM25Index

__all__ = [
    "InMemoryBM25Index",
    "LexicalIndex",
    "RetrievalMethod",
    "RetrievedChunk",
    "reciprocal_rank_fusion",
]
