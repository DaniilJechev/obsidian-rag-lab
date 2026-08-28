"""MLflow tracking for Phase 13 semantic cache eval."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence

import mlflow
from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    CACHE_EVAL_EXPERIMENT_NAME,
    DEFAULT_MLFLOW_TRACKING_URI,
    ENV_FILE,
)
from rag_based_on_obsidian.embeddings.mlflow_tracking import process_rss_mb
from rag_based_on_obsidian.eval.cache_runner import CacheEvalSummary, CacheQueryResult

CACHE_EVAL_EXPERIMENT_DESCRIPTION = (
    "Phase 13 Sprint 28: semantic cache on vs off on paraphrase eval set. "
    "Pass 1 runs canonical queries; pass 2 runs paraphrases. "
    "Run metrics: hit_rate, avg latency by pass, per-query cache_hit and "
    "latency_ms. Artifacts: summary.json and per_query.json."
)

_PASS_SUFFIX = {"canonical": "canonical", "paraphrase": "paraphrase"}


def build_cache_eval_artifacts(
    *,
    dataset_version: str,
    summary: CacheEvalSummary,
    rows: Sequence[CacheQueryResult],
    enable_cache: bool,
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build summary + per-query payloads for MLflow artifacts."""
    per_query = [query_record(row, index=index) for index, row in enumerate(rows, start=1)]
    summary_payload: dict[str, object] = {
        "dataset_version": dataset_version,
        "cache_enabled": enable_cache,
        "duration_seconds": duration_seconds,
        "group_count": summary.group_count,
        "canonical_count": summary.canonical_count,
        "paraphrase_count": summary.paraphrase_count,
        "paraphrase_hits": summary.paraphrase_hits,
        "hit_rate": summary.hit_rate,
        "avg_latency_ms": summary.avg_latency_ms,
        "canonical_avg_latency_ms": summary.canonical_avg_latency_ms,
        "paraphrase_avg_latency_ms": summary.paraphrase_avg_latency_ms,
        "paraphrase_hit_avg_latency_ms": summary.paraphrase_hit_avg_latency_ms,
        "paraphrase_miss_avg_latency_ms": summary.paraphrase_miss_avg_latency_ms,
        "latency_p50_ms": summary.latency_p50_ms,
        "latency_p95_ms": summary.latency_p95_ms,
        "canonical_latency_p50_ms": summary.canonical_latency_p50_ms,
        "pass1_tokens": summary.pass1_tokens,
        "pass2_tokens": summary.pass2_tokens,
        "tokens_saved": summary.tokens_saved,
    }
    if extra_params:
        summary_payload["run_params"] = dict(extra_params)
    return {
        "summary": summary_payload,
        "per_query": per_query,
    }


def query_record(row: CacheQueryResult, *, index: int) -> dict[str, object]:
    """Serialize one eval query row for artifacts and inspection."""
    total_tokens = None
    if row.prompt_tokens is not None or row.generated_tokens is not None:
        total_tokens = int(row.prompt_tokens or 0) + int(row.generated_tokens or 0)
    return {
        "index": index,
        "group_id": row.group_id,
        "pass": row.pass_name,
        "query": row.query,
        "cache_hit": row.cache_hit,
        "cache_similarity": row.cache_similarity,
        "cache_matched_query": row.cache_matched_query,
        "latency_ms": row.latency_ms,
        "avg_latency_ms": float(row.latency_ms) if row.latency_ms is not None else None,
        "prompt_tokens": row.prompt_tokens,
        "generated_tokens": row.generated_tokens,
        "total_tokens": total_tokens,
        "refused": row.refused,
        "refusal_reason": row.refusal_reason,
        "model": row.model,
        "answer": row.answer,
    }


def per_query_mlflow_metrics(rows: Sequence[CacheQueryResult]) -> dict[str, float]:
    """One cache_hit (0/1) and latency_ms metric per query for MLflow Compare."""
    metrics: dict[str, float] = {}
    for row in rows:
        suffix = _PASS_SUFFIX.get(row.pass_name, row.pass_name)
        prefix = f"q_{_metric_token(row.group_id)}_{suffix}"
        metrics[f"{prefix}_cache_hit"] = 1.0 if row.cache_hit else 0.0
        metrics[f"{prefix}_latency_ms"] = (
            float(row.latency_ms) if row.latency_ms is not None else 0.0
        )
        if row.cache_similarity is not None:
            metrics[f"{prefix}_cache_similarity"] = float(row.cache_similarity)
    return metrics


