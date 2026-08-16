"""MLflow tracking for embedding smoke experiments."""

import math
import subprocess
from collections.abc import Sequence
from time import perf_counter

import mlflow

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingVector,
)
from rag_based_on_obsidian.embeddings.settings import EmbeddingModelConfig
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
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
    started_at = perf_counter()
    vectors = provider.embed_documents(texts)
    duration_seconds = perf_counter() - started_at
    metrics = embedding_metrics(vectors, duration_seconds)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
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
