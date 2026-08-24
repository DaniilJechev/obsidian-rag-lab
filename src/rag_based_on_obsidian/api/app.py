"""FastAPI application: lifespan loads e5 once; routes hide retrieval internals."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Protocol

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from rag_based_on_obsidian.api.ingest import IngestBusyError, IngestUnavailableError
from rag_based_on_obsidian.api.runtime import (
    RetrieverUnavailableError,
    build_runtime,
)
from rag_based_on_obsidian.api.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    IngestAccepted,
    IngestStatus,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


class AppRuntime(Protocol):
    """HTTP surface: search, ingest, generate, and query logs. Tests inject a fake."""

    model_loaded: bool
    default_top_k: int

    def ping_qdrant(self) -> bool:
        """Return whether Qdrant currently answers."""
        ...

    async def search(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return ranked chunks for one query."""
        ...

    def start_ingest(self) -> IngestAccepted:
        """Start one background ingest or raise busy/unavailable."""
        ...

    def get_ingest(self, run_id: int) -> IngestStatus | None:
        """Return one ingestion_runs row."""
        ...

    def get_current_ingest(self) -> IngestStatus | None:
        """Return the newest ingestion_runs row."""
        ...

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
        """Best-effort write to query_logs."""
        ...

    def close(self) -> None:
        """Release backend clients."""
        ...

    async def generate(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
    ) -> dict[str, object]:
        """Return a structured RAG answer or a refusal payload."""
        ...


def create_app(*, runtime: AppRuntime | None = None) -> FastAPI:
    """Build the ASGI app. Pass ``runtime`` in tests to skip loading e5."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runtime = runtime if runtime is not None else build_runtime()
        try:
            yield
        finally:
            current = getattr(app.state, "runtime", None)
            if current is not None:
                current.close()

    application = FastAPI(
        title="Obsidian RAG retriever",
        lifespan=lifespan,
    )
    application.include_router(_build_router())
    return application


def _build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health(request: Request) -> JSONResponse:
        runtime = _optional_runtime(request)
        model_loaded = bool(runtime is not None and runtime.model_loaded)
        qdrant_ok = bool(runtime is not None and runtime.ping_qdrant())
        ready = model_loaded and qdrant_ok
        payload = HealthResponse(
            status="ok" if ready else "degraded",
            model_loaded=model_loaded,
            qdrant="ok" if qdrant_ok else "unreachable",
        )
        status_code = 200 if ready else 503
        return JSONResponse(
            status_code=status_code,
            content=payload.model_dump(mode="json"),
        )

    @router.post("/search")
    async def search(body: SearchRequest, request: Request) -> SearchResponse:
        runtime = _require_runtime(request)
        top_k = runtime.default_top_k if body.top_k is None else body.top_k
        if not runtime.model_loaded:
            _record_search_log(
                runtime,
                query=body.query,
                method=body.method,
                top_k=top_k,
                started=perf_counter(),
                result_count=0,
                error="embedding model is not loaded",
            )
            raise HTTPException(
                status_code=503,
                detail="embedding model is not loaded",
            )
        if not runtime.ping_qdrant():
            _record_search_log(
                runtime,
                query=body.query,
                method=body.method,
                top_k=top_k,
                started=perf_counter(),
                result_count=0,
                error="qdrant is unreachable",
            )
            raise HTTPException(status_code=503, detail="qdrant is unreachable")
        started = perf_counter()
        error: str | None = None
        chunks: list[RetrievedChunk] = []
        try:
            chunks = await runtime.search(
                body.query,
                method=body.method,
                top_k=top_k,
            )
        except RetrieverUnavailableError as exc:
            error = str(exc)
            _record_search_log(
                runtime,
                query=body.query,
                method=body.method,
                top_k=top_k,
                started=started,
                result_count=0,
                error=error,
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        _record_search_log(
            runtime,
            query=body.query,
            method=body.method,
            top_k=top_k,
            started=started,
            result_count=len(chunks),
            error=None,
        )
        return SearchResponse(
            query=body.query,
            method=body.method,
            top_k=top_k,
            results=[SearchHit.from_chunk(chunk) for chunk in chunks],
        )

    @router.post("/generate")
    async def generate(body: GenerateRequest, request: Request) -> GenerateResponse:
        runtime = _require_runtime(request)
        top_k = runtime.default_top_k if body.top_k is None else body.top_k
        if not runtime.model_loaded:
            raise HTTPException(
                status_code=503,
                detail="embedding model is not loaded",
            )
        if not runtime.ping_qdrant():
            raise HTTPException(status_code=503, detail="qdrant is unreachable")
        try:
            payload = await runtime.generate(
                body.query,
                method=body.method,
                top_k=top_k,
            )
        except RetrieverUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return GenerateResponse.model_validate(payload)

    @router.post("/ingest")
    async def ingest(request: Request) -> JSONResponse:
        runtime = _require_runtime(request)
        try:
            accepted = runtime.start_ingest()
        except IngestBusyError:
            raise HTTPException(
                status_code=409,
                detail="an ingest run is already in progress",
            ) from None
        except IngestUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return JSONResponse(
            status_code=202,
            content=accepted.model_dump(mode="json"),
        )

    @router.get("/ingest/current")
    async def ingest_current(request: Request) -> IngestStatus:
        runtime = _require_runtime(request)
        try:
            status = runtime.get_current_ingest()
        except IngestUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if status is None:
            raise HTTPException(status_code=404, detail="no ingest runs yet")
        return status

    @router.get("/ingest/{run_id}")
    async def ingest_status(run_id: int, request: Request) -> IngestStatus:
        runtime = _require_runtime(request)
        try:
            status = runtime.get_ingest(run_id)
        except IngestUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if status is None:
            raise HTTPException(status_code=404, detail="ingest run not found")
        return status

    return router


def _record_search_log(
    runtime: AppRuntime,
    *,
    query: str,
    method: RetrievalMethod,
    top_k: int,
    started: float,
    result_count: int,
    error: str | None,
) -> None:
    latency_ms = max(int((perf_counter() - started) * 1000), 0)
    runtime.record_query_log(
        query=query,
        method=method,
        top_k=top_k,
        latency_ms=latency_ms,
        result_count=result_count,
        error=error,
    )


def _optional_runtime(request: Request) -> AppRuntime | None:
    return getattr(request.app.state, "runtime", None)


def _require_runtime(request: Request) -> AppRuntime:
    runtime = _optional_runtime(request)
    if runtime is None:
        raise HTTPException(status_code=503, detail="retriever is not ready")
    return runtime


app = create_app()
