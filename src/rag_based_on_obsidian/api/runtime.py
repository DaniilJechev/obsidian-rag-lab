"""Long-lived retrieval process: one e5 load, one Qdrant client, three methods."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import replace
from pathlib import Path

import yaml
from qdrant_client import QdrantClient
from sqlalchemy import text

from rag_based_on_obsidian.api.ingest import (
    IngestService,
    IngestUnavailableError,
    build_ingest_engine,
)
from rag_based_on_obsidian.api.query_logs import write_query_log
from rag_based_on_obsidian.api.schemas import IngestAccepted, IngestStatus
from rag_based_on_obsidian.config import (
    DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    DEFAULT_LLM_CONFIG_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
    DEFAULT_RAGAS_CONFIG_PATH,
    DEFAULT_RETRIEVAL_CONFIG_PATH,
    load_config,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import versioned_collection_name
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.llm.openrouter import OpenRouterLLMProvider
from rag_based_on_obsidian.llm.pipeline import run_rag_generate
from rag_based_on_obsidian.llm.settings import LLMConfig, load_llm_config
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever
from rag_based_on_obsidian.retrieval.lexical import QdrantSparseRetriever
from rag_based_on_obsidian.retrieval.pipeline import HybridRetriever
from rag_based_on_obsidian.retrieval.settings import (
    RetrievalConfig,
    load_retrieval_config,
)
from rag_based_on_obsidian.vector_store.settings import QdrantConfig, load_qdrant_config

logger = logging.getLogger(__name__)

DEFAULT_QDRANT_TIMEOUT_SECONDS = 10.0
DEFAULT_SEARCH_TIMEOUT_SECONDS = 30.0


class RetrieverUnavailableError(Exception):
    """Search cannot run: Qdrant, timeout, or a missing runtime."""


class RetrieverRuntime:
    """Hold the warm embedder and retrievers for the life of the HTTP process."""

    def __init__(
        self,
        *,
        client: QdrantClient,
        provider: TransformersEmbeddingProvider,
        dense: QdrantDenseRetriever,
        lexical: QdrantSparseRetriever,
        hybrid: HybridRetriever,
        retrieval_config: RetrievalConfig,
        search_timeout_seconds: float,
        batch_config: BatchEmbeddingConfig,
        qdrant_config: QdrantConfig,
        llm_config: LLMConfig,
        model_loaded: bool = True,
    ) -> None:
        self._client = client
        self._provider = provider
        self._dense = dense
        self._lexical = lexical
        self._hybrid = hybrid
        self.retrieval_config = retrieval_config
        self.search_timeout_seconds = search_timeout_seconds
        self._batch_config = batch_config
        self._qdrant_config = qdrant_config
        self._llm_config = llm_config
        self.model_loaded = model_loaded
        self.default_top_k = retrieval_config.top_k
        self.retrieval_embedding_model = provider.metadata.model_name
        self.generate_model = llm_config.model
        self.judge_model = _read_judge_model_pin()
        # Same e5 pin as retrieval today; exposed separately because ragas
        # Answer Relevancy embeds on the host CLI, not inside /generate.
        self.evaluation_embedding_model = provider.metadata.model_name
        self._engine = None
        self._ingest: IngestService | None = None

    def ping_qdrant(self) -> bool:
        """Return True when Qdrant answers a cheap metadata call."""
        try:
            self._client.get_collections()
        except Exception:
            logger.exception("qdrant ping failed")
            return False
        return True

    def ping_postgres(self) -> bool:
        """Return True when Postgres answers ``SELECT 1``."""
        try:
            engine = self._ensure_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            logger.exception("postgres ping failed")
            return False
        return True

    async def search(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Run one retrieval method without reloading e5."""
        filters = dict(self.retrieval_config.filters)
        candidate_k = max(self.retrieval_config.candidate_k, top_k)
        rrf_k = self.retrieval_config.rrf_k
        try:
            return await asyncio.wait_for(
                self._search_method(
                    query,
                    method=method,
                    top_k=top_k,
                    candidate_k=candidate_k,
                    rrf_k=rrf_k,
                    filters=filters,
                ),
                timeout=self.search_timeout_seconds,
            )
        except TimeoutError as exc:
            raise RetrieverUnavailableError("search timed out") from exc
        except RetrieverUnavailableError:
            raise
        except Exception as exc:
            logger.exception("retrieval failed method=%s", method)
            raise RetrieverUnavailableError("retrieval backend failed") from exc

    async def _search_method(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
        candidate_k: int,
        rrf_k: int,
        filters: dict[str, object],
    ) -> list[RetrievedChunk]:
        if method is RetrievalMethod.DENSE:
            return await asyncio.to_thread(
                self._dense.search,
                query,
                top_k=top_k,
                filters=filters,
            )
        if method is RetrievalMethod.BM25:
            return await asyncio.to_thread(
                self._lexical.search,
                query,
                top_k=top_k,
                filters=filters,
            )
        return await self._hybrid.search(
            query,
            top_k=top_k,
            candidate_k=candidate_k,
            rrf_k=rrf_k,
            filters=filters,
        )

    async def generate(
        self,
        query: str,
        *,
        method: RetrievalMethod,
        top_k: int,
        model: str | None = None,
    ) -> dict[str, object]:
        """Retrieve, then call OpenRouter or refuse. Search stays available."""
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        llm_config = self._llm_config
        if model is not None and model.strip():
            llm_config = replace(self._llm_config, model=model.strip())
        provider = OpenRouterLLMProvider(llm_config, api_key=api_key)
        return await run_rag_generate(
            self.search,
            provider,
            llm_config,
            query,
            method=method,
            top_k=top_k,
        )

    def start_ingest(self) -> IngestAccepted:
        """Accept one background chunk+upsert job or raise busy/unavailable."""
        return self._ensure_ingest().start()

    def get_ingest(self, run_id: int) -> IngestStatus | None:
        """Read ``ingestion_runs`` for one HTTP job id."""
        return self._ensure_ingest().get(run_id)

    def get_current_ingest(self) -> IngestStatus | None:
        """Read the newest ``ingestion_runs`` row."""
        return self._ensure_ingest().get_current()

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
        """Best-effort insert into ``query_logs``."""
        engine = None
        try:
            engine = self._ensure_engine()
        except IngestUnavailableError:
            logger.warning("query log skipped: PostgreSQL is not configured")
        write_query_log(
            engine,
            query=query,
            method=method,
            top_k=top_k,
            latency_ms=latency_ms,
            result_count=result_count,
            error=error,
        )

    def _ensure_engine(self):
        if self._engine is None:
            try:
                self._engine = build_ingest_engine()
            except Exception as exc:
                raise IngestUnavailableError(
                    "PostgreSQL is not configured for ingest/query logs"
                ) from exc
        return self._engine

    def _ensure_ingest(self) -> IngestService:
        if self._ingest is None:
            try:
                app_config = load_config()
                engine = self._ensure_engine()
            except IngestUnavailableError:
                raise
            except Exception as exc:
                raise IngestUnavailableError(str(exc)) from exc
            self._ingest = IngestService(
                engine=engine,
                provider=self._provider,
                qdrant_client=self._client,
                batch_config=self._batch_config,
                qdrant_config=self._qdrant_config,
                vault_root=app_config.vault_root,
                allowed_directories=app_config.allowed_corpus_directories,
            )
        return self._ingest

    def close(self) -> None:
        """Release the Qdrant client and Postgres engine. Process exit unloads e5."""
        self._client.close()
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


