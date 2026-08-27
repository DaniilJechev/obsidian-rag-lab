"""One-shot Qdrant retrieval session for live eval: load the embedder once."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import TracebackType
from typing import Self

from qdrant_client import QdrantClient

from rag_based_on_obsidian.embeddings.qdrant_sink import versioned_collection_name
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    EmbeddingModelConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever
from rag_based_on_obsidian.retrieval.lexical import QdrantSparseRetriever
from rag_based_on_obsidian.retrieval.pipeline import HybridRetriever
from rag_based_on_obsidian.retrieval.rerank import Reranker, build_reranker
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig
from rag_based_on_obsidian.retrieval.settings import RetrievalConfig
from rag_based_on_obsidian.vector_store.settings import load_qdrant_config

RetrieveFn = Callable[[str], list[RetrievedChunk]]


@dataclass(frozen=True)
class LiveSessionInfo:
    """Reproducibility fields logged with a live eval run."""

    method: RetrievalMethod
    collection_name: str
    chunking_version: str
    top_k: int
    candidate_k: int
    rrf_k: int
    model_name: str
    model_revision: str
    device: str
    dimension: int
    normalized: bool
    max_length: int
    batch_size: int
    rerank_enabled: bool = False
    rerank_model_name: str | None = None
    rerank_max_length: int | None = None
    rerank_batch_size: int | None = None


class LiveRetrievalSession:
    """Hold one Qdrant client and optional embedder across many queries."""

    def __init__(
        self,
        *,
        client: QdrantClient,
        retrieve: RetrieveFn,
        info: LiveSessionInfo,
    ) -> None:
        self._client = client
        self._retrieve = retrieve
        self.info = info

    def search(self, query: str) -> list[RetrievedChunk]:
        """Run one query against the already-loaded retriever."""
        return self._retrieve(query)

    def close(self) -> None:
        """Release the Qdrant client."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        self.close()


def open_live_session(
    *,
    method: RetrievalMethod,
    retrieval_config: RetrievalConfig,
    model_config_path: Path,
    batch_config_path: Path,
    qdrant_config_path: Path,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
    enable_rerank: bool = False,
) -> LiveRetrievalSession:
    """Build retrievers for one method; load e5 only for dense and hybrid."""
    if enable_rerank and method is not RetrievalMethod.HYBRID:
        raise ValueError("enable_rerank requires --method hybrid")
    model_config = load_embedding_model_config(model_config_path)
    batch_config = load_batch_embedding_config(batch_config_path)
    qdrant_config = load_qdrant_config(qdrant_config_path)
    client = QdrantClient(url=qdrant_config.url)
    filters = dict(retrieval_config.filters)
    chunking_version = retrieval_config.chunking_version
    rerank_config = _active_rerank_config(retrieval_config.rerank, enable_rerank)
    try:
        if method is RetrievalMethod.BM25:
            collection_name = _collection_name(
                qdrant_config.collection,
                batch_config,
                model_config,
            )
            retriever = QdrantSparseRetriever(
                client,
                collection_name=collection_name,
                chunking_version=chunking_version,
                bm25_avg_len=qdrant_config.bm25_avg_len,
                bm25_model=qdrant_config.bm25_model,
            )

            def retrieve_bm25(query: str) -> list[RetrievedChunk]:
                return retriever.search(query, top_k=top_k, filters=filters)

            return LiveRetrievalSession(
                client=client,
                retrieve=retrieve_bm25,
                info=_info_from_config(
                    method=method,
                    collection_name=collection_name,
                    chunking_version=chunking_version,
                    top_k=top_k,
                    candidate_k=candidate_k,
                    rrf_k=rrf_k,
                    model_config=model_config,
                    device="n/a",
                    rerank_config=rerank_config,
                ),
            )

        provider = TransformersEmbeddingProvider(model_config)
        collection_name = versioned_collection_name(
            qdrant_config.collection,
            batch_config.chunking_version,
            model_name=provider.metadata.model_name,
            model_revision=provider.metadata.model_revision,
            vector_size=provider.metadata.dimension,
        )
        dense = QdrantDenseRetriever(
            client,
            collection_name=collection_name,
            provider=provider,
        )
        lexical = None
        if method is RetrievalMethod.HYBRID:
            lexical = QdrantSparseRetriever(
                client,
                collection_name=collection_name,
                chunking_version=chunking_version,
                bm25_avg_len=qdrant_config.bm25_avg_len,
                bm25_model=qdrant_config.bm25_model,
            )
        retrieve = _dense_or_hybrid_retrieve(
            method=method,
            dense=dense,
            lexical=lexical,
            provider=provider,
            top_k=top_k,
            candidate_k=candidate_k,
            rrf_k=rrf_k,
            filters=filters,
            rerank_config=rerank_config,
        )
        return LiveRetrievalSession(
            client=client,
            retrieve=retrieve,
            info=LiveSessionInfo(
                method=method,
                collection_name=collection_name,
                chunking_version=chunking_version,
                top_k=top_k,
                candidate_k=candidate_k,
                rrf_k=rrf_k,
                model_name=provider.metadata.model_name,
                model_revision=provider.metadata.model_revision,
                device=provider.metadata.device,
                dimension=provider.metadata.dimension,
                normalized=provider.metadata.normalized,
                max_length=model_config.max_length,
                batch_size=model_config.batch_size,
                rerank_enabled=rerank_config.enabled,
                rerank_model_name=(
                    rerank_config.model_name if rerank_config.enabled else None
                ),
                rerank_max_length=(
                    rerank_config.max_length if rerank_config.enabled else None
                ),
                rerank_batch_size=(
                    rerank_config.batch_size if rerank_config.enabled else None
                ),
            ),
        )
    except Exception:
        client.close()
        raise


