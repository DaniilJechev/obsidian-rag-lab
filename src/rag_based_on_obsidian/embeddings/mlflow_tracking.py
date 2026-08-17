"""MLflow tracking for embedding smoke experiments."""

import ctypes
import math
import os
import subprocess
from collections.abc import Mapping, Sequence
from ctypes import wintypes
from time import perf_counter

import mlflow

if os.name != "nt":
    import resource

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingVector,
)
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    EmbeddingModelConfig,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.vector_store.consistency import ConsistencyReport

SMOKE_CHECK_EXPERIMENT_DESCRIPTION = (
    "Sprint 10 CPU embedding experiments tracking model identity, "
    "inference throughput, vector shape, normalization, and runtime memory."
)
BATCH_EXPERIMENT_DESCRIPTION = (
    "Sprint 11 batch embedding experiments tracking versioned PostgreSQL "
    "chunks, retry behavior, throughput, failures and vector-store handoff."
)


def log_embedding_smoke_run(
    provider: TransformersEmbeddingProvider,
    texts: Sequence[str],
    *,
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
    config: EmbeddingModelConfig,
) -> str:
    """Run one embedding smoke sample and log operational evidence."""
    mlflow.set_tracking_uri(tracking_uri)
    _configure_experiment(experiment_name)
    ram_before_mb = process_rss_mb()
    started_at = perf_counter()
    vectors = provider.embed_documents(texts)
    duration_seconds = perf_counter() - started_at
    metrics = embedding_metrics(vectors, duration_seconds)
    ram_after_mb = process_rss_mb()
    metrics.update(
        {
            "ram_usage_mb": ram_after_mb,
            "ram_delta_mb": ram_after_mb - ram_before_mb,
        }
    )
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "model_name": config.model_name,
                "model_revision": config.model_revision,
                "device": provider.metadata.device,
                "dimension": provider.metadata.dimension,
                "normalized": provider.metadata.normalized,
                "max_length": config.max_length,
                "batch_size": config.batch_size,
                "document_prefix": config.document_prefix,
                "query_prefix": config.query_prefix,
                "show_progress": config.show_progress,
            }
        )
        mlflow.set_tags(
            {
                "embedding_model": config.name,
                "git_commit": _git_commit(),
            }
        )
        mlflow.log_metrics(metrics)
        return run.info.run_id


def log_batch_embedding_run(
    provider: TransformersEmbeddingProvider,
    config: BatchEmbeddingConfig,
    metrics: Mapping[str, float],
) -> str:
    """Log one completed batch run without vector-file artifacts."""
    mlflow.set_tracking_uri(config.tracking_uri)
    _configure_batch_experiment(config.experiment_name)
    with mlflow.start_run(run_name=config.run_name) as run:
        mlflow.log_params(
            {
                "model_name": provider.metadata.model_name,
                "model_revision": provider.metadata.model_revision,
                "device": provider.metadata.device,
                "dimension": provider.metadata.dimension,
                "normalized": provider.metadata.normalized,
                "chunking_version": config.chunking_version,
                "pipeline_batch_size": config.batch_size,
                "max_retries": config.max_retries,
                "retry_backoff_seconds": config.retry_backoff_seconds,
            }
        )
        mlflow.set_tags(
            {
                "embedding_model": provider.metadata.model_name,
                "git_commit": _git_commit(),
                "phase": "4",
                "sprint": "11",
                "task": "EMB-002",
                "experiment_type": "batch-embedding",
            }
        )
        mlflow.log_metrics(dict(metrics))
        return run.info.run_id


def log_qdrant_consistency_run(
    *,
    config: BatchEmbeddingConfig,
    collection_name: str,
    report: ConsistencyReport,
) -> str:
    """Log PostgreSQL/Qdrant consistency evidence as an MLflow run."""
    mlflow.set_tracking_uri(config.tracking_uri)
    _configure_batch_experiment(config.experiment_name)
    with mlflow.start_run(run_name=f"{config.run_name}-consistency") as run:
        mlflow.log_params(
            {
                "chunking_version": config.chunking_version,
                "collection_name": collection_name,
            }
        )
        mlflow.set_tags(
            {
                "task": "RET-001",
                "experiment_type": "qdrant-consistency",
            }
        )
        mlflow.log_metrics(
            {
                "postgres_points": report.postgres_points,
                "qdrant_points": report.qdrant_points,
                "missing_points": len(report.missing_point_keys),
                "extra_points": len(report.extra_point_keys),
                "metadata_mismatches": len(report.metadata_mismatches),
                "consistency_mismatches": report.mismatch_count,
            }
        )
        return run.info.run_id


def _configure_experiment(experiment_name: str) -> None:
    """Create and describe an experiment before starting its first run."""
    experiment_tags = {
        "mlflow.note.content": SMOKE_CHECK_EXPERIMENT_DESCRIPTION,
        "phase": "4",
        "sprint": "10",
        "task": "EMB-001",
        "experiment_type": "embedding-smoke",
    }
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        mlflow.create_experiment(experiment_name, tags=experiment_tags)
    mlflow.set_experiment(experiment_name)
    for key, value in experiment_tags.items():
        mlflow.set_experiment_tag(key, value)


def _configure_batch_experiment(experiment_name: str) -> None:
    """Create and describe the Sprint 11 experiment before a run."""
    experiment_tags = {
        "mlflow.note.content": BATCH_EXPERIMENT_DESCRIPTION,
        "phase": "4",
        "sprint": "11",
        "task": "EMB-002",
        "experiment_type": "batch-embedding",
    }
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        mlflow.create_experiment(experiment_name, tags=experiment_tags)
    mlflow.set_experiment(experiment_name)
    for key, value in experiment_tags.items():
        mlflow.set_experiment_tag(key, value)


def process_rss_mb() -> float:
    """Return the current process resident memory in megabytes."""
    if os.name == "nt":
        return _windows_process_rss_mb()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return float(usage.ru_maxrss) / (1024 * 1024)


def _windows_process_rss_mb() -> float:
    """Read Windows process working-set size without extra dependencies."""
    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(ProcessMemoryCounters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_process_memory_info.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    success = get_process_memory_info(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    if not success:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, "GetProcessMemoryInfo failed")
    return float(counters.WorkingSetSize) / (1024 * 1024)


def embedding_metrics(
    vectors: Sequence[EmbeddingVector],
    duration_seconds: float,
) -> dict[str, float]:
    """Calculate operational smoke metrics from one provider run."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    norms = [
        math.sqrt(sum(value * value for value in vector))
        for vector in vectors
    ]
    return {
        "documents_count": float(len(vectors)),
        "duration_seconds": duration_seconds,
        "documents_per_second": len(vectors) / duration_seconds,
        "vector_norm_mean": (
            sum(norms) / len(norms) if norms else 0.0
        ),
        "vector_norm_min": min(norms, default=0.0),
        "vector_norm_max": max(norms, default=0.0),
    }


def _git_commit() -> str:
    """Return the current commit without requiring Git at runtime."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"
