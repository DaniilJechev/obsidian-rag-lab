"""MLflow tracking for Phase 13 token budget eval."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence

import mlflow
from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    DEFAULT_MLFLOW_TRACKING_URI,
    ENV_FILE,
    TOKEN_BUDGET_EVAL_EXPERIMENT_NAME,
)
from rag_based_on_obsidian.embeddings.mlflow_tracking import process_rss_mb
from rag_based_on_obsidian.eval.token_budget.budget_runner import (
    BudgetEvalSummary,
    BudgetQueryResult,
)
from rag_based_on_obsidian.pipeline_versions import PROMPT_VERSION

TOKEN_BUDGET_EXPERIMENT_DESCRIPTION = (
    "Phase 13 Sprint 29: max_context_tokens ablation (800/1200/1800) on gold "
    "subset with cache disabled. One MLflow run per budget. Metrics: prompt "
    "tokens, latency, packed chunks, nDCG@k, MRR@k, RAGAS faithfulness and "
    "answer relevancy. Artifacts: summary.json and per_query.json."
)


def build_budget_eval_artifacts(
    *,
    dataset_version: str,
    summary: BudgetEvalSummary,
    rows: Sequence[BudgetQueryResult],
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build summary + per-query payloads for MLflow artifacts."""
    per_query = [query_record(row, index=index) for index, row in enumerate(rows, start=1)]
    summary_payload: dict[str, object] = {
        "dataset_version": dataset_version,
        "budget": summary.budget,
        "duration_seconds": duration_seconds,
        "question_count": summary.question_count,
        "scored_count": summary.scored_count,
        "skipped_count": summary.skipped_count,
        "refused_count": summary.refused_count,
        "refusal_rate": summary.refusal_rate,
        "mean_prompt_tokens": summary.mean_prompt_tokens,
        "median_prompt_tokens": summary.median_prompt_tokens,
        "p95_prompt_tokens": summary.p95_prompt_tokens,
        "mean_generated_tokens": summary.mean_generated_tokens,
        "mean_latency_ms": summary.mean_latency_ms,
        "p50_latency_ms": summary.p50_latency_ms,
        "p95_latency_ms": summary.p95_latency_ms,
        "mean_packed_chunks": summary.mean_packed_chunks,
        "mean_est_tokens": summary.mean_est_tokens,
        "mean_ndcg_at_k": summary.mean_ndcg_at_k,
        "mean_mrr_at_k": summary.mean_mrr_at_k,
        "mean_faithfulness": summary.mean_faithfulness,
        "mean_answer_relevancy": summary.mean_answer_relevancy,
    }
    if extra_params:
        summary_payload["run_params"] = dict(extra_params)
    return {"summary": summary_payload, "per_query": per_query}


def query_record(row: BudgetQueryResult, *, index: int) -> dict[str, object]:
    """Serialize one budget eval row for artifacts."""
    return {
        "index": index,
        "item_id": row.item_id,
        "budget": row.budget,
        "query": row.query,
        "prompt_tokens": row.prompt_tokens,
        "generated_tokens": row.generated_tokens,
        "latency_ms": row.latency_ms,
        "packed_chunks": row.packed_chunks,
        "est_tokens": row.est_tokens,
        "gate_trace": row.gate_trace,
        "refused": row.refused,
        "refusal_reason": row.refusal_reason,
        "model": row.model,
        "answer": row.answer,
        "packed_note_paths": list(row.packed_note_paths),
        "ndcg_at_k": row.ndcg_at_k,
        "mrr_at_k": row.mrr_at_k,
        "faithfulness": row.faithfulness,
        "answer_relevancy": row.answer_relevancy,
        "skipped": row.skipped,
        "skip_reason": row.skip_reason,
    }