def log_cache_eval_run(
    *,
    dataset_version: str,
    summary: CacheEvalSummary,
    rows: Sequence[CacheQueryResult],
    duration_seconds: float,
    enable_cache: bool,
    extra_params: Mapping[str, object] | None = None,
    run_name: str | None = None,
) -> str | None:
    """Log one semantic cache eval run with per-query metrics and artifacts."""
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    _configure_cache_eval_experiment()
    label = "semantic-cache-on" if enable_cache else "semantic-cache-off"
    artifacts = build_cache_eval_artifacts(
        dataset_version=dataset_version,
        summary=summary,
        rows=rows,
        enable_cache=enable_cache,
        duration_seconds=duration_seconds,
        extra_params=extra_params,
    )
    with mlflow.start_run(run_name=run_name or label) as run:
        params: dict[str, object] = {
            "dataset_version": dataset_version,
            "run_kind": "cache_paraphrase",
            "cache_enabled": enable_cache,
            "group_count": summary.group_count,
            "canonical_count": summary.canonical_count,
            "paraphrase_count": summary.paraphrase_count,
        }
        if extra_params:
            params.update(extra_params)
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.set_tags(
            {
                "git_commit": _git_commit(),
                "experiment_type": "cache_eval",
                "phase": "13",
                "sprint": "28",
                "task": "CACHE-001",
                "run_kind": "cache_paraphrase",
                "cache_label": label,
                "cache_enabled": str(enable_cache).lower(),
            }
        )
        metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "group_count": float(summary.group_count),
            "canonical_count": float(summary.canonical_count),
            "paraphrase_count": float(summary.paraphrase_count),
            "paraphrase_hits": float(summary.paraphrase_hits),
            "hit_rate": summary.hit_rate,
            "avg_latency_ms": summary.avg_latency_ms,
            "canonical_avg_latency_ms": summary.canonical_avg_latency_ms,
            "paraphrase_avg_latency_ms": summary.paraphrase_avg_latency_ms,
            "paraphrase_hit_avg_latency_ms": summary.paraphrase_hit_avg_latency_ms,
            "paraphrase_miss_avg_latency_ms": summary.paraphrase_miss_avg_latency_ms,
            "latency_p50_ms": summary.latency_p50_ms,
            "latency_p95_ms": summary.latency_p95_ms,
            "canonical_latency_p50_ms": summary.canonical_latency_p50_ms,
            "pass1_tokens": float(summary.pass1_tokens),
            "pass2_tokens": float(summary.pass2_tokens),
            "tokens_saved": float(summary.tokens_saved),
            "ram_usage_mb": process_rss_mb(),
        }
        metrics.update(per_query_mlflow_metrics(rows))
        mlflow.log_metrics(metrics)
        _log_utf8_json(dict(artifacts["summary"]), "summary.json")
        _log_utf8_json({"items": artifacts["per_query"]}, "per_query.json")
        return run.info.run_id


def _metric_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    return token.strip("_") or "query"


def _log_utf8_json(payload: Mapping[str, object], artifact_path: str) -> None:
    mlflow.log_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        artifact_path,
    )


def _configure_cache_eval_experiment() -> None:
    experiment_tags = {
        "mlflow.note.content": CACHE_EVAL_EXPERIMENT_DESCRIPTION,
        "phase": "13",
        "sprint": "28",
        "task": "CACHE-001",
        "experiment_type": "cache_eval",
    }
    experiment = mlflow.get_experiment_by_name(CACHE_EVAL_EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(CACHE_EVAL_EXPERIMENT_NAME, tags=dict(experiment_tags))
    mlflow.set_experiment(CACHE_EVAL_EXPERIMENT_NAME)
    for key, value in experiment_tags.items():
        mlflow.set_experiment_tag(key, value)


def _git_commit() -> str:
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
