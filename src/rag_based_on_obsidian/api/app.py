"""FastAPI application: lifespan loads e5 once; routes hide retrieval internals."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from rag_based_on_obsidian.api.runtime import (
    RetrieverUnavailableError,
    build_runtime,
)
from rag_based_on_obsidian.api.schemas import (
    HealthResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


class SearchRuntime(Protocol):
    """Minimal surface the HTTP layer needs. Tests inject a fake."""

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

    def close(self) -> None:
        """Release backend clients."""
        ...


def create_app(*, runtime: SearchRuntime | None = None) -> FastAPI:
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
        if not runtime.model_loaded:
            raise HTTPException(
                status_code=503,
                detail="embedding model is not loaded",
            )
        if not runtime.ping_qdrant():
            raise HTTPException(status_code=503, detail="qdrant is unreachable")
        top_k = runtime.default_top_k if body.top_k is None else body.top_k
        try:
            chunks = await runtime.search(
                body.query,
                method=body.method,
                top_k=top_k,
            )
        except RetrieverUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return SearchResponse(
            query=body.query,
            method=body.method,
            top_k=top_k,
            results=[SearchHit.from_chunk(chunk) for chunk in chunks],
        )

    return router


def _optional_runtime(request: Request) -> SearchRuntime | None:
    return getattr(request.app.state, "runtime", None)


def _require_runtime(request: Request) -> SearchRuntime:
    runtime = _optional_runtime(request)
    if runtime is None:
        raise HTTPException(status_code=503, detail="retriever is not ready")
    return runtime


app = create_app()
