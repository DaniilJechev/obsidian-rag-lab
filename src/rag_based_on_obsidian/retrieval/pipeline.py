"""Hybrid retrieval orchestration for dense Qdrant and BM25 backends."""

import asyncio
from collections.abc import Iterable, Mapping
from typing import Protocol

from rag_based_on_obsidian.embeddings.contracts import EmbeddingProvider
from rag_based_on_obsidian.retrieval.contracts import (
    LexicalIndex,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever
from rag_based_on_obsidian.retrieval.fusion import reciprocal_rank_fusion
from rag_based_on_obsidian.retrieval.lexical import InMemoryBM25Index
from rag_based_on_obsidian.retrieval.progress import logger

type ChunkRow = Mapping[str, object]


class VersionedChunkReader(Protocol):
    """Minimal repository contract needed to build the lexical index."""

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> Iterable[list[dict[str, object]]]:
        """Yield bounded batches for one explicit chunking version."""


class HybridRetriever:
    """Run dense and lexical retrieval, then fuse their rankings."""

    def __init__(
        self,
        *,
        dense: QdrantDenseRetriever,
        lexical: LexicalIndex,
        provider: EmbeddingProvider,
    ) -> None:
        self.dense = dense
        self.lexical = lexical
        self.provider = provider

    @classmethod
    def from_repository(
        cls,
        *,
        dense: QdrantDenseRetriever,
        provider: EmbeddingProvider,
        repository: VersionedChunkReader,
        chunking_version: str,
        batch_size: int,
    ) -> "HybridRetriever":
        """Build the versioned in-memory BM25 index from PostgreSQL rows."""
        logger.info(
            "stage=bm25_index_load chunking_version=%s batch_size=%s",
            chunking_version,
            batch_size,
        )
        rows = (
            row
            for batch in repository.iter_by_version(
                chunking_version=chunking_version,
                batch_size=batch_size,
            )
            for row in batch
        )
        lexical = InMemoryBM25Index.from_rows(
            rows,
            chunking_version=chunking_version,
        )
        return cls(dense=dense, lexical=lexical, provider=provider)

    async def search(
        self,
        query: str,
        *,
        top_k: int,
        candidate_k: int,
        rrf_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Run independent retrieval branches concurrently via threads."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be at least top_k")

        logger.info("stage=hybrid_embed_query")
        query_vector = await asyncio.to_thread(
            self.provider.embed_query,
            query,
        )
        logger.info("stage=hybrid_fanout dense+bm25 candidate_k=%s", candidate_k)
        dense_task = asyncio.to_thread(
            self.dense.search_vector,
            query_vector,
            top_k=candidate_k,
            filters=filters,
        )
        lexical_task = asyncio.to_thread(
            self.lexical.search,
            query,
            top_k=candidate_k,
            filters=filters,
        )
        dense_results, lexical_results = await asyncio.gather(
            dense_task,
            lexical_task,
        )
        logger.info(
            "stage=hybrid_rrf dense_hits=%s bm25_hits=%s top_k=%s",
            len(dense_results),
            len(lexical_results),
            top_k,
        )
        fused = reciprocal_rank_fusion(
            (dense_results, lexical_results),
            top_k=top_k,
            rrf_k=rrf_k,
        )
        logger.info("stage=hybrid_rrf_done hits=%s", len(fused))
        return fused
