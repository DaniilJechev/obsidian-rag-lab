"""HTTP contract tests for the retriever API. No live e5 or vault."""

from dataclasses import dataclass, field

from fastapi.testclient import TestClient

from rag_based_on_obsidian.api.app import create_app
from rag_based_on_obsidian.api.ingest import IngestBusyError, IngestUnavailableError
from rag_based_on_obsidian.api.runtime import RetrieverUnavailableError
from rag_based_on_obsidian.api.schemas import IngestAccepted, IngestStatus
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


@dataclass
class FakeRuntime:
    """Stand-in for RetrieverRuntime: no model download, no Qdrant."""

    model_loaded: bool = True
    default_top_k: int = 5
    qdrant_ok: bool = True
    postgres_ok: bool = True
    retrieval_embedding_model: str | None = "intfloat/multilingual-e5-small"
    generate_model: str | None = "openai/gpt-4o-mini"
    judge_model: str | None = "openai/gpt-4o-mini"
    evaluation_embedding_model: str | None = "intfloat/multilingual-e5-small"
    search_calls: int = 0
    fail_search: bool = False
    ingest_busy: bool = False
    hold_ingest: bool = False
    fail_ingest: bool = False
    next_run_id: int = 1
    ingest_runs: dict[int, IngestStatus] = field(default_factory=dict)
    query_logs: list[dict[str, object]] = field(default_factory=list)
    generate_calls: list[dict[str, object]] = field(default_factory=list)
    empty_hits: bool = False
    fail_llm: bool = False
    missing_llm_key: bool = False
    fail_parse_json: bool = False

    def ping_qdrant(self) -> bool:
        return self.qdrant_ok

    def ping_postgres(self) -> bool:
        return self.postgres_ok

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
        if self.empty_hits:
            return []
        return [
            RetrievedChunk(
                chunk_id=1,
                text=f"hit for {query}",
                score=0.9,
                retrieval_method=method,
                metadata={"note_id": 42, "source_path": "DLS2/RoPE.md"},
                chunking_version="sprint9-policy-512-v2",
                rank=1,
                point_key="1:sprint9-policy-512-v2",
            )
        ][:top_k]

    async def generate(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
        model: str | None = None,
        enable_cache: bool | None = None,
        max_context_tokens: int | None = None,
    ) -> dict[str, object]:
        _ = model
        self.generate_calls.append(
            {
                "query": query,
                "method": method,
                "top_k": top_k,
                "model": model,
                "enable_cache": enable_cache,
                "max_context_tokens": max_context_tokens,
            }
        )
        if self.missing_llm_key:
            raise LLMUnavailableError("OPENROUTER_API_KEY is not configured")
        if self.fail_llm:
            raise LLMUnavailableError("openrouter is unreachable")
        if self.fail_parse_json:
            raise LLMUnavailableError(
                "structured output is not valid JSON",
                raw_generation='{"answer":"x \\approx 0","citations":[',
            )
        chunks = await self.search(query, method=method, top_k=top_k)
        if not chunks:
            return {
                "query": query,
                "method": method,
                "top_k": top_k,
                "answer": None,
                "citations": [],
                "confidence": 0.0,
                "refused": True,
                "refusal_reason": "no retrieved context",
                "model": None,
                "latency_ms": None,
                "usage": None,
                "contexts": [],
            }
        return {
            "query": query,
            "method": method,
            "top_k": top_k,
            "answer": f"answer for {query}",
            "citations": [{"chunk_id": 1, "note_path": "DLS2/RoPE.md"}],
            "contexts": [
                {
                    "chunk_id": 1,
                    "note_path": "DLS2/RoPE.md",
                    "text": f"hit for {query}",
                }
            ],
            "confidence": 0.8,
            "refused": False,
            "refusal_reason": None,
            "model": model or "openai/gpt-4o-mini",
            "latency_ms": 12,
            "usage": {"prompt_tokens": 10, "generated_tokens": 4},
        }

    def start_ingest(self) -> IngestAccepted:
        if self.fail_ingest:
            raise IngestUnavailableError("vault is not mounted")
        if self.ingest_busy:
            raise IngestBusyError
        run_id = self.next_run_id
        self.next_run_id += 1
        self.ingest_busy = True
        self.ingest_runs[run_id] = IngestStatus(
            run_id=run_id,
            status="running",
            corpus_scope="DLS1,DLS2",
        )
        if not self.hold_ingest:
            self.ingest_busy = False
            self.ingest_runs[run_id] = IngestStatus(
                run_id=run_id,
                status="completed",
                corpus_scope="DLS1,DLS2",
                documents_total=1,
                documents_succeeded=1,
                documents_failed=0,
                documents_skipped=0,
            )
        return IngestAccepted(run_id=run_id, status="running")

    def get_ingest(self, run_id: int) -> IngestStatus | None:
        return self.ingest_runs.get(run_id)

    def get_current_ingest(self) -> IngestStatus | None:
        if not self.ingest_runs:
            return None
        return self.ingest_runs[max(self.ingest_runs)]

    def record_query_log(
        self,
        *,
        query: str,
        method: RetrievalMethod,
        top_k: int,
        latency_ms: int,
        result_count: int,
        error: str | None,
    ) -> None:
        self.query_logs.append(
            {
                "query": query,
                "method": method,
                "top_k": top_k,
                "latency_ms": latency_ms,
                "result_count": result_count,
                "error": error,
            }
        )

    def close(self) -> None:
        return None


