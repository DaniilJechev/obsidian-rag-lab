"""Background HTTP ingest: one in-flight job, production chunking policy."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from sqlalchemy import Engine, create_engine, select

from rag_based_on_obsidian.api.schemas import IngestAccepted, IngestStatus
from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.chunking.postgres_ingestion import materialize_policy
from rag_based_on_obsidian.config import CHUNKING_CONFIG_DIR
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.db.schema import ingestion_runs
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    BatchEmbeddingResult,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import (
    QdrantVectorSink,
    versioned_collection_name,
)
from rag_based_on_obsidian.embeddings.settings import BatchEmbeddingConfig
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.ingestion.contracts import RunCounters
from rag_based_on_obsidian.ingestion.repositories import IngestionRunRepository
from rag_based_on_obsidian.vector_store.settings import QdrantConfig

logger = logging.getLogger(__name__)

PRODUCTION_POLICY_PATH = CHUNKING_CONFIG_DIR / "policy_chunking_512.yaml"
PRODUCTION_CHUNKING_VERSION = "sprint9-policy-512-v2"


class IngestBusyError(Exception):
    """A second HTTP ingest arrived while one is still running."""


class IngestUnavailableError(Exception):
    """Ingest cannot start: vault, Postgres, or configuration is missing."""


class IngestService:
    """Serialize HTTP ingest and record progress on ``ingestion_runs``."""

    def __init__(
        self,
        *,
        engine: Engine,
        provider: TransformersEmbeddingProvider,
        qdrant_client: QdrantClient,
        batch_config: BatchEmbeddingConfig,
        qdrant_config: QdrantConfig,
        vault_root: Path,
        allowed_directories: tuple[str, ...],
        policy_path: Path = PRODUCTION_POLICY_PATH,
    ) -> None:
        self._engine = engine
        self._provider = provider
        self._qdrant_client = qdrant_client
        self._batch_config = batch_config
        self._qdrant_config = qdrant_config
        self._vault_root = vault_root
        self._allowed_directories = allowed_directories
        self._policy_path = policy_path
        self._busy = False
        self._guard = threading.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    def start(self) -> IngestAccepted:
        """Insert a running row, spawn background work, return immediately."""
        self._assert_vault_ready()
        if self._batch_config.chunking_version != PRODUCTION_CHUNKING_VERSION:
            raise IngestUnavailableError(
                "batch embedding chunking_version must match production "
                f"{PRODUCTION_CHUNKING_VERSION}"
            )
        with self._guard:
            if self._busy:
                raise IngestBusyError
            self._busy = True
        try:
            with self._engine.begin() as connection:
                run_id = IngestionRunRepository(connection).create(
                    corpus_scope=",".join(self._allowed_directories)
                )
        except Exception as exc:
            with self._guard:
                self._busy = False
            raise IngestUnavailableError(
                "failed to create ingestion_runs row"
            ) from exc
        try:
            task = asyncio.get_running_loop().create_task(
                asyncio.to_thread(self._run, run_id)
            )
        except RuntimeError:
            threading.Thread(target=self._run, args=(run_id,), daemon=True).start()
        else:
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        return IngestAccepted(run_id=run_id, status="running")

    def get(self, run_id: int) -> IngestStatus | None:
        """Return one ingestion_runs row, or None if it does not exist."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(ingestion_runs).where(ingestion_runs.c.run_id == run_id)
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return self._status_from_row(row)

    def get_current(self) -> IngestStatus | None:
        """Return the newest ingestion_runs row, or None if the table is empty."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(ingestion_runs)
                    .order_by(ingestion_runs.c.run_id.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return self._status_from_row(row)

    @staticmethod
    def _status_from_row(row: Mapping[str, Any]) -> IngestStatus:
        return IngestStatus(
            run_id=int(row["run_id"]),
            status=str(row["status"]),
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            corpus_scope=str(row["corpus_scope"]),
            documents_total=int(row["documents_total"]),
            documents_succeeded=int(row["documents_succeeded"]),
            documents_failed=int(row["documents_failed"]),
            documents_skipped=int(row["documents_skipped"]),
        )

    def _assert_vault_ready(self) -> None:
        if not self._vault_root.is_dir():
            raise IngestUnavailableError(
                f"vault is not mounted or not a directory: {self._vault_root}"
            )
        if not self._policy_path.is_file():
            raise IngestUnavailableError(
                f"production chunking policy missing: {self._policy_path}"
            )
        for directory in self._allowed_directories:
            candidate = self._vault_root / directory
            if not candidate.is_dir():
                raise IngestUnavailableError(
                    f"corpus directory missing under vault: {directory}"
                )

    def _run(self, run_id: int) -> None:
        try:
            with self._engine.connect() as connection:
                chunk_result = materialize_policy(
                    connection,
                    vault_root=self._vault_root,
                    allowed_directories=self._allowed_directories,
                    policy_path=self._policy_path,
                )
            embed_result = self._upsert_dense_sparse()
            if embed_result.failures and embed_result.embeddings_succeeded == 0:
                status = "failed"
            elif embed_result.failures:
                status = "partial"
            else:
                status = "completed"
            counters = RunCounters(
                total=chunk_result.documents,
                new=chunk_result.documents,
            )
            self._finish(run_id, counters, status=status)
        except Exception:
            logger.exception("ingest run_id=%s failed", run_id)
            try:
                self._finish(run_id, RunCounters(), status="failed")
            except Exception:
                logger.exception("failed to mark ingest failed run_id=%s", run_id)
        finally:
            with self._guard:
                self._busy = False

    def _upsert_dense_sparse(self) -> BatchEmbeddingResult:
        """Same pipeline as CLI upsert-dense-sparse, reusing the warm e5."""
        metadata = self._provider.metadata
        with self._engine.connect() as connection:
            repository = ChunkRepository(connection)
            collection_name = versioned_collection_name(
                self._qdrant_config.collection,
                self._batch_config.chunking_version,
                model_name=metadata.model_name,
                model_revision=metadata.model_revision,
                vector_size=metadata.dimension,
            )
            sink = QdrantVectorSink.from_url(
                self._qdrant_config.url,
                collection_name=collection_name,
                vector_size=metadata.dimension,
                max_retries=self._qdrant_config.max_retries,
                retry_backoff_seconds=self._qdrant_config.retry_backoff_seconds,
                bm25_avg_len=self._qdrant_config.bm25_avg_len,
                bm25_model=self._qdrant_config.bm25_model,
            )
            try:
                pipeline = BatchEmbeddingPipeline(
                    self._provider,
                    self._batch_config,
                    stage_logger=logger.info,
                )
                return pipeline.execute(
                    repository, sink=sink, log_mlflow=False
                )
            finally:
                sink.client.close()

    def _finish(self, run_id: int, counters: RunCounters, *, status: str) -> None:
        with self._engine.begin() as connection:
            IngestionRunRepository(connection).finish(
                run_id, counters, status=status
            )


def build_ingest_engine() -> Engine:
    """Open PostgreSQL for ingest rows and query logs. Caller disposes it."""
    return create_engine(load_database_url())
