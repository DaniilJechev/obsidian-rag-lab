"""MLflow tracking-server client boundary for chunking experiments."""

from __future__ import annotations

import subprocess
from pathlib import Path

import mlflow

from rag_based_on_obsidian.chunking.experiments.core import ExperimentResult


def log_experiment_to_mlflow(
    result: ExperimentResult,
    artifact_dir: Path,
    *,
    experiment_name: str = "sprint-9-chunking-experiments",
    tracking_uri: str,
) -> str:
    """Log one result through the MLflow Tracking Server HTTP API."""
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    params = {
        "policy_name": result.config.policy.name,
        "chunking_version": result.config.chunking_version,
        "chunk_size": result.config.policy.chunk_size,
        "chunk_overlap": result.config.policy.chunk_overlap,
        "short_chunk_fraction": result.short_chunk_fraction,
        "config_sha256": result.config.config_sha256,
        "git_commit": _git_commit(),
    }
    with mlflow.start_run(run_name=result.config.policy.name) as run:
        mlflow.log_params(params)
        mlflow.set_tags(
            {
                "chunking_version": result.config.chunking_version,
                "config_sha256": result.config.config_sha256,
                "git_commit": params["git_commit"],
            }
        )
        mlflow.log_metrics(
            {name: float(value) for name, value in result.metrics.items()}
        )
        mlflow.log_artifacts(str(artifact_dir))
        return run.info.run_id


def _git_commit() -> str:
    """Return the current commit without making Git availability mandatory."""
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
