"""MLflow tracking for Phase 10 RAGAS generation eval runs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from statistics import pstdev
from typing import Any

import mlflow
from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    DEFAULT_MLFLOW_TRACKING_URI,
    ENV_FILE,
    RAGAS_EXPERIMENT_NAME,
)
from rag_based_on_obsidian.embeddings.mlflow_tracking import process_rss_mb
from rag_based_on_obsidian.eval.ragas.ragas_contracts import (
    SCORED_RAGAS_FIELDS,
    RagasDatasetMetrics,
)

RAGAS_EXPERIMENT_DESCRIPTION = (
    "Phase 10 generation evaluation: Faithfulness, Answer Relevancy, "
    "note-level Context Precision/Recall proxy, tokens and latency. "
    "Generate is measured via POST /generate. JSON judge stays integers 0–5 "
    "(human sample). Ragas framework metrics are native 0–1 and must not be "
    "rescaled into the JSON Likert."
)


def log_ragas_run(
    *,
    dataset_version: str,
    metrics: RagasDatasetMetrics,
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
    extra_tags: Mapping[str, object] | None = None,
    artifact: Mapping[str, object] | None = None,
    prompts: Mapping[str, str] | None = None,
    run_name: str | None = None,
) -> str | None:
    """Log one RAGAS harness run with Phase 10 experiment tags."""
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    _configure_ragas_experiment()
    with mlflow.start_run(run_name=run_name or "ragas-live") as run:
        params: dict[str, object] = {
            "dataset_version": dataset_version,
            "label_granularity": "note",
            "run_kind": "ragas_live",
            "question_count": metrics.question_count,
            "scored_count": metrics.scored_count,
            "skipped_count": metrics.skipped_count,
            "refused_count": metrics.refused_count,
            "notes_processed": metrics.notes_processed,
        }
        if extra_params:
            params.update(extra_params)
        if prompts:
            for name, text in prompts.items():
                params[f"prompt_{name}_sha256"] = _sha256_16(text)
        mlflow.log_params({key: str(value) for key, value in params.items()})
        tags: dict[str, str] = {
            "git_commit": _git_commit(),
            "phase": "10",
            "sprint": "23",
            "task": "MLOPS-002",
            "experiment_type": "ragas",
            "run_kind": "ragas_live",
        }
        if extra_tags:
            tags.update({key: str(value) for key, value in extra_tags.items()})
        mlflow.set_tags(tags)
        logged_metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "question_count": float(metrics.question_count),
            "scored_count": float(metrics.scored_count),
            "skipped_count": float(metrics.skipped_count),
            "refused_count": float(metrics.refused_count),
            "total_prompt_tokens": float(metrics.total_prompt_tokens),
            "total_generated_tokens": float(metrics.total_generated_tokens),
            "notes_processed": float(metrics.notes_processed),
            "ram_usage_mb": process_rss_mb(),
        }
        if duration_seconds > 0 and metrics.question_count > 0:
            logged_metrics["questions_per_second"] = (
                metrics.question_count / duration_seconds
            )
        if metrics.mean_latency_ms is not None:
            logged_metrics["mean_latency_ms"] = metrics.mean_latency_ms
        if metrics.mean_prompt_tokens is not None:
            logged_metrics["mean_prompt_tokens"] = metrics.mean_prompt_tokens
        if metrics.median_prompt_tokens is not None:
            logged_metrics["median_prompt_tokens"] = metrics.median_prompt_tokens
        if metrics.mean_generated_tokens is not None:
            logged_metrics["mean_generated_tokens"] = metrics.mean_generated_tokens
        if metrics.median_generated_tokens is not None:
            logged_metrics["median_generated_tokens"] = (
                metrics.median_generated_tokens
            )
        for field in SCORED_RAGAS_FIELDS:
            value = getattr(metrics, field)
            if value is not None:
                logged_metrics[field] = float(value)
                alias = _METRIC_ALIASES.get(field)
                if alias is not None:
                    logged_metrics[alias] = float(value)
        if metrics.question_count > 0:
            logged_metrics["scored_ratio"] = (
                metrics.scored_count / metrics.question_count
            )
        raw_items: list[Any] = []
        if artifact is not None:
            maybe_items = artifact.get("items")
            if isinstance(maybe_items, list):
                raw_items = maybe_items
                logged_metrics.update(_item_score_spread(raw_items))
        mlflow.log_metrics(logged_metrics)
        if artifact is not None:
            _log_utf8_json(dict(artifact), "per_question.json")
            if raw_items:
                _log_per_question_metrics(raw_items)
            failed = _failed_generation_rows(raw_items)
            if failed:
                _log_utf8_json({"items": failed}, "failed_generations.json")
        if prompts:
            for name, text in prompts.items():
                mlflow.log_text(text, f"prompts/{name}.txt")
        return run.info.run_id


def _log_utf8_json(payload: Mapping[str, Any], artifact_path: str) -> None:
    """Write JSON artifacts with literal Unicode (no ``\\uXXXX`` escapes)."""
    mlflow.log_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        artifact_path,
    )


def mlflow_generate_run_name(generate_model: str) -> str:
    """Stable MLflow run name: ragas-framework-sprint23-generate-<model>."""
    safe = (
        generate_model.strip()
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "-")
    )
    if not safe:
        safe = "unknown"
    return f"ragas-framework-sprint23-generate-{safe}"


def _failed_generation_rows(items: Sequence[Any]) -> list[dict[str, object]]:
    """Skipped / refused rows for a dedicated failure artifact."""
    failed: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        if not item.get("skipped") and not item.get("refused"):
            continue
        failed.append(
            {
                "item_id": item.get("item_id"),
                "question": item.get("question"),
                "skipped": item.get("skipped"),
                "refused": item.get("refused"),
                "skip_reason": item.get("skip_reason"),
                "raw_generation": item.get("raw_generation"),
                "answer": item.get("answer"),
                "model": item.get("model"),
                "latency_ms": item.get("latency_ms"),
                "prompt_tokens": item.get("prompt_tokens"),
                "generated_tokens": item.get("generated_tokens"),
            }
        )
    return failed


def _sha256_16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


_METRIC_ALIASES: dict[str, str] = {
    "faithfulness": "judge_faithfulness",
    "answer_relevancy": "judge_answer_relevancy",
    "context_precision": "proxy_context_precision",
    "context_recall": "proxy_context_recall",
}

_ITEM_METRIC_KEYS: tuple[tuple[str, str], ...] = (
    ("faithfulness", "item_faithfulness"),
    ("answer_relevancy", "item_answer_relevancy"),
    ("context_precision", "item_context_precision"),
    ("context_recall", "item_context_recall"),
)


def _item_score_spread(items: Sequence[Any]) -> dict[str, float]:
    """Stdev of per-question judge scores. Empty or single value → omit."""
    spread: dict[str, float] = {}
    for source, dest in (
        ("faithfulness", "stdev_faithfulness"),
        ("answer_relevancy", "stdev_answer_relevancy"),
    ):
        values = [
            float(item[source])
            for item in items
            if isinstance(item, dict)
            and isinstance(item.get(source), (int, float))
            and not isinstance(item.get(source), bool)
        ]
        if len(values) >= 2:
            spread[dest] = float(pstdev(values))
    return spread


def _log_per_question_metrics(items: Sequence[Any]) -> None:
    """One MLflow step per gold item so Compare can plot generation curves."""
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        point: dict[str, float] = {
            "item_skipped": 1.0 if item.get("skipped") else 0.0,
        }
        for source, dest in _ITEM_METRIC_KEYS:
            value = item.get(source)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            point[dest] = float(value)
        mlflow.log_metrics(point, step=index)


def _configure_ragas_experiment() -> None:
    """Create the RAGAS experiment and keep experiment-level tags current."""
    experiment_tags = {
        "mlflow.note.content": RAGAS_EXPERIMENT_DESCRIPTION,
        "phase": "10",
        "sprint": "23",
        "task": "MLOPS-002",
        "experiment_type": "ragas",
    }
    experiment = mlflow.get_experiment_by_name(RAGAS_EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(RAGAS_EXPERIMENT_NAME, tags=experiment_tags)
    mlflow.set_experiment(RAGAS_EXPERIMENT_NAME)
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
