"""HTTP contract tests for the retriever API. No live e5 or vault."""

from dataclasses import dataclass

from fastapi.testclient import TestClient

from rag_based_on_obsidian.api.app import create_app
from rag_based_on_obsidian.api.runtime import RetrieverUnavailableError
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


@dataclass
class FakeRuntime:
    """Stand-in for RetrieverRuntime: no model download, no Qdrant."""

    model_loaded: bool = True
    default_top_k: int = 5
    qdrant_ok: bool = True
    search_calls: int = 0
    fail_search: bool = False

    def ping_qdrant(self) -> bool:
        return self.qdrant_ok

    async def search(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
    ) -> list[RetrievedChunk]:
        self.search_calls += 1
        if self.fail_search:
            raise RetrieverUnavailableError("retrieval backend failed")
        return [
            RetrievedChunk(
                chunk_id=1,
                text=f"hit for {query}",
                score=0.9,
                retrieval_method=method,
                metadata={"note_id": 42},
                chunking_version="sprint9-policy-512-v2",
                rank=1,
                point_key="1:sprint9-policy-512-v2",
            )
        ][:top_k]

    def close(self) -> None:
        return None


def _client(runtime: FakeRuntime) -> TestClient:
    return TestClient(create_app(runtime=runtime))


def test_health_ok_when_model_and_qdrant_ready() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "model_loaded": True,
        "qdrant": "ok",
    }


def test_health_503_when_qdrant_unreachable() -> None:
    runtime = FakeRuntime(qdrant_ok=False)
    with _client(runtime) as client:
        response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["model_loaded"] is True
    assert body["qdrant"] == "unreachable"


def test_search_empty_query_returns_422() -> None:
    with _client(FakeRuntime()) as client:
        response = client.post("/search", json={"query": "   "})
    assert response.status_code == 422


def test_search_default_method_is_hybrid() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "attention"})
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "hybrid"
    assert body["top_k"] == 5
    assert body["query"] == "attention"
    assert body["results"][0]["chunk_id"] == 1
    assert body["results"][0]["text"] == "hit for attention"
    assert "ScoredPoint" not in response.text


def test_search_503_when_qdrant_down() -> None:
    runtime = FakeRuntime(qdrant_ok=False)
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "attention"})
    assert response.status_code == 503
    assert response.json()["detail"] == "qdrant is unreachable"


def test_search_503_when_backend_fails() -> None:
    runtime = FakeRuntime(fail_search=True)
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "attention"})
    assert response.status_code == 503
    assert "failed" in response.json()["detail"]


def test_repeated_search_does_not_construct_another_runtime() -> None:
    runtime = FakeRuntime()
    app = create_app(runtime=runtime)
    with TestClient(app) as client:
        first = client.post("/search", json={"query": "one", "method": "dense"})
        second = client.post("/search", json={"query": "two", "method": "dense"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert runtime.search_calls == 2
    assert first.json()["results"][0]["retrieval_method"] == "dense"
