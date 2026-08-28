"""In-memory semantic cache store tests (no Redis)."""

from rag_based_on_obsidian.cache.semantic_store import InMemorySemanticCacheStore
from rag_based_on_obsidian.cache.settings import CacheConfig


def _config(**overrides: object) -> CacheConfig:
    base = {
        "name": "test-cache",
        "enabled": True,
        "similarity_threshold": 0.92,
        "max_entries": 2,
    }
    base.update(overrides)
    return CacheConfig(**base)


def test_store_and_lookup_hit() -> None:
    store = InMemorySemanticCacheStore(_config())
    pipeline = "semantic-v1|model|hybrid|chunk|embed|rerank-off|generate-v1"
    embedding = (1.0, 0.0, 0.0)
    store.store(
        pipeline,
        "canonical question",
        embedding,
        {"answer": "cached answer", "citations": [], "contexts": []},
    )
    hit = store.lookup(pipeline, (0.99, 0.01, 0.0))
    assert hit is not None
    assert hit.similarity >= 0.92
    assert hit.response["answer"] == "cached answer"


def test_lookup_miss_below_threshold() -> None:
    store = InMemorySemanticCacheStore(_config())
    pipeline = "pv1"
    store.store(pipeline, "q1", (1.0, 0.0), {"answer": "a"})
    miss = store.lookup(pipeline, (0.0, 1.0))
    assert miss is None


def test_eviction_when_max_entries_exceeded() -> None:
    store = InMemorySemanticCacheStore(_config(max_entries=2))
    pipeline = "pv1"
    store.store(pipeline, "q1", (1.0, 0.0, 0.0), {"answer": "1"})
    store.store(pipeline, "q2", (0.0, 1.0, 0.0), {"answer": "2"})
    store.store(pipeline, "q3", (0.0, 0.0, 1.0), {"answer": "3"})
    assert store.lookup(pipeline, (1.0, 0.0, 0.0)) is None
    assert store.lookup(pipeline, (0.0, 0.0, 1.0)) is not None


def test_pipeline_version_isolation() -> None:
    store = InMemorySemanticCacheStore(_config())
    store.store("pv-a", "q", (1.0, 0.0), {"answer": "a"})
    assert store.lookup("pv-b", (1.0, 0.0)) is None
