"""LangGraph: retrieve → gate → generate | refuse.

Keeps packing, parser, and OpenRouter in ``llm/``; this module only
orchestrates the same semantics as the former linear ``run_rag_generate``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

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

SearchFn = Callable[..., Awaitable[list[RetrievedChunk]]]
RouteAfterGate = Literal["generate", "refuse"]


def build_generate_graph(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
):
    """Compile a retrieve→gate→generate|refuse graph closed over deps."""

    async def retrieve(state: GenerateGraphState) -> dict[str, object]:
        chunks = await search(
            state["query"],
            method=state["method"],
            top_k=state["top_k"],
        )
        return {"chunks": chunks, "path": ["retrieve"]}

    async def gate(state: GenerateGraphState) -> dict[str, object]:
        chunks = state.get("chunks") or []
        reason = should_refuse(
            chunks,
            min_retrieval_score=config.min_retrieval_score,
        )
        if reason is not None:
            return {"refuse_reason": reason, "packed": [], "path": ["gate"]}
        packed = pack_chunks(chunks, max_context_tokens=config.max_context_tokens)
        if not packed:
            return {
                "refuse_reason": "no retrieved context",
                "packed": [],
                "path": ["gate"],
            }
        return {"refuse_reason": None, "packed": packed, "path": ["gate"]}

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
        }

    async def refuse(state: GenerateGraphState) -> dict[str, object]:
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
        }

    graph = StateGraph(GenerateGraphState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("gate", gate)
    graph.add_node("generate", generate)
    graph.add_node("refuse", refuse)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "gate")
    graph.add_conditional_edges(
        "gate",
        route_after_gate,
        {"generate": "generate", "refuse": "refuse"},
    )
    graph.add_edge("generate", END)
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
) -> dict[str, object]:
    """Invoke the compiled graph and return a JSON-ready generate payload."""
    app = build_generate_graph(search, provider, config)
    final: GenerateGraphState = await app.ainvoke(
        {
            "query": query,
            "method": method,
            "top_k": top_k,
            "path": [],
        }
    )
    return {
        "query": query,
        "method": method,
        "top_k": top_k,
        "answer": final.get("answer"),
        "citations": final.get("citations") or [],
        "contexts": final.get("contexts") or [],
        "confidence": float(final.get("confidence") or 0.0),
        "refused": bool(final.get("refused")),
        "refusal_reason": final.get("refuse_reason") if final.get("refused") else None,
        "model": final.get("model"),
        "latency_ms": final.get("latency_ms"),
        "usage": final.get("usage"),
        "graph_path": list(final.get("path") or []),
    }
