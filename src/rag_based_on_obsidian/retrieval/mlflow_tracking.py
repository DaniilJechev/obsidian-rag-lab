"""MLflow tracking for synthetic retrieval searches."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping

import mlflow
from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    DEFAULT_MLFLOW_TRACKING_URI,
    ENV_FILE,
)

SEARCH_EXPERIMENT_NAME = "searching"
SEARCH_EXPERIMENT_DESCRIPTION = (
    "Sprint 15 retrieval searches tracking operation type, latency, "
    "result counts and stage timings for dense, BM25 and hybrid smoke runs. "
    "These runs record technical correctness only, not semantic quality."
)


def log_search_run(
    *,
    operation: str,
    query: str,
    top_k: int,
    candidate_k: int,
    rrf_k: int,
    chunking_version: str,
    result_count: int,
    duration_seconds: float,
    stage_seconds: Mapping[str, float],
    collection_name: str | None = None,
    model_name: str | None = None,
    model_revision: str | None = None,
    device: str | None = None,
    dimension: int | None = None,
    error: str | None = None,
) -> str | None:
    """Log one search attempt to the searching experiment."""
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    _configure_search_experiment()
    with mlflow.start_run(run_name=f"search-{operation}") as run:
        params: dict[str, object] = {
            "operation": operation,
            "query": query[:500],
            "query_length": len(query),
            "top_k": top_k,
            "candidate_k": candidate_k,
            "rrf_k": rrf_k,
            "chunking_version": chunking_version,
        }
        if collection_name:
            params["collection_name"] = collection_name
        if model_name:
            params["model_name"] = model_name
        if model_revision:
            params["model_revision"] = model_revision
        if device:
            params["device"] = device
        if dimension is not None:
            params["dimension"] = dimension
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.set_tags(
            {
                "git_commit": _git_commit(),
                "phase": "5",
                "sprint": "15",
                "task": "RET-002",
                "experiment_type": "retrieval-search",
                "search_operation": operation,
                "search_status": "error" if error else "ok",
            }
        )
        metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "result_count": float(result_count),
            "query_length": float(len(query)),
            "top_k": float(top_k),
        }
        for stage, seconds in stage_seconds.items():
            metrics[f"stage_{stage}_seconds"] = seconds
        mlflow.log_metrics(metrics)
        if error:
            mlflow.set_tag("error", error[:500])
        return run.info.run_id


def _configure_search_experiment() -> None:
    """Create and describe the searching experiment before a run."""
    experiment_tags = {
        "mlflow.note.content": SEARCH_EXPERIMENT_DESCRIPTION,
        "phase": "5",
        "sprint": "15",
        "task": "RET-002",
        "experiment_type": "retrieval-search",
    }
    experiment = mlflow.get_experiment_by_name(SEARCH_EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(SEARCH_EXPERIMENT_NAME, tags=experiment_tags)
    mlflow.set_experiment(SEARCH_EXPERIMENT_NAME)
    for key, value in experiment_tags.items():
        mlflow.set_experiment_tag(key, value)


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
