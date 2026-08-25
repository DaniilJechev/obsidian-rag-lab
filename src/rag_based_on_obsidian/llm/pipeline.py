"""Retrieve, pack, refuse, or call the LLM. No FastAPI types here."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

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


async def run_rag_generate(
    search: SearchFn,
    provider: LLMProvider,
    config: LLMConfig,
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> dict[str, object]:
    """Return a JSON-ready generate payload. May raise LLM errors."""
    chunks = await search(query, method=method, top_k=top_k)
    reason = should_refuse(chunks, min_retrieval_score=config.min_retrieval_score)
    if reason is not None:
        return _refused(
            query=query,
            method=method,
            top_k=top_k,
            reason=reason,
        )
    packed = pack_chunks(chunks, max_context_tokens=config.max_context_tokens)
    if not packed:
        return _refused(
            query=query,
            method=method,
            top_k=top_k,
            reason="no retrieved context",
        )
    result = await provider.generate(build_messages(query, packed))
    try:
        answer, citations, confidence = parse_generation_json(result.content, packed)
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
        "query": query,
        "method": method,
        "top_k": top_k,
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
        "refusal_reason": None,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "usage": usage,
    }


def _refused(
    *,
    query: str,
    method: RetrievalMethod,
    top_k: int,
    reason: str,
) -> dict[str, object]:
    return {
        "query": query,
        "method": method,
        "top_k": top_k,
        "answer": None,
        "citations": [],
        "contexts": [],
        "confidence": 0.0,
        "refused": True,
        "refusal_reason": reason,
        "model": None,
        "latency_ms": None,
        "usage": None,
    }
