"""Batch orchestration, validation and vector persistence."""

import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from time import perf_counter, sleep
from typing import Any, Protocol

from tqdm import tqdm

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingProvider,
    EmbeddingVector,
    validate_vectors,
)
from rag_based_on_obsidian.embeddings.mlflow_tracking import (
    log_batch_embedding_run,
)
from rag_based_on_obsidian.embeddings.settings import BatchEmbeddingConfig

type ChunkRow = Mapping[str, object]


class ChunkBatchReader(Protocol):
    """Minimal repository contract required by the batch pipeline."""

    def count_by_version(self, *, chunking_version: str) -> int:
        """Return the total number of chunks for one version."""

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> Iterable[list[dict[str, object]]]:
        """Yield stable, bounded batches for one chunking version."""


@dataclass(frozen=True)
class SinkWriteResult:
    """Operational evidence returned after one durable sink write."""

    points_written: int
    duration_seconds: float
    attempts: int
    vector_bytes: int


class SinkWriteError(RuntimeError):
    """A sink failed after exhausting its own retry budget."""

    def __init__(self, message: str, *, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


class EmbeddingSink(Protocol):
    """Persistence boundary for validated embedding batches."""

    def upsert_batch(
        self,
        embeddings: Sequence["EmbeddedChunk"],
        chunks: Sequence[ChunkRow],
    ) -> SinkWriteResult:
        """Persist one validated batch and return only after it is durable."""


@dataclass(frozen=True)
class EmbeddedChunk:
    """A vector paired with the immutable chunk identity it represents."""

    chunk_id: int
    note_id: int
    chunk_index: int
    chunking_version: str
    vector: EmbeddingVector


@dataclass(frozen=True)
class EmbeddingFailure:
    """A chunk that belongs to a batch that exhausted its retry budget."""

    chunk_id: int
    attempts: int
    error_type: str
    error_message: str


@dataclass(frozen=True)
class BatchEmbeddingResult:
    """Complete outcome of one deterministic batch embedding run."""

    embeddings: tuple[EmbeddedChunk, ...]
    embeddings_succeeded: int
    failures: tuple[EmbeddingFailure, ...]
    chunks_total: int
    batches_total: int
    batches_succeeded: int
    attempts_total: int
    duration_seconds: float
    upsert_batches_total: int = 0
    upsert_points: int = 0
    upsert_duration_seconds: float = 0.0
    qdrant_errors: int = 0
    qdrant_embedding_bytes: int = 0
    consistency_mismatches: int = 0
    mlflow_run_id: str | None = None

    @property
    def metrics(self) -> dict[str, float]:
        """Return MLflow- and JSON-compatible operational metrics."""
        return {
            "chunks_total": float(self.chunks_total),
            "embeddings_succeeded": float(self.embeddings_succeeded),
            "embeddings_failed": float(len(self.failures)),
            "batches_total": float(self.batches_total),
            "batches_succeeded": float(self.batches_succeeded),
            "batches_failed": float(self.batches_total - self.batches_succeeded),
            "attempts_total": float(self.attempts_total),
            "duration_seconds": self.duration_seconds,
            "embeddings_per_second": (
                len(self.embeddings) / self.duration_seconds
                if self.duration_seconds > 0
                else 0.0
            ),
            "failure_rate": (
                len(self.failures) / self.chunks_total
                if self.chunks_total
                else 0.0
            ),
            "upsert_batches_total": float(self.upsert_batches_total),
            "upsert_points": float(self.upsert_points),
            "upsert_duration_seconds": self.upsert_duration_seconds,
            "upsert_throughput": (
                self.upsert_points / self.upsert_duration_seconds
                if self.upsert_duration_seconds > 0
                else 0.0
            ),
            "qdrant_errors": float(self.qdrant_errors),
            "qdrant_embedding_bytes": float(self.qdrant_embedding_bytes),
            "qdrant_embedding_storage_bytes": float(
                self.qdrant_embedding_bytes
            ),
            "consistency_mismatches": float(self.consistency_mismatches),
        }


class BatchEmbeddingPipeline:
    """Embed versioned PostgreSQL chunks with bounded batches and retries."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        config: BatchEmbeddingConfig,
        *,
        progress_factory: Callable[..., Any] = tqdm,
        sleep_fn: Callable[[float], None] = sleep,
        stage_logger: Callable[[str], None] | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self._progress_factory = progress_factory
        self._sleep = sleep_fn
        self._stage_logger = stage_logger

    def run(self, repository: ChunkBatchReader) -> BatchEmbeddingResult:
        """Read and embed one explicit chunking version from PostgreSQL."""
        total_chunks = repository.count_by_version(
            chunking_version=self.config.chunking_version
        )
        self._log_stage(
            f"Loaded chunk count from PostgreSQL: {total_chunks} "
            f"({self.config.chunking_version})"
        )
        return self._run_batches(
            repository.iter_by_version(
                chunking_version=self.config.chunking_version,
                batch_size=self.config.batch_size,
            ),
            total_chunks=total_chunks,
        )

    def run_chunks(self, chunks: Sequence[ChunkRow]) -> BatchEmbeddingResult:
        """Embed supplied rows in stable order; useful for unit tests."""
        ordered = sorted(
            chunks,
            key=lambda chunk: (
                _required_int(chunk, "note_id"),
                _required_int(chunk, "chunk_index"),
                _required_int(chunk, "chunk_id"),
            ),
        )
        return self._run_batches(
            _split_batches(ordered, self.config.batch_size),
            total_chunks=len(ordered),
        )

    def execute(
        self,
        repository: ChunkBatchReader,
        *,
        sink: EmbeddingSink | None = None,
    ) -> BatchEmbeddingResult:
        """Run, persist batches and log the completed MLflow run."""
        result = self._run_repository(
            repository,
            sink=sink,
            retain_embeddings=False,
        )
        self._log_stage("Logging batch metrics to MLflow")
        run_id = log_batch_embedding_run(
            provider=self.provider,
            config=self.config,
            metrics=result.metrics,
        )
        return replace(result, mlflow_run_id=run_id)

    def _run_repository(
        self,
        repository: ChunkBatchReader,
        *,
        sink: EmbeddingSink | None,
        retain_embeddings: bool,
    ) -> BatchEmbeddingResult:
        """Run repository batches with an optional direct persistence sink."""
        total_chunks = repository.count_by_version(
            chunking_version=self.config.chunking_version
        )
        self._log_stage(
            f"Loaded chunk count from PostgreSQL: {total_chunks} "
            f"({self.config.chunking_version})"
        )
        return self._run_batches(
            repository.iter_by_version(
                chunking_version=self.config.chunking_version,
                batch_size=self.config.batch_size,
            ),
            total_chunks=total_chunks,
            sink=sink,
            retain_embeddings=retain_embeddings,
        )

    def _run_batches(
        self,
        batches: Iterable[Sequence[ChunkRow]],
        *,
        total_chunks: int | None = None,
        sink: EmbeddingSink | None = None,
        retain_embeddings: bool = True,
    ) -> BatchEmbeddingResult:
        started_at = perf_counter()
        embeddings: list[EmbeddedChunk] = []
        failures: list[EmbeddingFailure] = []
        chunks_total = 0
        batches_total = 0
        batches_succeeded = 0
        embeddings_succeeded = 0
        attempts_total = 0
        upsert_batches_total = 0
        upsert_points = 0
        upsert_duration_seconds = 0.0
        qdrant_errors = 0
        qdrant_embedding_bytes = 0
        self._log_stage("Starting embedding inference")
        progress = self._progress_factory(
            desc="Embedding and upserting chunks" if sink else "Embedding chunks",
            total=total_chunks,
            unit="chunk",
            disable=not self.config.show_progress,
        )
        try:
            for batch in batches:
                normalized_batch = _ordered_batch(batch)
                if not normalized_batch:
                    continue
                batches_total += 1
                chunks_total += len(normalized_batch)
                batch_embeddings, batch_failures, attempts = self._embed_batch(
                    normalized_batch
                )
                attempts_total += attempts
                if batch_failures:
                    failures.extend(batch_failures)
                else:
                    try:
                        if sink is not None:
                            self._log_stage(
                                f"Upserting batch {batches_total} "
                                f"({len(batch_embeddings)} points)"
                            )
                            write_result = sink.upsert_batch(
                                batch_embeddings,
                                normalized_batch,
                            )
                        else:
                            write_result = None
                    except SinkWriteError as error:
                        qdrant_errors += error.attempts
                        failures.extend(
                            EmbeddingFailure(
                                chunk_id=_required_int(chunk, "chunk_id"),
                                attempts=error.attempts,
                                error_type=type(error).__name__,
                                error_message=str(error),
                            )
                            for chunk in normalized_batch
                        )
                        progress.update(len(normalized_batch))
                        continue
                    except Exception as error:  # noqa: BLE001
                        qdrant_errors += 1
                        failures.extend(
                            EmbeddingFailure(
                                chunk_id=_required_int(chunk, "chunk_id"),
                                attempts=1,
                                error_type=type(error).__name__,
                                error_message=str(error),
                            )
                            for chunk in normalized_batch
                        )
                        progress.update(len(normalized_batch))
                        continue

                    batches_succeeded += 1
                    embeddings_succeeded += len(batch_embeddings)
                    if retain_embeddings:
                        embeddings.extend(batch_embeddings)
                    if write_result is not None:
                        upsert_batches_total += 1
                        upsert_points += write_result.points_written
                        upsert_duration_seconds += write_result.duration_seconds
                        qdrant_embedding_bytes += write_result.vector_bytes
                progress.update(len(normalized_batch))
        finally:
            progress.close()

        return BatchEmbeddingResult(
            embeddings=tuple(embeddings),
            embeddings_succeeded=embeddings_succeeded,
            failures=tuple(failures),
            chunks_total=chunks_total,
            batches_total=batches_total,
            batches_succeeded=batches_succeeded,
            attempts_total=attempts_total,
            duration_seconds=perf_counter() - started_at,
            upsert_batches_total=upsert_batches_total,
            upsert_points=upsert_points,
            upsert_duration_seconds=upsert_duration_seconds,
            qdrant_errors=qdrant_errors,
            qdrant_embedding_bytes=qdrant_embedding_bytes,
        )

    def _log_stage(self, message: str) -> None:
        if self._stage_logger is not None:
            self._stage_logger(message)

    def _embed_batch(
        self,
        batch: Sequence[ChunkRow],
    ) -> tuple[list[EmbeddedChunk], list[EmbeddingFailure], int]:
        if any(
            chunk.get("chunking_version") != self.config.chunking_version
            for chunk in batch
        ):
            raise ValueError(
                "chunk batch contains a different chunking_version than configured"
            )
        texts = [_required_text(chunk) for chunk in batch]
        attempts = 0
        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 2):
            attempts += 1
            try:
                vectors = self.provider.embed_documents(texts)
                validate_embedding_batch(
                    vectors,
                    self.provider,
                    expected_count=len(batch),
                )
                return (
                    [
                        EmbeddedChunk(
                            chunk_id=_required_int(chunk, "chunk_id"),
                            note_id=_required_int(chunk, "note_id"),
                            chunk_index=_required_int(chunk, "chunk_index"),
                            chunking_version=self.config.chunking_version,
                            vector=vector,
                        )
                        for chunk, vector in zip(batch, vectors, strict=True)
                    ],
                    [],
                    attempts,
                )
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt <= self.config.max_retries:
                    self._sleep(self.config.retry_backoff_seconds)

        assert last_error is not None
        failure = [
            EmbeddingFailure(
                chunk_id=_required_int(chunk, "chunk_id"),
                attempts=attempts,
                error_type=type(last_error).__name__,
                error_message=str(last_error),
            )
            for chunk in batch
        ]
        return [], failure, attempts


def validate_embedding_batch(
    vectors: Sequence[EmbeddingVector],
    provider: EmbeddingProvider,
    *,
    expected_count: int | None = None,
) -> None:
    """Validate count, dimensions, finite values and configured normalization."""
    validate_vectors(
        vectors,
        expected_count=len(vectors) if expected_count is None else expected_count,
        metadata=provider.metadata,
    )
    if not provider.metadata.normalized:
        return
    for vector in vectors:
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError("provider returned a non-normalized vector")


def _ordered_batch(batch: Sequence[ChunkRow]) -> list[ChunkRow]:
    return sorted(
        batch,
        key=lambda chunk: (
            _required_int(chunk, "note_id"),
            _required_int(chunk, "chunk_index"),
            _required_int(chunk, "chunk_id"),
        ),
    )


def _split_batches(
    chunks: Sequence[ChunkRow],
    batch_size: int,
) -> Iterable[list[ChunkRow]]:
    for start in range(0, len(chunks), batch_size):
        yield list(chunks[start : start + batch_size])


def _required_int(chunk: ChunkRow, field: str) -> int:
    value = chunk.get(field)
    if not isinstance(value, int):
        raise TypeError(f"chunk {field} must be an integer")
    return value


def _required_text(chunk: ChunkRow) -> str:
    value = chunk.get("text")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("chunk text must be a non-empty string")
    return value
