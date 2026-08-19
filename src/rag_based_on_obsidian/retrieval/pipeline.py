"""Hybrid retrieval orchestration for dense Qdrant and BM25 backends."""

import asyncio
from collections.abc import Mapping

from rag_based_on_obsidian.embeddings.contracts import EmbeddingProvider
from rag_based_on_obsidian.retrieval.contracts import (
    LexicalIndex,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever
from rag_based_on_obsidian.retrieval.fusion import reciprocal_rank_fusion
from rag_based_on_obsidian.retrieval.progress import logger


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