def log_budget_eval_run(
    *,
    dataset_version: str,
    summary: BudgetEvalSummary,
    rows: Sequence[BudgetQueryResult],
    duration_seconds: float,
    extra_params: Mapping[str, object] | None = None,
    experiment_name: str | None = None,
    run_name: str | None = None,
) -> str | None:
    """Log one budget ablation run with metrics and artifacts."""
    load_dotenv(ENV_FILE)
    tracking_uri = os.environ.get(
        "MLFLOW_TRACKING_URI",
        DEFAULT_MLFLOW_TRACKING_URI,
    )
    mlflow.set_tracking_uri(tracking_uri)
    target_experiment = experiment_name or TOKEN_BUDGET_EVAL_EXPERIMENT_NAME
    _configure_budget_eval_experiment(target_experiment)
    artifacts = build_budget_eval_artifacts(
        dataset_version=dataset_version,
        summary=summary,
        rows=rows,
        duration_seconds=duration_seconds,
        extra_params=extra_params,
    )
    label = run_name or f"budget-{summary.budget}"
    with mlflow.start_run(run_name=label) as run:
        params: dict[str, object] = {
            "dataset_version": dataset_version,
            "run_kind": "token_budget",
            "max_context_tokens": summary.budget,
            "prompt_version": PROMPT_VERSION,
            "cache_enabled": False,
            "question_count": summary.question_count,
        }
        if extra_params:
            params.update(extra_params)
        mlflow.log_params({key: str(value) for key, value in params.items()})
        mlflow.set_tags(
            {
                "git_commit": _git_commit(),
                "experiment_type": "token_budget_eval",
                "phase": "13",
                "sprint": "29",
                "task": "CACHE-002",
                "run_kind": "token_budget",
                "max_context_tokens": str(summary.budget),
            }
        )
        metrics: dict[str, float] = {
            "duration_seconds": duration_seconds,
            "max_context_tokens": float(summary.budget),
            "question_count": float(summary.question_count),
            "scored_count": float(summary.scored_count),
            "skipped_count": float(summary.skipped_count),
            "refused_count": float(summary.refused_count),
            "refusal_rate": summary.refusal_rate,
            "ram_usage_mb": process_rss_mb(),
        }
        _maybe_log(metrics, "mean_prompt_tokens", summary.mean_prompt_tokens)
        _maybe_log(metrics, "median_prompt_tokens", summary.median_prompt_tokens)
        _maybe_log(metrics, "p95_prompt_tokens", summary.p95_prompt_tokens)
        _maybe_log(metrics, "mean_generated_tokens", summary.mean_generated_tokens)
        _maybe_log(metrics, "mean_latency_ms", summary.mean_latency_ms)
        _maybe_log(metrics, "p50_latency_ms", summary.p50_latency_ms)
        _maybe_log(metrics, "p95_latency_ms", summary.p95_latency_ms)
        _maybe_log(metrics, "mean_packed_chunks", summary.mean_packed_chunks)
        _maybe_log(metrics, "mean_est_tokens", summary.mean_est_tokens)
        _maybe_log(metrics, "ndcg_at_5", summary.mean_ndcg_at_k)
        _maybe_log(metrics, "mrr_at_5", summary.mean_mrr_at_k)
        _maybe_log(metrics, "faithfulness", summary.mean_faithfulness)
        _maybe_log(metrics, "answer_relevancy", summary.mean_answer_relevancy)
        mlflow.log_metrics(metrics)
        _log_utf8_json(dict(artifacts["summary"]), "summary.json")
        _log_utf8_json({"items": artifacts["per_query"]}, "per_query.json")
        return run.info.run_id


def _maybe_log(metrics: dict[str, float], key: str, value: float | None) -> None:
    if value is not None:
        metrics[key] = float(value)


def _log_utf8_json(payload: Mapping[str, object], artifact_path: str) -> None:
    mlflow.log_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        artifact_path,
    )


def _configure_budget_eval_experiment(name: str) -> None:
    experiment_tags = {
        "mlflow.note.content": TOKEN_BUDGET_EXPERIMENT_DESCRIPTION,
        "phase": "13",
        "sprint": "29",
        "task": "CACHE-002",
        "experiment_type": "token_budget_eval",
    }
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is None:
        mlflow.create_experiment(name, tags=dict(experiment_tags))
    mlflow.set_experiment(name)
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


def _metric_token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    return token.strip("_") or "query"
