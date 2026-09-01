"""LangGraph: semantic_cache → classify → retrieve → rerank → gate → generate → self_check → cache_write.

Sprint 28 adds optional Redis semantic cache (E5 cosine) before classify.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

from rag_based_on_obsidian.cache.semantic_store import SemanticCacheStore
from rag_based_on_obsidian.cache.settings import CacheConfig
from rag_based_on_obsidian.lang_graph.policies import (
    MAX_SELF_CHECK_RETRIES,
    classify_query,
    rewrite_query,
    self_check_generation,
)
from rag_based_on_obsidian.lang_graph.state import GenerateGraphState
from rag_based_on_obsidian.llm.contracts import (
    LLMProvider,
    LLMResponseError,
    LLMUnavailableError,
)
from rag_based_on_obsidian.llm.packing import (
    build_messages,
    estimate_tokens,
    pack_chunks,
    should_refuse,
)
from rag_based_on_obsidian.llm.parser import parse_generation_json
from rag_based_on_obsidian.llm.settings import LLMConfig
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.rerank import IdentityReranker, Reranker
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig

SearchFn = Callable[..., Awaitable[list[RetrievedChunk]]]
EmbedQueryFn = Callable[[str], tuple[float, ...]]
RouteAfterClassify = Literal["retrieve", "refuse"]
RouteAfterGate = Literal["generate", "refuse"]
RouteAfterSelfCheck = Literal["pass", "rewrite"]
RouteAfterCacheLookup = Literal["hit", "miss"]


def _cache_active(
    cache_config: CacheConfig | None,
    cache_store: SemanticCacheStore | None,
) -> bool:
    return bool(
        cache_config is not None
        and cache_config.enabled
        and cache_store is not None
    )


def _response_from_cache(hit_response: dict[str, object]) -> dict[str, object]:
    return {
        "answer": hit_response.get("answer"),
        "citations": list(hit_response.get("citations") or []),
        "contexts": list(hit_response.get("contexts") or []),
        "confidence": float(hit_response.get("confidence") or 0.0),
        "refused": False,
        "model": hit_response.get("model"),
        "latency_ms": hit_response.get("latency_ms"),
        "usage": hit_response.get("usage"),
    }


def _cache_payload_from_state(state: GenerateGraphState) -> dict[str, object]:
    return {
        "answer": state.get("answer"),
        "citations": list(state.get("citations") or []),
        "contexts": list(state.get("contexts") or []),
        "confidence": float(state.get("confidence") or 0.0),
        "model": state.get("model"),
        "latency_ms": state.get("latency_ms"),
        "usage": state.get("usage"),
    }


def build_generate_graph(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
    *,
    reranker: Reranker | None = None,
    rerank_config: RerankConfig | None = None,
    candidate_k: int | None = None,
    cache_config: CacheConfig | None = None,
    cache_store: SemanticCacheStore | None = None,
    embed_query: EmbedQueryFn | None = None,
    pipeline_version: str | None = None,
):
    """Compile semantic_cache→classify→retrieve→…→cache_write|refuse."""
    active_reranker: Reranker = reranker or IdentityReranker()
    rerank_enabled = bool(rerank_config is not None and rerank_config.enabled)
    pool_k = int(candidate_k) if candidate_k is not None and rerank_enabled else None
    cache_on = _cache_active(cache_config, cache_store)

    async def semantic_cache_lookup(state: GenerateGraphState) -> dict[str, object]:
        if not cache_on:
            return {
                "cache_hit": False,
                "path": ["semantic_cache_lookup"],
                "trace": [{"node": "semantic_cache_lookup", "reason": "disabled"}],
            }
        assert cache_config is not None
        assert cache_store is not None
        assert embed_query is not None
        assert pipeline_version is not None
        lookup_query = state.get("original_query") or state["query"]
        embedding = await asyncio.to_thread(embed_query, lookup_query)
        hit = await asyncio.to_thread(
            cache_store.lookup,
            pipeline_version,
            embedding,
        )
        if hit is None:
            return {
                "cache_hit": False,
                "path": ["semantic_cache_lookup"],
                "trace": [
                    {
                        "node": "semantic_cache_lookup",
                        "reason": "miss",
                    }
                ],
            }
        cached = _response_from_cache(hit.response)
        matched = hit.matched_query
        if len(matched) > 120:
            matched = matched[:117] + "..."
        update: dict[str, object] = {
            **cached,
            "cache_hit": True,
            "cache_similarity": hit.similarity,
            "cache_matched_query": matched,
            "path": ["semantic_cache_lookup"],
            "trace": [
                {
                    "node": "semantic_cache_lookup",
                    "reason": f"hit sim={hit.similarity:.4f}",
                }
            ],
        }
        return update

    def route_after_cache_lookup(state: GenerateGraphState) -> RouteAfterCacheLookup:
        if state.get("cache_hit"):
            return "hit"
        return "miss"

    async def semantic_cache_write(state: GenerateGraphState) -> dict[str, object]:
        if not cache_on:
            return {
                "path": ["semantic_cache_write"],
                "trace": [{"node": "semantic_cache_write", "reason": "disabled"}],
            }
        if state.get("cache_hit"):
            return {
                "path": ["semantic_cache_write"],
                "trace": [{"node": "semantic_cache_write", "reason": "skip_hit"}],
            }
        if not state.get("self_check_ok"):
            return {
                "path": ["semantic_cache_write"],
                "trace": [{"node": "semantic_cache_write", "reason": "skip_failed_check"}],
            }
        if state.get("refused"):
            return {
                "path": ["semantic_cache_write"],
                "trace": [{"node": "semantic_cache_write", "reason": "skip_refused"}],
            }
        assert cache_store is not None
        assert embed_query is not None
        assert pipeline_version is not None
        lookup_query = state.get("original_query") or state["query"]
        embedding = await asyncio.to_thread(embed_query, lookup_query)
        await asyncio.to_thread(
            cache_store.store,
            pipeline_version,
            lookup_query,
            embedding,
            _cache_payload_from_state(state),
        )
        return {
            "path": ["semantic_cache_write"],
            "trace": [{"node": "semantic_cache_write", "reason": "stored"}],
        }

    async def classify(state: GenerateGraphState) -> dict[str, object]:
        label, reason = classify_query(state["query"])
        update: dict[str, object] = {
            "classify_label": label,
            "original_query": state.get("original_query") or state["query"],
            "retry_count": int(state.get("retry_count") or 0),
            "path": ["classify"],
            "trace": [{"node": "classify", "reason": reason}],
        }
        if label == "refuse":
            update["refuse_reason"] = reason
        return update

    def route_after_classify(state: GenerateGraphState) -> RouteAfterClassify:
        if state.get("classify_label") == "refuse":
            return "refuse"
        return "retrieve"

    async def retrieve(state: GenerateGraphState) -> dict[str, object]:
        fetch_k = int(state["top_k"])
        if pool_k is not None:
            fetch_k = max(pool_k, fetch_k)
        chunks = await search(
            state["query"],
            method=state["method"],
            top_k=fetch_k,
        )
        return {
            "chunks": chunks,
            "path": ["retrieve"],
            "trace": [
                {
                    "node": "retrieve",
                    "reason": f"chunks={len(chunks)} pool_k={fetch_k}",
                }
            ],
        }

    async def rerank(state: GenerateGraphState) -> dict[str, object]:
        chunks = list(state.get("chunks") or [])
        top_k = int(state["top_k"])
        if rerank_enabled:
            active_reranker.ensure_loaded()
            ranked = await asyncio.to_thread(
                active_reranker.rerank,
                state["query"],
                chunks,
                top_k=top_k,
            )
            reason = f"CE enabled top_k={top_k} in={len(chunks)} out={len(ranked)}"
        else:
            ranked = await asyncio.to_thread(
                active_reranker.rerank,
                state["query"],
                chunks,
                top_k=top_k,
            )
            reason = f"passthrough top_k={top_k}"
        return {
            "chunks": ranked,
            "path": ["rerank"],
            "trace": [{"node": "rerank", "reason": reason}],
        }

    async def gate(state: GenerateGraphState) -> dict[str, object]:
        chunks = state.get("chunks") or []
        reason = should_refuse(
            chunks,
            min_retrieval_score=config.min_retrieval_score,
        )
        if reason is not None:
            return {
                "refuse_reason": reason,
                "packed": [],
                "path": ["gate"],
                "trace": [
                    {
                        "node": "gate",
                        "reason": (
                            f"refused=true budget={config.max_context_tokens} "
                            f"detail={reason}"
                        ),
                    }
                ],
            }
        packed = pack_chunks(chunks, max_context_tokens=config.max_context_tokens)
        if not packed:
            reason = "no retrieved context"
            return {
                "refuse_reason": reason,
                "packed": [],
                "path": ["gate"],
                "trace": [
                    {
                        "node": "gate",
                        "reason": (
                            f"refused=true budget={config.max_context_tokens} "
                            f"detail={reason}"
                        ),
                    }
                ],
            }
        est_tokens = sum(estimate_tokens(item.text) for item in packed)
        return {
            "refuse_reason": None,
            "packed": packed,
            "path": ["gate"],
            "trace": [
                {
                    "node": "gate",
                    "reason": (
                        f"packed={len(packed)} budget={config.max_context_tokens} "
                        f"est_tokens={est_tokens} refused=false"
                    ),
                }
            ],
        }

    def route_after_gate(state: GenerateGraphState) -> RouteAfterGate:
        if state.get("refuse_reason"):
            return "refuse"
        return "generate"

    async def generate(state: GenerateGraphState) -> dict[str, object]:
        packed = state["packed"]
        result = await provider.generate(build_messages(state["query"], packed))
        try:
            answer, citations, confidence = parse_generation_json(
                result.content,
                packed,
            )
        except LLMResponseError as exc:
            raise LLMUnavailableError(
                str(exc),
                raw_generation=result.content,
            ) from exc
        usage: dict[str, int] | None = None
        if result.usage is not None:
            usage = {
                "prompt_tokens": result.usage.prompt_tokens,
                "generated_tokens": result.usage.generated_tokens,
            }
        return {
            "answer": answer,
            "citations": citations,
            "contexts": [
                {
                    "chunk_id": item.chunk_id,
                    "note_path": item.note_path,
                    "text": item.text,
                }
                for item in packed
            ],
            "confidence": confidence,
            "refused": False,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "usage": usage,
            "path": ["generate"],
            "trace": [
                {
                    "node": "generate",
                    "reason": f"confidence={confidence:.3f}",
                }
            ],
        }

    async def self_check(state: GenerateGraphState) -> dict[str, object]:
        ok, reason = self_check_generation(
            answer=state.get("answer"),
            confidence=float(state.get("confidence") or 0.0),
            citations=state.get("citations"),
            refused=bool(state.get("refused")),
        )
        return {
            "self_check_ok": ok,
            "self_check_reason": reason,
            "path": ["self_check"],
            "trace": [{"node": "self_check", "reason": reason}],
        }

    def route_after_self_check(state: GenerateGraphState) -> RouteAfterSelfCheck:
        if state.get("self_check_ok"):
            return "pass"
        retries = int(state.get("retry_count") or 0)
        if retries >= MAX_SELF_CHECK_RETRIES:
            return "pass"
        return "rewrite"

    async def rewrite(state: GenerateGraphState) -> dict[str, object]:
        attempt = int(state.get("retry_count") or 0)
        new_query = rewrite_query(state["query"], attempt=attempt)
        return {
            "query": new_query,
            "retry_count": attempt + 1,
            "answer": None,
            "citations": [],
            "contexts": [],
            "confidence": 0.0,
            "self_check_ok": None,
            "self_check_reason": None,
            "path": ["rewrite"],
            "trace": [
                {
                    "node": "rewrite",
                    "reason": f"retry={attempt + 1}/{MAX_SELF_CHECK_RETRIES}",
                }
            ],
        }

    async def refuse(state: GenerateGraphState) -> dict[str, object]:
        reason = state.get("refuse_reason") or "refused"
        return {
            "answer": None,
            "citations": [],
            "contexts": [],
            "confidence": 0.0,
            "refused": True,
            "model": None,
            "latency_ms": None,
            "usage": None,
            "path": ["refuse"],
            "trace": [{"node": "refuse", "reason": str(reason)}],
        }

    graph = StateGraph(GenerateGraphState)
    graph.add_node("semantic_cache_lookup", semantic_cache_lookup)
    graph.add_node("semantic_cache_write", semantic_cache_write)
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank", rerank)
    graph.add_node("gate", gate)
    graph.add_node("generate", generate)
    graph.add_node("self_check", self_check)
    graph.add_node("rewrite", rewrite)
    graph.add_node("refuse", refuse)
    graph.add_edge(START, "semantic_cache_lookup")
    graph.add_conditional_edges(
        "semantic_cache_lookup",
        route_after_cache_lookup,
        {"hit": END, "miss": "classify"},
    )
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"retrieve": "retrieve", "refuse": "refuse"},
    )
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "gate")
    graph.add_conditional_edges(
        "gate",
        route_after_gate,
        {"generate": "generate", "refuse": "refuse"},
    )
    graph.add_edge("generate", "self_check")
    graph.add_conditional_edges(
        "self_check",
        route_after_self_check,
        {"pass": "semantic_cache_write", "rewrite": "rewrite"},
    )
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("refuse", END)
    return graph.compile()


async def run_generate_graph(
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
    """Invoke the compiled graph and return a JSON-ready generate payload."""
    app = build_generate_graph(
        search,
        provider,
        config,
        reranker=reranker,
        rerank_config=rerank_config,
        candidate_k=candidate_k,
        cache_config=cache_config,
        cache_store=cache_store,
        embed_query=embed_query,
        pipeline_version=pipeline_version,
    )
    final: GenerateGraphState = await app.ainvoke(
        {
            "query": query,
            "original_query": query,
            "method": method,
            "top_k": top_k,
            "path": [],
            "trace": [],
            "retry_count": 0,
            "cache_hit": False,
        }
    )
    refused = bool(final.get("refused"))
    return {
        "query": final.get("original_query") or query,
        "method": method,
        "top_k": top_k,
        "answer": final.get("answer"),
        "citations": final.get("citations") or [],
        "contexts": final.get("contexts") or [],
        "confidence": float(final.get("confidence") or 0.0),
        "refused": refused,
        "refusal_reason": final.get("refuse_reason") if refused else None,
        "model": final.get("model"),
        "latency_ms": final.get("latency_ms"),
        "usage": final.get("usage"),
        "graph_path": list(final.get("path") or []),
        "graph_trace": list(final.get("trace") or []),
        "retry_count": int(final.get("retry_count") or 0),
        "rewritten_query": (
            final.get("query")
            if (final.get("original_query") or query) != final.get("query")
            else None
        ),
        "cache_hit": bool(final.get("cache_hit")),
        "cache_similarity": final.get("cache_similarity"),
        "cache_matched_query": final.get("cache_matched_query"),
    }
