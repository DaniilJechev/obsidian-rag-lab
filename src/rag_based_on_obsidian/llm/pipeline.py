"""Retrieve, pack, refuse, or call the LLM via LangGraph. No FastAPI types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from rag_based_on_obsidian.cache.semantic_store import SemanticCacheStore
from rag_based_on_obsidian.cache.settings import CacheConfig
from rag_based_on_obsidian.llm.contracts import LLMProvider
from rag_based_on_obsidian.llm.settings import LLMConfig
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.rerank import Reranker
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig

SearchFn = Callable[..., Awaitable[list[RetrievedChunk]]]
EmbedQueryFn = Callable[[str], tuple[float, ...]]


async def run_rag_generate(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
    candidate_k: int | None = None,
    reranker: Reranker | None = None,
    rerank_config: RerankConfig | None = None,
    cache_config: CacheConfig | None = None,
    cache_store: SemanticCacheStore | None = None,
    embed_query: EmbedQueryFn | None = None,
    pipeline_version: str | None = None,
) -> dict[str, object]:
    """Return a JSON-ready generate payload. May raise LLM errors.

    Sprint 24+: thin facade over ``run_generate_graph`` so API/runtime and
    existing tests keep calling this name while the control flow is a graph.
    """
    # Lazy import avoids: workflow → llm.contracts → llm.__init__ → pipeline → workflow
    from rag_based_on_obsidian.lang_graph.workflow import run_generate_graph

    return await run_generate_graph(
        search,
        provider,
        config,
        query,
        method=method,
        top_k=top_k,
        candidate_k=candidate_k,
        reranker=reranker,
        rerank_config=rerank_config,
        cache_config=cache_config,
        cache_store=cache_store,
        embed_query=embed_query,
        pipeline_version=pipeline_version,
    )