def build_runtime() -> RetrieverRuntime:
    """Load YAML, connect to Qdrant, and load e5 once for all HTTP methods."""
    model_config_path = Path(
        os.environ.get(
            "EMBEDDING_MODEL_CONFIG_PATH",
            str(DEFAULT_EMBEDDING_MODEL_CONFIG_PATH),
        )
    )
    batch_config_path = Path(
        os.environ.get(
            "BATCH_EMBEDDING_CONFIG_PATH",
            str(DEFAULT_BATCH_EMBEDDING_CONFIG_PATH),
        )
    )
    qdrant_config_path = Path(
        os.environ.get(
            "QDRANT_CONFIG_PATH",
            str(DEFAULT_QDRANT_CONFIG_PATH),
        )
    )
    retrieval_config_path = Path(
        os.environ.get(
            "RETRIEVAL_CONFIG_PATH",
            str(DEFAULT_RETRIEVAL_CONFIG_PATH),
        )
    )
    llm_config_path = Path(
        os.environ.get(
            "LLM_CONFIG_PATH",
            str(DEFAULT_LLM_CONFIG_PATH),
        )
    )
    qdrant_timeout = float(
        os.environ.get(
            "QDRANT_TIMEOUT_SECONDS",
            str(DEFAULT_QDRANT_TIMEOUT_SECONDS),
        )
    )
    search_timeout = float(
        os.environ.get(
            "SEARCH_TIMEOUT_SECONDS",
            str(DEFAULT_SEARCH_TIMEOUT_SECONDS),
        )
    )

    model_config = load_embedding_model_config(model_config_path)
    batch_config = load_batch_embedding_config(batch_config_path)
    qdrant_config = load_qdrant_config(qdrant_config_path)
    qdrant_url = os.environ.get("QDRANT_URL", qdrant_config.url).strip()
    if qdrant_url:
        qdrant_config = replace(qdrant_config, url=qdrant_url)
    retrieval_config = load_retrieval_config(retrieval_config_path)
    llm_config = load_llm_config(llm_config_path)

    client = QdrantClient(url=qdrant_config.url, timeout=qdrant_timeout)
    try:
        provider = TransformersEmbeddingProvider(model_config)
        collection_name = versioned_collection_name(
            qdrant_config.collection,
            batch_config.chunking_version,
            model_name=provider.metadata.model_name,
            model_revision=provider.metadata.model_revision,
            vector_size=provider.metadata.dimension,
        )
        dense = QdrantDenseRetriever(
            client,
            collection_name=collection_name,
            provider=provider,
        )
        lexical = QdrantSparseRetriever(
            client,
            collection_name=collection_name,
            chunking_version=retrieval_config.chunking_version,
            bm25_avg_len=qdrant_config.bm25_avg_len,
            bm25_model=qdrant_config.bm25_model,
        )
        hybrid = HybridRetriever(dense=dense, lexical=lexical, provider=provider)
        return RetrieverRuntime(
            client=client,
            provider=provider,
            dense=dense,
            lexical=lexical,
            hybrid=hybrid,
            retrieval_config=retrieval_config,
            search_timeout_seconds=search_timeout,
            batch_config=batch_config,
            qdrant_config=qdrant_config,
            llm_config=llm_config,
        )
    except Exception:
        client.close()
        raise


def _read_judge_model_pin(path: Path | None = None) -> str | None:
    """Read ``judge_model`` from ragas YAML without loading gold or eval config.

    The judge runs in ``rag-cli`` on the host. Health still reports the pin
    baked into this process's configs (the Docker image until ``--build``).
    """
    config_path = path or DEFAULT_RAGAS_CONFIG_PATH
    try:
        with config_path.open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except FileNotFoundError:
        logger.warning("judge pin missing: %s", config_path)
        return None
    except Exception:
        logger.exception("failed to read judge pin from %s", config_path)
        return None
    if not isinstance(raw, dict):
        return None
    value = raw.get("judge_model")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
