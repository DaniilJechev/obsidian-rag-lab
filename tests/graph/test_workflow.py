"""LangGraph generate path: classify, retry, refuse without live OpenRouter."""

import asyncio

from rag_based_on_obsidian.lang_graph.policies import MAX_SELF_CHECK_RETRIES
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


class _LowThenHighConfidenceLLM:
    """First generate fails self-check; second passes after rewrite."""

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        self.calls += 1
        if self.calls == 1:
            content = (
                '{"answer":"weak",'
                '"citations":[{"chunk_id":1,"note_path":"x"}],'
                '"confidence":0.1}'
            )
        else:
            content = (
                '{"answer":"strong after rewrite",'
                '"citations":[{"chunk_id":1,"note_path":"x"}],'
                '"confidence":0.9}'
            )
        return LLMResult(
            content=content,
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
    _ = query, top_k
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
    _ = query, method, top_k
    return []


def test_graph_answer_path_includes_classify_and_self_check() -> None:
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
    assert payload["graph_path"] == [
        "classify",
        "retrieve",
        "rerank",
        "gate",
        "generate",
        "self_check",
    ]
    assert payload["retry_count"] == 0
    assert payload["rewritten_query"] is None
    assert [step["node"] for step in payload["graph_trace"]] == payload["graph_path"]


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
            "nothing useful here",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is True
    assert payload["refusal_reason"] == "no retrieved context"
    assert payload["graph_path"] == [
        "classify",
        "retrieve",
        "rerank",
        "gate",
        "refuse",
    ]


def test_graph_classify_early_refuse() -> None:
    class _Boom:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            raise AssertionError("LLM must not run on classify refuse")

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="x")

    payload = asyncio.run(
        run_generate_graph(
            _search_one,
            _Boom(),
            _CONFIG,
            "??",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["refused"] is True
    assert payload["graph_path"] == ["classify", "refuse"]
    assert payload["graph_trace"][0]["node"] == "classify"


def test_graph_self_check_retry_then_pass() -> None:
    llm = _LowThenHighConfidenceLLM()
    payload = asyncio.run(
        run_generate_graph(
            _search_one,
            llm,
            _CONFIG,
            "What is RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert llm.calls == 2
    assert payload["refused"] is False
    assert payload["retry_count"] == 1
    assert payload["rewritten_query"] is not None
    assert "rewrite" in payload["graph_path"]
    assert payload["graph_path"].count("generate") == 2
    assert payload["graph_path"].count("self_check") == 2
    assert payload["answer"] == "strong after rewrite"


def test_graph_self_check_retry_cap() -> None:
    """After one rewrite, a second low-confidence answer is accepted (capped)."""

    class _AlwaysLow:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            return LLMResult(
                content=(
                    '{"answer":"still weak",'
                    '"citations":[{"chunk_id":1,"note_path":"x"}],'
                    '"confidence":0.1}'
                ),
                model="fake",
                latency_ms=1,
            )

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="fake")

    payload = asyncio.run(
        run_generate_graph(
            _search_one,
            _AlwaysLow(),
            _CONFIG,
            "What is RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
        )
    )
    assert payload["retry_count"] == MAX_SELF_CHECK_RETRIES
    assert payload["graph_path"].count("rewrite") == 1
    assert payload["graph_path"].count("generate") == 2
    assert payload["refused"] is False
    assert payload["confidence"] == 0.1


def test_graph_rerank_node_reorders_when_enabled() -> None:
    class _Reverse:
        def ensure_loaded(self) -> None:
            return None

        def rerank(self, query: str, chunks: list[RetrievedChunk], *, top_k: int):
            _ = query
            ordered = list(reversed(chunks))[:top_k]
            return [
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=chunk.score,
                    retrieval_method=chunk.retrieval_method,
                    metadata=dict(chunk.metadata),
                    chunking_version=chunk.chunking_version,
                    rank=index,
                    rerank_score=float(10 - index),
                )
                for index, chunk in enumerate(ordered, start=1)
            ]

    async def _search_two(
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
    ) -> list[RetrievedChunk]:
        _ = query
        return [
            RetrievedChunk(
                chunk_id=1,
                text="first",
                score=0.9,
                retrieval_method=method,
                metadata={"source_path": "a.md"},
                chunking_version="t",
                rank=1,
            ),
            RetrievedChunk(
                chunk_id=2,
                text="second",
                score=0.8,
                retrieval_method=method,
                metadata={"source_path": "b.md"},
                chunking_version="t",
                rank=2,
            ),
        ][:top_k]

    from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig

    payload = asyncio.run(
        run_generate_graph(
            _search_two,
            _FakeLLM(),
            _CONFIG,
            "What is RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=2,
            reranker=_Reverse(),
            rerank_config=RerankConfig(name="test", enabled=True),
            candidate_k=2,
        )
    )
    assert "rerank" in payload["graph_path"]
    assert payload["contexts"][0]["chunk_id"] == 2
