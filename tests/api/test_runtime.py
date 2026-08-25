from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from rag_based_on_obsidian.api import runtime as runtime_module


class _FakeClient:
    def __init__(self, url: str, timeout: float | None = None) -> None:
        self.url = url
        self.timeout = timeout
        self.closed = False

    def get_collections(self) -> object:
        return object()

    def close(self) -> None:
        self.closed = True


class _FakeProvider:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.metadata = type(
            "Meta",
            (),
            {
                "model_name": "e5",
                "model_revision": "rev",
                "device": "cpu",
                "dimension": 384,
                "normalized": True,
            },
        )()


class _FakeDense:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeSparse:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeHybrid:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakePostgresEngine:
    def connect(self) -> _FakePostgresConnection:
        return _FakePostgresConnection()


class _FakePostgresConnection:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, _statement: object) -> None:
        return None


def test_build_runtime_uses_qdrant_url_env(monkeypatch) -> None:
    @dataclass(frozen=True)
    class FakeModel:
        model_name: str = "e5"
        model_revision: str = "rev"
        dimension: int = 384
        normalized: bool = True
        max_length: int = 512
        batch_size: int = 8
        device: str = "cpu"

    @dataclass(frozen=True)
    class FakeBatch:
        chunking_version: str = "sprint9-policy-512-v2"

    @dataclass(frozen=True)
    class FakeQdrant:
        url: str = "http://localhost:6333"
        collection: str = "notes"
        bm25_avg_len: float = 191.0
        bm25_model: str = "Qdrant/bm25"

    @dataclass(frozen=True)
    class FakeRetrieval:
        name: str = "test"
        chunking_version: str = "sprint9-policy-512-v2"
        top_k: int = 5
        candidate_k: int = 20
        rrf_k: int = 60
        filters: dict[str, object] = field(default_factory=dict)

    @dataclass(frozen=True)
    class FakeLlm:
        name: str = "test-llm"
        model: str = "openai/gpt-4o-mini"
        base_url: str = "https://openrouter.ai/api/v1"
        timeout_seconds: float = 30.0
        temperature: float = 0.0
        max_output_tokens: int = 256
        max_context_tokens: int = 1024
        min_retrieval_score: float = 0.0
        http_referer: str = "https://example.test"
        app_title: str = "test"

    captured: dict[str, object] = {}

    def fake_client(url: str, timeout: float | None = None) -> _FakeClient:
        captured["url"] = url
        captured["timeout"] = timeout
        return _FakeClient(url, timeout)

    monkeypatch.setenv("QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setattr(
        runtime_module, "load_embedding_model_config", lambda _p: FakeModel()
    )
    monkeypatch.setattr(
        runtime_module, "load_batch_embedding_config", lambda _p: FakeBatch()
    )
    monkeypatch.setattr(runtime_module, "load_qdrant_config", lambda _p: FakeQdrant())
    monkeypatch.setattr(
        runtime_module, "load_retrieval_config", lambda _p: FakeRetrieval()
    )
    monkeypatch.setattr(runtime_module, "load_llm_config", lambda _p: FakeLlm())
    monkeypatch.setattr(
        runtime_module, "_read_judge_model_pin", lambda: "openai/gpt-4o-mini"
    )
    monkeypatch.setattr(runtime_module, "QdrantClient", fake_client)
    monkeypatch.setattr(runtime_module, "TransformersEmbeddingProvider", _FakeProvider)
    monkeypatch.setattr(runtime_module, "QdrantDenseRetriever", _FakeDense)
    monkeypatch.setattr(runtime_module, "QdrantSparseRetriever", _FakeSparse)
    monkeypatch.setattr(runtime_module, "HybridRetriever", _FakeHybrid)
    monkeypatch.setattr(
        runtime_module,
        "versioned_collection_name",
        lambda *_args, **_kwargs: "collection",
    )

    built = runtime_module.build_runtime()
    try:
        assert captured["url"] == "http://qdrant:6333"
        assert built.model_loaded is True
        assert built.default_top_k == 5
        assert built.retrieval_embedding_model == "e5"
        assert built.generate_model == "openai/gpt-4o-mini"
        assert built.judge_model == "openai/gpt-4o-mini"
        assert built.evaluation_embedding_model == "e5"
        assert built.ping_qdrant() is True
        monkeypatch.setattr(
            built,
            "_ensure_engine",
            lambda: _FakePostgresEngine(),
        )
        assert built.ping_postgres() is True
        monkeypatch.setattr(
            built,
            "_ensure_engine",
            lambda: (_ for _ in ()).throw(RuntimeError("postgres down")),
        )
        assert built.ping_postgres() is False
    finally:
        built.close()
