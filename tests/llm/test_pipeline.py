"""RAG generate pipeline with a fake LLM. No network."""

import asyncio

import pytest

from rag_based_on_obsidian.llm.contracts import LLMMessage, LLMMetadata, LLMResult
from rag_based_on_obsidian.llm.pipeline import run_rag_generate
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
        assert messages[0].role == "system"
        assert "RoPE" in messages[1].content
        return LLMResult(
            content=(
                '{"answer":"RoPE rotates embeddings.",'
                '"citations":[{"chunk_id":1,"note_path":"x"}],'
                '"confidence":0.9}'
            ),
            model="openai/gpt-4o-mini",
            latency_ms=5,
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
    assert method is RetrievalMethod.HYBRID
    assert top_k == 5
    return [
        RetrievedChunk(
            chunk_id=1,
            text="RoPE applies a rotation to query and key vectors.",
            score=0.8,
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


def test_pipeline_returns_answer_and_rewrites_citation_path() -> None:
    payload = asyncio.run(
        run_rag_generate(
            _search_one,
            _FakeLLM(),
            _CONFIG,
            "What is RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is False
    assert payload["answer"] == "RoPE rotates embeddings."
    assert payload["citations"] == [{"chunk_id": 1, "note_path": "DLS2/RoPE.md"}]
    assert payload["contexts"] == [
        {
            "chunk_id": 1,
            "note_path": "DLS2/RoPE.md",
            "text": "RoPE applies a rotation to query and key vectors.",
        }
    ]
    assert payload["graph_path"] == [
        "classify",
        "retrieve",
        "gate",
        "generate",
        "self_check",
    ]


def test_pipeline_refuses_without_calling_llm() -> None:
    class _Boom:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            raise AssertionError("LLM must not be called on refuse")

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="x")

    payload = asyncio.run(
        run_rag_generate(
            _search_empty,
            _Boom(),
            _CONFIG,
            "nothing here",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is True
    assert payload["refusal_reason"] == "no retrieved context"
    assert payload["contexts"] == []
    assert payload["graph_path"] == [
        "classify",
        "retrieve",
        "gate",
        "refuse",
    ]


def test_pipeline_attaches_raw_generation_on_parse_failure() -> None:
    from rag_based_on_obsidian.llm.contracts import LLMUnavailableError

    class _BadJson:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            return LLMResult(
                content='{"answer":"x \\approx 0","citations":[',
                model="fake",
                latency_ms=1,
            )

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="fake")

    with pytest.raises(LLMUnavailableError) as caught:
        asyncio.run(
            run_rag_generate(
                _search_one,
                _BadJson(),
                _CONFIG,
                "What is RoPE?",
                method=RetrievalMethod.HYBRID,
                top_k=5,
            )
        )
    assert "valid JSON" in str(caught.value)
    assert caught.value.raw_generation is not None
    assert "\\approx" in caught.value.raw_generation
