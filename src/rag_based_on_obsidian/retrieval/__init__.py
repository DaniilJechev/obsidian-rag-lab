"""Backend-independent retrieval contracts and implementations."""

from rag_based_on_obsidian.retrieval.contracts import (
    LexicalIndex,
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.fusion import reciprocal_rank_fusion
from rag_based_on_obsidian.retrieval.lexical import QdrantSparseRetriever

__all__ = [
    "LexicalIndex",
    "QdrantSparseRetriever",
    "RetrievalMethod",
    "RetrievedChunk",
    "reciprocal_rank_fusion",
]