def _active_rerank_config(base: RerankConfig, enable_rerank: bool) -> RerankConfig:
    """CLI ``--enable-rerank`` overrides YAML ``enabled`` for this session only."""
    return replace(base, enabled=enable_rerank)


def _dense_or_hybrid_retrieve(
    *,
    method: RetrievalMethod,
    dense: QdrantDenseRetriever,
    lexical: QdrantSparseRetriever | None,
    provider: TransformersEmbeddingProvider,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
    filters: Mapping[str, object],
    rerank_config: RerankConfig,
) -> RetrieveFn:
    if method is RetrievalMethod.DENSE:

        def retrieve_dense(query: str) -> list[RetrievedChunk]:
            return dense.search(query, top_k=top_k, filters=filters)

        return retrieve_dense

    if lexical is None:
        raise ValueError("hybrid eval requires a lexical retriever")
    hybrid = HybridRetriever(dense=dense, lexical=lexical, provider=provider)
    if not rerank_config.enabled:

        def retrieve_hybrid(query: str) -> list[RetrievedChunk]:
            return asyncio.run(
                hybrid.search(
                    query,
                    top_k=top_k,
                    candidate_k=candidate_k,
                    rrf_k=rrf_k,
                    filters=filters,
                )
            )

        return retrieve_hybrid

    reranker: Reranker = build_reranker(rerank_config)
    reranker.ensure_loaded()

    def retrieve_hybrid_rerank(query: str) -> list[RetrievedChunk]:
        pool = asyncio.run(
            hybrid.search(
                query,
                top_k=candidate_k,
                candidate_k=candidate_k,
                rrf_k=rrf_k,
                filters=filters,
            )
        )
        return reranker.rerank(query, pool, top_k=top_k)

    return retrieve_hybrid_rerank


def _collection_name(
    base_name: str,
    batch_config: BatchEmbeddingConfig,
    model_config: EmbeddingModelConfig,
) -> str:
    if model_config.dimension is None:
        raise ValueError("model config must define dimension for BM25 eval")
    return versioned_collection_name(
        base_name,
        batch_config.chunking_version,
        model_name=model_config.model_name,
        model_revision=model_config.model_revision,
        vector_size=model_config.dimension,
    )


def _info_from_config(
    *,
    method: RetrievalMethod,
    collection_name: str,
    chunking_version: str,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
    model_config: EmbeddingModelConfig,
    device: str,
    rerank_config: RerankConfig,
) -> LiveSessionInfo:
    if model_config.dimension is None:
        raise ValueError("model config must define dimension")
    return LiveSessionInfo(
        method=method,
        collection_name=collection_name,
        chunking_version=chunking_version,
        top_k=top_k,
        candidate_k=candidate_k,
        rrf_k=rrf_k,
        model_name=model_config.model_name,
        model_revision=model_config.model_revision,
        device=device,
        dimension=model_config.dimension,
        normalized=model_config.normalized,
        max_length=model_config.max_length,
        batch_size=model_config.batch_size,
        rerank_enabled=rerank_config.enabled,
        rerank_model_name=(
            rerank_config.model_name if rerank_config.enabled else None
        ),
        rerank_max_length=(
            rerank_config.max_length if rerank_config.enabled else None
        ),
        rerank_batch_size=(
            rerank_config.batch_size if rerank_config.enabled else None
        ),
    )
