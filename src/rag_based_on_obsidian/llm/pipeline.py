"""Retrieve, pack, refuse, or call the LLM via LangGraph. No FastAPI types."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from rag_based_on_obsidian.lang_graph.workflow import run_generate_graph
from rag_based_on_obsidian.llm.contracts import LLMProvider
from rag_based_on_obsidian.llm.settings import LLMConfig
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk

SearchFn = Callable[..., Awaitable[list[RetrievedChunk]]]


async def run_rag_generate(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> dict[str, object]:
    """Return a JSON-ready generate payload. May raise LLM errors.

    Sprint 24: thin facade over ``run_generate_graph`` so API/runtime and
    existing tests keep calling this name while the control flow is a graph.
    """

    return await run_generate_graph(
        search,
        provider,
        config,
        query,
        method=method,
        top_k=top_k,
    )
