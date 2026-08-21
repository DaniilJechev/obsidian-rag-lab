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
from rag_based_on_obsidian.embeddings.mlflow_tracking import process_rss_mb
from rag_based_on_obsidian.eval.contracts import (
    DatasetMetrics,
    scored_metrics_for_log,
)

EVAL_EXPERIMENT_DESCRIPTION = (
    "Phase 7 retrieval evaluation: note-level binary IR metrics "
    "(nDCG, MRR, Precision, Recall, F1, Hit, MAP, R-Precision). "
    "run_kind=synthetic_harness is a fixture ranking smoke. "
    "run_kind=live is a corpus baseline against Qdrant (Sprint 18)."
)
ALLOWED_EVAL_RUN_KINDS = frozenset({"synthetic_harness", "live"})


def log_eval_harness_run(
    *,
    dataset_version: str,
    run_kind: str,
    metrics: DatasetMetrics,
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
    extra_tags: Mapping[str, object] | None = None,
    extra_metrics: Mapping[str, float] | None = None,
    artifact: Mapping[str, object] | None = None,
    run_name: str | None = None,
) -> str | None:
    """Log one eval harness run: synthetic fixture ranking or live retrieval."""
    if run_kind not in ALLOWED_EVAL_RUN_KINDS:
        allowed = ", ".join(sorted(ALLOWED_EVAL_RUN_KINDS))
        raise ValueError(f"run_kind must be one of: {allowed}")
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    _configure_eval_experiment()
    with mlflow.start_run(run_name=run_name or f"eval-{run_kind}") as run:
        params: dict[str, object] = {
            "dataset_version": dataset_version,
            "label_granularity": "note",
            "run_kind": run_kind,
            "question_count": metrics.question_count,
            "scored_count": metrics.scored_count,
            "skipped_count": metrics.skipped_count,
        }
        if metrics.k is not None:
            params["k"] = metrics.k
        if extra_params:
            params.update(extra_params)
        mlflow.log_params({key: str(value) for key, value in params.items()})
        tags: dict[str, str] = {
            "git_commit": _git_commit(),
            "phase": "7",
            "sprint": "18",
            "task": "EVAL-002",
            "experiment_type": "eval",
            "run_kind": run_kind,
        }
        if extra_tags:
            tags.update({key: str(value) for key, value in extra_tags.items()})
        mlflow.set_tags(tags)
        logged_metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "question_count": float(metrics.question_count),
            "scored_count": float(metrics.scored_count),
            "skipped_count": float(metrics.skipped_count),
        }
        if duration_seconds > 0 and metrics.question_count > 0:
            logged_metrics["questions_per_second"] = (
                metrics.question_count / duration_seconds
            )
        logged_metrics["ram_usage_mb"] = process_rss_mb()
        logged_metrics.update(scored_metrics_for_log(metrics))
        if extra_metrics:
            logged_metrics.update(extra_metrics)
        mlflow.log_metrics(logged_metrics)
        if artifact is not None:
            mlflow.log_dict(dict(artifact), "per_question.json")
        return run.info.run_id


def _configure_eval_experiment() -> None:
    """Create the eval experiment and keep experiment-level tags current."""
    experiment_tags = {
        "mlflow.note.content": EVAL_EXPERIMENT_DESCRIPTION,
        "phase": "7",
        "sprint": "18",
        "task": "EVAL-002",
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
