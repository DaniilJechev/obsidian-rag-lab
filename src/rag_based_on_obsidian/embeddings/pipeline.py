"""Batch orchestration, validation and temporary artifact persistence."""

import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
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

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> Iterable[list[dict[str, object]]]:
        """Yield stable, bounded batches for one chunking version."""


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
    failures: tuple[EmbeddingFailure, ...]
    chunks_total: int
    batches_total: int
    batches_succeeded: int
    attempts_total: int
    duration_seconds: float

    @property
    def metrics(self) -> dict[str, float]:
        """Return MLflow- and JSON-compatible operational metrics."""
        return {
            "chunks_total": float(self.chunks_total),
            "embeddings_succeeded": float(len(self.embeddings)),
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
        }


class JsonArtifactWriter:
    """Write reproducible JSON handoff files with atomic replacement."""

    def write(
        self,
        result: BatchEmbeddingResult,
        *,
        provider: EmbeddingProvider,
        config: BatchEmbeddingConfig,
    ) -> tuple[Path, Path, Path]:
        """Write embeddings, manifest and metrics and return their paths."""
        config.artifact_dir.mkdir(parents=True, exist_ok=True)
        embeddings_path = config.artifact_dir / "embeddings.json"
        manifest_path = config.artifact_dir / "manifest.json"
        metrics_path = config.artifact_dir / "metrics.json"

        embeddings_payload = [
            {
                "chunk_id": item.chunk_id,
                "note_id": item.note_id,
                "chunk_index": item.chunk_index,
                "chunking_version": item.chunking_version,
                "vector": list(item.vector),
            }
            for item in result.embeddings
        ]
        manifest_payload = {
            "artifact_format": "temporary-json-v1",
            "pipeline_name": config.name,
            "chunking_version": config.chunking_version,
            "batch_size": config.batch_size,
            "max_retries": config.max_retries,
            "model_name": provider.metadata.model_name,
            "model_revision": provider.metadata.model_revision,
            "device": provider.metadata.device,
            "dimension": provider.metadata.dimension,
            "normalized": provider.metadata.normalized,
            "chunks_total": result.chunks_total,
            "embeddings_succeeded": len(result.embeddings),
            "embeddings_failed": len(result.failures),
        }
        metrics_payload: dict[str, object] = {
            **result.metrics,
            "failed_chunks": [asdict(failure) for failure in result.failures],
        }
        _atomic_write_json(embeddings_path, embeddings_payload)
        _atomic_write_json(manifest_path, manifest_payload)
        _atomic_write_json(metrics_path, metrics_payload)
        return embeddings_path, manifest_path, metrics_path


class BatchEmbeddingPipeline:
    """Embed versioned PostgreSQL chunks with bounded batches and retries."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        config: BatchEmbeddingConfig,
        *,
        progress_factory: Callable[..., Any] = tqdm,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        self.provider = provider
        self.config = config
        self._progress_factory = progress_factory
        self._sleep = sleep_fn

    def run(self, repository: ChunkBatchReader) -> BatchEmbeddingResult:
        """Read and embed one explicit chunking version from PostgreSQL."""
        return self._run_batches(
            repository.iter_by_version(
                chunking_version=self.config.chunking_version,
                batch_size=self.config.batch_size,
            )
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
        return self._run_batches(_split_batches(ordered, self.config.batch_size))

    def execute(
        self,
        repository: ChunkBatchReader,
        *,
        artifact_writer: JsonArtifactWriter | None = None,
    ) -> BatchEmbeddingResult:
        """Run, persist temporary artifacts and log the completed MLflow run."""
        result = self.run(repository)
        writer = artifact_writer or JsonArtifactWriter()
        writer.write(result, provider=self.provider, config=self.config)
        log_batch_embedding_run(
            provider=self.provider,
            config=self.config,
            metrics=result.metrics,
        )
        return result

    def _run_batches(
        self,
        batches: Iterable[Sequence[ChunkRow]],
    ) -> BatchEmbeddingResult:
        started_at = perf_counter()
        embeddings: list[EmbeddedChunk] = []
        failures: list[EmbeddingFailure] = []
        chunks_total = 0
        batches_total = 0
        batches_succeeded = 0
        attempts_total = 0
        progress = self._progress_factory(
            desc="Embedding chunk batches",
            unit="batch",
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
                    batches_succeeded += 1
                    embeddings.extend(batch_embeddings)
                progress.update(1)
        finally:
            progress.close()

        return BatchEmbeddingResult(
            embeddings=tuple(embeddings),
            failures=tuple(failures),
            chunks_total=chunks_total,
            batches_total=batches_total,
            batches_succeeded=batches_succeeded,
            attempts_total=attempts_total,
            duration_seconds=perf_counter() - started_at,
        )

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


def _atomic_write_json(path: Path, payload: object) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary_path.replace(path)
