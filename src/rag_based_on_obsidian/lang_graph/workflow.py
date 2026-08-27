"""LangGraph: classify → retrieve → rerank → gate → generate → self_check | refuse.

Sprint 26 adds optional cross-encoder ``rerank`` (passthrough when disabled).
Packing, parser, and OpenRouter stay in ``llm/``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

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
    pack_chunks,
    should_refuse,
)
from rag_based_on_obsidian.llm.parser import parse_generation_json
from rag_based_on_obsidian.llm.settings import LLMConfig
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.rerank import IdentityReranker, Reranker
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig

SearchFn = Callable[..., Awaitable[list[RetrievedChunk]]]
RouteAfterClassify = Literal["retrieve", "refuse"]
RouteAfterGate = Literal["generate", "refuse"]
RouteAfterSelfCheck = Literal["pass", "rewrite"]


def build_generate_graph(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
    *,
    reranker: Reranker | None = None,
    rerank_config: RerankConfig | None = None,
    candidate_k: int | None = None,
):
    """Compile classify→retrieve→rerank→gate→generate→self_check|refuse."""
    active_reranker: Reranker = reranker or IdentityReranker()
    rerank_enabled = bool(rerank_config is not None and rerank_config.enabled)
    pool_k = int(candidate_k) if candidate_k is not None and rerank_enabled else None

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
                "trace": [{"node": "gate", "reason": reason}],
            }
        packed = pack_chunks(chunks, max_context_tokens=config.max_context_tokens)
        if not packed:
            reason = "no retrieved context"
            return {
                "refuse_reason": reason,
                "packed": [],
                "path": ["gate"],
                "trace": [{"node": "gate", "reason": reason}],
            }
        return {
            "refuse_reason": None,
            "packed": packed,
            "path": ["gate"],
            "trace": [{"node": "gate", "reason": f"packed={len(packed)}"}],
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
    graph.add_node("classify", classify)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank", rerank)
    graph.add_node("gate", gate)
    graph.add_node("generate", generate)
    graph.add_node("self_check", self_check)
    graph.add_node("rewrite", rewrite)
    graph.add_node("refuse", refuse)
    graph.add_edge(START, "classify")
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
        {"pass": END, "rewrite": "rewrite"},
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
) -> dict[str, object]:
    """Invoke the compiled graph and return a JSON-ready generate payload."""
    app = build_generate_graph(
        search,
        provider,
        config,
        reranker=reranker,
        rerank_config=rerank_config,
        candidate_k=candidate_k,
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
    }
