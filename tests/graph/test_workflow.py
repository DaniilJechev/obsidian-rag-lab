"""LangGraph generate path: answer vs refuse without live OpenRouter."""

import asyncio

from rag_based_on_obsidian.lang_graph.workflow import run_generate_graph
from rag_based_on_obsidian.llm.contracts import LLMMessage, LLMMetadata, LLMResult
from rag_based_on_obsidian.llm.settings import LLMConfig
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk

_CONFIG = LLMConfig(
    name="test",
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    min_retrieval_score=0.0,
    max_context_tokens=200,
)


class _FakeLLM:
    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        return LLMResult(
            content=(
                '{"answer":"ok",'
                '"citations":[{"chunk_id":1,"note_path":"x"}],'
                '"confidence":0.8}'
            ),
            model="openai/gpt-4o-mini",
            latency_ms=3,
        )

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(provider="fake", model="openai/gpt-4o-mini")


async def _search_one(
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id=1,
            text="RoPE rotates query and key vectors by position.",
            score=0.9,
            retrieval_method=method,
            metadata={"source_path": "DLS2/RoPE.md"},
            chunking_version="sprint9-policy-512-v2",
            rank=1,
        )
    ]


async def _search_empty(
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> list[RetrievedChunk]:
    return []


def test_graph_answer_path_is_retrieve_gate_generate() -> None:
    payload = asyncio.run(
        run_generate_graph(
            _search_one,
            _FakeLLM(),
            _CONFIG,
            "What is RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is False
    assert payload["graph_path"] == ["retrieve", "gate", "generate"]


def test_graph_refuse_path_skips_llm() -> None:
    class _Boom:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            raise AssertionError("LLM must not run on refuse branch")

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="x")

    payload = asyncio.run(
        run_generate_graph(
            _search_empty,
            _Boom(),
            _CONFIG,
            "nothing",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is True
    assert payload["refusal_reason"] == "no retrieved context"
    assert payload["graph_path"] == ["retrieve", "gate", "refuse"]
