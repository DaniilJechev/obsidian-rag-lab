"""MLflow tracking for Phase 7 retrieval evaluation harness runs."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping

import mlflow
from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    DEFAULT_MLFLOW_TRACKING_URI,
    ENV_FILE,
    EVAL_EXPERIMENT_NAME,
)
from rag_based_on_obsidian.eval.contracts import DatasetMetrics

EVAL_EXPERIMENT_DESCRIPTION = (
    "Phase 7 retrieval evaluation: note-level nDCG/MRR/Recall/Hit. "
    "Sprint 17 logs synthetic harness smoke only. Live dense/bm25/hybrid "
    "corpus baselines belong to Sprint 18 and must use run_kind=live."
)


def log_eval_harness_run(
    *,
    dataset_version: str,
    run_kind: str,
    metrics: DatasetMetrics,
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
) -> str | None:
    """Log one eval harness run. Synthetic smoke must not use run_kind=live."""
    if run_kind == "live":
        raise ValueError("Sprint 17 must not log live corpus baselines")
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    _configure_eval_experiment()
    with mlflow.start_run(run_name=f"eval-{run_kind}") as run:
        params: dict[str, object] = {
            "dataset_version": dataset_version,
            "label_granularity": "note",
            "run_kind": run_kind,
            "question_count": metrics.question_count,
            "scored_count": metrics.scored_count,
            "skipped_count": metrics.skipped_count,
        }
        if extra_params:
            params.update(extra_params)
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.set_tags(
            {
                "git_commit": _git_commit(),
                "phase": "7",
                "sprint": "17",
                "task": "EVAL-002",
                "experiment_type": "eval",
                "run_kind": run_kind,
            }
        )
        logged_metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "question_count": float(metrics.question_count),
            "scored_count": float(metrics.scored_count),
            "skipped_count": float(metrics.skipped_count),
        }
        for name in (
            "ndcg_at_5",
            "ndcg_at_10",
            "mrr_at_10",
            "recall_at_5",
            "recall_at_10",
            "hit_at_10",
        ):
            value = getattr(metrics, name)
            if value is not None:
                logged_metrics[name] = float(value)
        mlflow.log_metrics(logged_metrics)
        return run.info.run_id


def _configure_eval_experiment() -> None:
    """Create the eval experiment and keep experiment-level tags current."""
    experiment_tags = {
        "mlflow.note.content": EVAL_EXPERIMENT_DESCRIPTION,
        "phase": "7",
        "sprint": "17",
        "task": "EVAL-001",
        "experiment_type": "eval",
    }
    experiment = mlflow.get_experiment_by_name(EVAL_EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(EVAL_EXPERIMENT_NAME, tags=experiment_tags)
    mlflow.set_experiment(EVAL_EXPERIMENT_NAME)
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