def _client(runtime: FakeRuntime) -> TestClient:
    return TestClient(create_app(runtime=runtime))


def test_health_ok_when_model_and_backends_ready() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "model_loaded": True,
        "qdrant": "ok",
        "postgres": "ok",
        "models": {
            "retrieval_embedding": "intfloat/multilingual-e5-small",
            "generate": "openai/gpt-4o-mini",
            "judge": "openai/gpt-4o-mini",
            "evaluation_embedding": "intfloat/multilingual-e5-small",
        },
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
    assert body["postgres"] == "ok"


def test_health_503_when_postgres_unreachable() -> None:
    runtime = FakeRuntime(postgres_ok=False)
    with _client(runtime) as client:
        response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["model_loaded"] is True
    assert body["qdrant"] == "ok"
    assert body["postgres"] == "unreachable"


def test_search_empty_query_returns_422() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "   "})
    assert response.status_code == 422
    assert runtime.query_logs == []


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
    assert len(runtime.query_logs) == 1
    log = runtime.query_logs[0]
    assert log["query"] == "attention"
    assert log["method"] == RetrievalMethod.HYBRID
    assert log["result_count"] == 1
    assert log["error"] is None


def test_search_503_when_qdrant_down() -> None:
    runtime = FakeRuntime(qdrant_ok=False)
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "attention"})
    assert response.status_code == 503
    assert response.json()["detail"] == "qdrant is unreachable"
    assert len(runtime.query_logs) == 1
    assert runtime.query_logs[0]["error"] == "qdrant is unreachable"


def test_search_503_when_backend_fails() -> None:
    runtime = FakeRuntime(fail_search=True)
    with _client(runtime) as client:
        response = client.post("/search", json={"query": "attention"})
    assert response.status_code == 503
    assert "failed" in response.json()["detail"]
    assert runtime.query_logs[0]["error"] == "retrieval backend failed"


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
    assert len(runtime.query_logs) == 2


def test_ingest_returns_202_and_run_id() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post("/ingest")
    assert response.status_code == 202
    body = response.json()
    assert body["run_id"] == 1
    assert body["status"] == "running"


def test_second_ingest_returns_409_while_first_is_in_flight() -> None:
    runtime = FakeRuntime(hold_ingest=True)
    with _client(runtime) as client:
        first = client.post("/ingest")
        second = client.post("/ingest")
        status = client.get("/ingest/1")
    assert first.status_code == 202
    assert second.status_code == 409
    assert status.status_code == 200
    assert status.json()["status"] == "running"


