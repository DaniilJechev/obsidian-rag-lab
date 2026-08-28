"""LangGraph semantic cache hit/miss integration tests."""

import asyncio

from rag_based_on_obsidian.cache.semantic_store import InMemorySemanticCacheStore
from rag_based_on_obsidian.cache.settings import CacheConfig
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
_CACHE_CONFIG = CacheConfig(name="test-cache", enabled=True, similarity_threshold=0.92)
_PIPELINE = "semantic-v1|model|hybrid|chunk|embed|rerank-off|generate-v1"


class _BoomLLM:
    async def generate(self, messages: list[LLMMessage]) -> LLMResult:
        raise AssertionError("LLM must not run on cache hit")

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(provider="fake", model="x")


async def _search_boom(
    query: str,
    *,
    method: RetrievalMethod,
    top_k: int,
) -> list[RetrievedChunk]:
    raise AssertionError("retrieval must not run on cache hit")


def _embed(text: str) -> tuple[float, ...]:
    if "dropout" in text.lower():
        return (1.0, 0.0, 0.0)
    if "overfitting" in text.lower():
        return (0.99, 0.01, 0.0)
    return (0.0, 1.0, 0.0)


def test_graph_semantic_cache_hit_skips_pipeline() -> None:
    store = InMemorySemanticCacheStore(_CACHE_CONFIG)
    store.store(
        _PIPELINE,
        "Зачем нужен dropout?",
        (1.0, 0.0, 0.0),
        {
            "answer": "from cache",
            "citations": [],
            "contexts": [],
            "confidence": 0.88,
            "model": "cached",
            "latency_ms": 1,
            "usage": None,
        },
    )
    payload = asyncio.run(
        run_generate_graph(
            _search_boom,
            _BoomLLM(),
            _CONFIG,
            "Как dropout борется с overfitting?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
            cache_config=_CACHE_CONFIG,
            cache_store=store,
            embed_query=_embed,
            pipeline_version=_PIPELINE,
        )
    )
    assert payload["cache_hit"] is True
    assert payload["answer"] == "from cache"
    assert payload["graph_path"] == ["semantic_cache_lookup"]
    assert "generate" not in payload["graph_path"]


def test_graph_semantic_cache_miss_runs_full_pipeline() -> None:
    class _FakeLLM:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            return LLMResult(
                content=(
                    '{"answer":"fresh",'
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
        _ = query, top_k
        return [
            RetrievedChunk(
                chunk_id=1,
                text="chunk",
                score=0.9,
                retrieval_method=method,
                metadata={"source_path": "x.md"},
                chunking_version="t",
                rank=1,
            )
        ]

    store = InMemorySemanticCacheStore(_CACHE_CONFIG)
    payload = asyncio.run(
        run_generate_graph(
            _search_one,
            _FakeLLM(),
            _CONFIG,
            "Что такое RoPE?",
            method=RetrievalMethod.HYBRID,
            top_k=5,
            cache_config=_CACHE_CONFIG,
            cache_store=store,
            embed_query=_embed,
            pipeline_version=_PIPELINE,
        )
    )
    assert payload["cache_hit"] is False
    assert payload["answer"] == "fresh"
    assert payload["graph_path"][0] == "semantic_cache_lookup"
    assert "generate" in payload["graph_path"]
    assert payload["graph_path"][-1] == "semantic_cache_write"
    hit = store.lookup(_PIPELINE, _embed("Что такое RoPE?"))
    assert hit is not None
