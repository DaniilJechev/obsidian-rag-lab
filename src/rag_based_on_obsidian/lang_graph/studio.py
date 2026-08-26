"""Local LangGraph Studio entrypoint (``langgraph dev``).

Does **not** replace FastAPI ``POST /generate``. The API keeps using
in-process ``run_generate_graph``. This module only exposes a compiled
graph for the Studio Agent Server.

Modes (env ``LANGGRAPH_STUDIO_MODE``):

- ``stub`` (default) — fake search + fake LLM; no Qdrant/OpenRouter/torch.
  Use to inspect nodes, edges, and state in Studio.
- ``live`` — same ``RetrieverRuntime`` + OpenRouter as the API (slow start;
  needs Postgres/Qdrant/.env keys).
"""

from __future__ import annotations

import os
from pathlib import Path

from rag_based_on_obsidian.lang_graph.workflow import build_generate_graph
from rag_based_on_obsidian.llm.contracts import (
    LLMMessage,
    LLMMetadata,
    LLMProvider,
    LLMResult,
)
from rag_based_on_obsidian.llm.settings import LLMConfig, load_llm_config
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk

_DEFAULT_LLM_CONFIG = Path("configs/llm/openrouter.yaml")


class _StubLLM:
    """Deterministic JSON answer for Studio without network."""

    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        _ = messages
        return LLMResult(
            content=(
                '{"answer":"Studio stub: RoPE rotates query/key by position. '
                'See [[RoPE]].",'
                '"citations":[{"chunk_id":1,"note_path":"DLS2/RoPE.md"}],'
                '"confidence":0.85}'
            ),
            model="studio-stub",
            latency_ms=1,
        )

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(provider="studio-stub", model="studio-stub")


async def _stub_search(
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> list[RetrievedChunk]:
    """Return one chunk, or none if the query asks to refuse."""
    _ = top_k
    lowered = query.strip().lower()
    if lowered in {"", "refuse", "empty"} or "refuse" in lowered:
        return []
    return [
        RetrievedChunk(
            chunk_id=1,
            text="RoPE applies a rotation to query and key vectors by position.",
            score=0.9,
            retrieval_method=method,
            metadata={"source_path": "DLS2/RoPE.md"},
            chunking_version="studio-stub",
            rank=1,
        )
    ]


def _stub_config() -> LLMConfig:
    path = Path(os.environ.get("LLM_CONFIG_PATH", str(_DEFAULT_LLM_CONFIG)))
    if path.is_file():
        return load_llm_config(path)
    return LLMConfig(
        name="studio-stub",
        model="studio-stub",
        base_url="http://127.0.0.1",
        min_retrieval_score=0.0,
        max_context_tokens=512,
    )


def _live_graph():
    """Wire real retrieval + OpenRouter (same stack as API)."""
    from rag_based_on_obsidian.api.runtime import build_runtime
    from rag_based_on_obsidian.llm.openrouter import OpenRouterLLMProvider

    runtime = build_runtime()
    llm_config = load_llm_config(
        Path(os.environ.get("LLM_CONFIG_PATH", str(_DEFAULT_LLM_CONFIG)))
    )
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    provider: LLMProvider = OpenRouterLLMProvider(llm_config, api_key=api_key)
    return build_generate_graph(runtime.search, provider, llm_config)


def graph():
    """Factory for ``langgraph.json`` / Studio. Prefer stub for local UI."""
    mode = os.environ.get("LANGGRAPH_STUDIO_MODE", "stub").strip().lower()
    if mode == "live":
        return _live_graph()
    return build_generate_graph(_stub_search, _StubLLM(), _stub_config())