def test_ingest_current_returns_newest_run() -> None:
    runtime = FakeRuntime(hold_ingest=True)
    with _client(runtime) as client:
        started = client.post("/ingest")
        current = client.get("/ingest/current")
    assert started.status_code == 202
    assert current.status_code == 200
    body = current.json()
    assert body["run_id"] == started.json()["run_id"]
    assert body["status"] == "running"


def test_ingest_current_empty_returns_404() -> None:
    with _client(FakeRuntime()) as client:
        response = client.get("/ingest/current")
    assert response.status_code == 404
    assert response.json()["detail"] == "no ingest runs yet"


def test_ingest_status_unknown_run_returns_404() -> None:
    with _client(FakeRuntime()) as client:
        response = client.get("/ingest/999")
    assert response.status_code == 404


def test_ingest_unavailable_returns_503() -> None:
    runtime = FakeRuntime(fail_ingest=True)
    with _client(runtime) as client:
        response = client.post("/ingest")
    assert response.status_code == 503
    assert "vault" in response.json()["detail"]


def test_generate_returns_structured_answer() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "What is RoPE?"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["answer"] == "answer for What is RoPE?"
    assert body["citations"][0]["chunk_id"] == 1
    assert body["citations"][0]["note_path"] == "DLS2/RoPE.md"
    assert body["contexts"][0]["chunk_id"] == 1
    assert body["contexts"][0]["note_path"] == "DLS2/RoPE.md"
    assert body["method"] == "hybrid"
    assert body["model"] == "openai/gpt-4o-mini"
    assert runtime.search_calls == 1
    assert runtime.query_logs == []


def test_generate_accepts_model_override() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post(
            "/generate",
            json={
                "query": "What is RoPE?",
                "model": "google/gemini-3.7-flash",
            },
        )
    assert response.status_code == 200
    assert response.json()["model"] == "google/gemini-3.7-flash"


def test_generate_accepts_enable_cache_override() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post(
            "/generate",
            json={"query": "What is RoPE?", "enable_cache": True},
        )
    assert response.status_code == 200
    assert runtime.generate_calls[-1]["enable_cache"] is True


def test_generate_accepts_max_context_tokens_override() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post(
            "/generate",
            json={"query": "What is RoPE?", "max_context_tokens": 800},
        )
    assert response.status_code == 200
    assert runtime.generate_calls[-1]["max_context_tokens"] == 800


def test_generate_rejects_non_positive_max_context_tokens() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post(
            "/generate",
            json={"query": "What is RoPE?", "max_context_tokens": 0},
        )
    assert response.status_code == 422


def test_generate_rejects_blank_model() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post(
            "/generate",
            json={"query": "What is RoPE?", "model": "  "},
        )
    assert response.status_code == 422


def test_generate_empty_query_returns_422() -> None:
    runtime = FakeRuntime()
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "  "})
    assert response.status_code == 422
    assert runtime.search_calls == 0


def test_generate_refuses_without_context() -> None:
    runtime = FakeRuntime(empty_hits=True)
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "unknown topic"})
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert body["answer"] is None
    assert body["refusal_reason"] == "no retrieved context"


def test_generate_503_when_key_missing() -> None:
    runtime = FakeRuntime(missing_llm_key=True)
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "attention"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_generate_503_when_openrouter_down() -> None:
    runtime = FakeRuntime(fail_llm=True)
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "attention"})
    assert response.status_code == 503
    assert "openrouter" in response.json()["detail"]


def test_generate_503_includes_raw_generation_on_parse_failure() -> None:
    runtime = FakeRuntime(fail_parse_json=True)
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "attention"})
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["message"] == "structured output is not valid JSON"
    assert "\\approx" in detail["raw_generation"]


def test_generate_503_when_qdrant_down() -> None:
    runtime = FakeRuntime(qdrant_ok=False)
    with _client(runtime) as client:
        response = client.post("/generate", json={"query": "attention"})
    assert response.status_code == 503
    assert response.json()["detail"] == "qdrant is unreachable"
    assert runtime.search_calls == 0
