from dataclasses import dataclass
from pathlib import Path

from rag_based_on_obsidian.eval.retrieval import live_session
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.settings import RetrievalConfig


class _FakeClient:
    def close(self) -> None:
        return None


def test_open_live_session_bm25_does_not_load_embedder(monkeypatch, tmp_path: Path) -> None:
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
        url: str = "http://127.0.0.1:6333"
        collection: str = "notes"
        bm25_avg_len: float = 191.0
        bm25_model: str = "Qdrant/bm25"

    class FakeSparse:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def search(self, query: str, *, top_k: int, filters: object) -> list[object]:
            return []

    monkeypatch.setattr(live_session, "load_embedding_model_config", lambda _p: FakeModel())
    monkeypatch.setattr(live_session, "load_batch_embedding_config", lambda _p: FakeBatch())
    monkeypatch.setattr(live_session, "load_qdrant_config", lambda _p: FakeQdrant())
    monkeypatch.setattr(live_session, "QdrantClient", lambda url: _FakeClient())
    monkeypatch.setattr(live_session, "QdrantSparseRetriever", FakeSparse)

    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("BM25 eval must not load the embedding model")

    monkeypatch.setattr(live_session, "TransformersEmbeddingProvider", boom)
    monkeypatch.setattr(
        live_session,
        "versioned_collection_name",
        lambda *_args, **_kwargs: "collection",
    )

    session = live_session.open_live_session(
        method=RetrievalMethod.BM25,
        retrieval_config=RetrievalConfig(
            name="test",
            chunking_version="sprint9-policy-512-v2",
        ),
        model_config_path=tmp_path / "model.yaml",
        batch_config_path=tmp_path / "batch.yaml",
        qdrant_config_path=tmp_path / "qdrant.yaml",
        top_k=10,
        candidate_k=20,
        rrf_k=60,
    )
    try:
        assert session.info.method is RetrievalMethod.BM25
        assert session.info.device == "n/a"
        assert session.search("nDCG") == []
    finally:
        session.close()


def test_open_live_session_dense_loads_provider_once(monkeypatch, tmp_path: Path) -> None:
    constructed: list[str] = []

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
        url: str = "http://127.0.0.1:6333"
        collection: str = "notes"
        bm25_avg_len: float = 191.0
        bm25_model: str = "Qdrant/bm25"

    class FakeMetadata:
        model_name = "e5"
        model_revision = "rev"
        device = "cpu"
        dimension = 384
        normalized = True

    class FakeProvider:
        metadata = FakeMetadata()

        def __init__(self, _config: object) -> None:
            constructed.append("provider")

        def embed_query(self, text: str) -> tuple[float, ...]:
            return (1.0, 0.0)

    class FakeDense:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def search(self, query: str, *, top_k: int, filters: object) -> list[object]:
            return []

    monkeypatch.setattr(live_session, "load_embedding_model_config", lambda _p: FakeModel())
    monkeypatch.setattr(live_session, "load_batch_embedding_config", lambda _p: FakeBatch())
    monkeypatch.setattr(live_session, "load_qdrant_config", lambda _p: FakeQdrant())
    monkeypatch.setattr(live_session, "QdrantClient", lambda url: _FakeClient())
    monkeypatch.setattr(live_session, "TransformersEmbeddingProvider", FakeProvider)
    monkeypatch.setattr(live_session, "QdrantDenseRetriever", FakeDense)
    monkeypatch.setattr(
        live_session,
        "versioned_collection_name",
        lambda *_args, **_kwargs: "collection",
    )

    session = live_session.open_live_session(
        method=RetrievalMethod.DENSE,
        retrieval_config=RetrievalConfig(
            name="test",
            chunking_version="sprint9-policy-512-v2",
        ),
        model_config_path=tmp_path / "model.yaml",
        batch_config_path=tmp_path / "batch.yaml",
        qdrant_config_path=tmp_path / "qdrant.yaml",
        top_k=10,
        candidate_k=20,
        rrf_k=60,
    )
    try:
        session.search("one")
        session.search("two")
        assert constructed == ["provider"]
    finally:
        session.close()
