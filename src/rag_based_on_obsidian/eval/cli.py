"""CLI for gold loading, synthetic ranking evaluation and live retrieval eval."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from sqlalchemy import create_engine

from rag_based_on_obsidian.config import (
    DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    DEFAULT_CACHE_PARAPHRASE_PATH,
    DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    DEFAULT_EVAL_DATASET_VERSION,
    DEFAULT_EVAL_GOLD_PATH,
    DEFAULT_LLM_CONFIG_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
    DEFAULT_RETRIEVAL_CONFIG_PATH,
    DEFAULT_TOKEN_BUDGET_CONFIG_PATH,
    ENV_FILE,
    RERANK_EVAL_EXPERIMENT_NAME,
)
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.eval.cache.cache_mlflow import log_cache_eval_run
from rag_based_on_obsidian.eval.cache.cache_runner import run_cache_eval_sync
from rag_based_on_obsidian.eval.cache.cache_yaml import load_cache_paraphrase_yaml
from rag_based_on_obsidian.eval.contracts import scored_metrics_for_log
from rag_based_on_obsidian.eval.gold_slice import select_gold_slice
from rag_based_on_obsidian.eval.gold_yaml import load_gold_yaml
from rag_based_on_obsidian.eval.judge_factory import build_generation_judge
from rag_based_on_obsidian.eval.metrics import macro_average
from rag_based_on_obsidian.eval.mlflow_tracking import log_eval_harness_run
from rag_based_on_obsidian.eval.postgres_loader import (
    bind_live_gold_items,
    clear_eval_items,
    load_eval_items,
    load_note_path_index,
    resolve_note_ids,
    upsert_eval_items,
)
from rag_based_on_obsidian.eval.progress import EvalProgress, configure_eval_logging
from rag_based_on_obsidian.eval.retrieval.live_runner import run_live_eval
from rag_based_on_obsidian.eval.retrieval.live_session import (
    LiveSessionInfo,
    open_live_session,
)
from rag_based_on_obsidian.eval.retrieval.scoring import score_path_rankings
from rag_based_on_obsidian.eval.token_budget.budget_mlflow import log_budget_eval_run
from rag_based_on_obsidian.eval.token_budget.budget_runner import run_budget_eval_sync
from rag_based_on_obsidian.eval.token_budget.budget_yaml import load_budget_config
from rag_based_on_obsidian.llm.settings import load_llm_config
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.settings import load_retrieval_config


def build_parser() -> argparse.ArgumentParser:
    """Build gold load, ranking-score and live retrieval eval commands."""
    parser = argparse.ArgumentParser(
        prog="rag-cli eval",
        description="Load gold items, score rankings, or run live retrieval eval.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    load_parser = subparsers.add_parser("load-gold")
    load_parser.add_argument("--gold", type=Path, default=DEFAULT_EVAL_GOLD_PATH)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--gold", type=Path, default=DEFAULT_EVAL_GOLD_PATH)
    score_parser.add_argument("--rankings", type=Path, required=True)
    score_parser.add_argument("--top-k", type=int, required=True)
    score_parser.add_argument("--log-mlflow", action="store_true")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--method",
        required=True,
        choices=[method.value for method in RetrievalMethod],
    )
    run_parser.add_argument("--gold", type=Path, default=DEFAULT_EVAL_GOLD_PATH)
    run_parser.add_argument(
        "--dataset-version",
        default=DEFAULT_EVAL_DATASET_VERSION,
    )
    run_parser.add_argument(
        "--retrieval-config",
        type=Path,
        default=DEFAULT_RETRIEVAL_CONFIG_PATH,
    )
    run_parser.add_argument(
        "--qdrant-config",
        type=Path,
        default=DEFAULT_QDRANT_CONFIG_PATH,
    )
    run_parser.add_argument(
        "--batch-config",
        type=Path,
        default=DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    )
    run_parser.add_argument(
        "--model-config",
        type=Path,
        default=DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    )
    run_parser.add_argument("--top-k", type=int, required=True)
    run_parser.add_argument(
        "--candidate-k",
        type=int,
        default=None,
        help="Hybrid candidate pool. Default: 2 * --top-k.",
    )
    run_parser.add_argument(
        "--rrf-k",
        type=int,
        default=None,
        help="RRF constant k in 1/(rrf_k + rank). Default: retrieval.yaml rrf_k.",
    )
    run_parser.add_argument(
        "--log-mlflow",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    run_parser.add_argument(
        "--enable-rerank",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Apply cross-encoder after hybrid for this run "
            "(overrides YAML enabled; no Docker restart needed)."
        ),
    )
    cache_parser = subparsers.add_parser(
        "cache",
        help="Two-pass paraphrase eval for semantic cache hit rate and latency.",
    )
    cache_parser.add_argument(
        "--paraphrase-set",
        type=Path,
        default=DEFAULT_CACHE_PARAPHRASE_PATH,
    )
    cache_parser.add_argument(
        "--method",
        default=RetrievalMethod.HYBRID.value,
        choices=[method.value for method in RetrievalMethod],
    )
    cache_parser.add_argument("--top-k", type=int, default=5)
    cache_parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Running API base URL (POST /generate).",
    )
    cache_parser.add_argument(
        "--enable-cache",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Pass enable_cache=true/false on each POST /generate for this run "
            "(overrides configs/cache/cache.yaml without restarting the API)."
        ),
    )
    cache_parser.add_argument(
        "--log-mlflow",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    budget_parser = subparsers.add_parser(
        "budget",
        help="Token budget ablation on gold subset (800/1200/1800 by default).",
    )
    budget_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_TOKEN_BUDGET_CONFIG_PATH,
    )
    budget_parser.add_argument(
        "--budgets",
        default=None,
        help="Comma-separated override for YAML budgets, e.g. 800,1200,1800.",
    )
    budget_parser.add_argument(
        "--log-mlflow",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    budget_parser.add_argument(
        "--no-ragas",
        action="store_true",
        help="Skip RAGAS judge; record tokens and latency only.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one eval operation."""
    args = build_parser().parse_args(argv)
    if args.operation == "load-gold":
        return _load_gold(args.gold)
    if args.operation == "score":
        return _score_rankings(
            args.gold,
            args.rankings,
            args.top_k,
            args.log_mlflow,
        )
    if args.operation == "run":
        return _run_live(args)
    if args.operation == "cache":
        return _run_cache(args)
    if args.operation == "budget":
        return _run_budget(args)
    print("error: eval requires load-gold, score, run, cache or budget", file=sys.stderr)
    return 2


def _load_gold(gold_path: Path) -> int:
    configure_eval_logging()
    progress = EvalProgress()
    load_dotenv(ENV_FILE)
    progress.mark("load_env", gold=gold_path)
    dataset_version, items = load_gold_yaml(gold_path)
    progress.mark(
        "load_yaml",
        dataset_version=dataset_version,
        items=len(items),
    )
    engine = create_engine(load_database_url())
    progress.mark("connect_postgres")
    try:
        with engine.begin() as connection:
            path_index = load_note_path_index(connection, show_progress=True)
            progress.mark("load_note_path_index", notes=len(path_index))
            resolved = resolve_note_ids(items, path_index, show_progress=True)
            progress.mark("resolve_note_ids", questions=len(resolved))
            cleared = clear_eval_items(connection)
            progress.mark("clear_eval_items", cleared=cleared)
            written = upsert_eval_items(connection, items, resolved)
            progress.mark("upsert_eval_items", upserted=written)
    finally:
        engine.dispose()
    progress.mark("done")
    print(
        json.dumps(
            {
                "dataset_version": dataset_version,
                "items": len(items),
                "cleared": cleared,
                "upserted": written,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _score_rankings(
    gold_path: Path,
    rankings_path: Path,
    top_k: int,
    log_mlflow: bool,
) -> int:
    if top_k <= 0:
        print("error: --top-k must be positive", file=sys.stderr)
        return 2
    started = perf_counter()
    dataset_version, items = load_gold_yaml(gold_path)
    rankings = _load_rankings(rankings_path)
    results = score_path_rankings(items, rankings, k=top_k)
    summary = macro_average(results, k=top_k)
    duration = perf_counter() - started
    payload = {
        "dataset_version": dataset_version,
        "run_kind": "synthetic_harness",
        "k": top_k,
        "question_count": summary.question_count,
        "scored_count": summary.scored_count,
        "skipped_count": summary.skipped_count,
        "duration_seconds": duration,
    }
    payload.update(scored_metrics_for_log(summary))
    if log_mlflow:
        payload["mlflow_run_id"] = log_eval_harness_run(
            dataset_version=dataset_version,
            run_kind="synthetic_harness",
            metrics=summary,
            duration_seconds=duration,
            extra_params={"gold_path": str(gold_path), "k": top_k},
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _run_live(args: argparse.Namespace) -> int:
    load_dotenv(ENV_FILE)
    method = RetrievalMethod(args.method)
    top_k = args.top_k
    if top_k <= 0:
        print("error: --top-k must be positive", file=sys.stderr)
        return 2
    enable_rerank = bool(args.enable_rerank)
    if enable_rerank and method is not RetrievalMethod.HYBRID:
        print(
            "error: --enable-rerank requires --method hybrid",
            file=sys.stderr,
        )
        return 2
    gold_version, yaml_items = load_gold_yaml(args.gold)
    dataset_version = args.dataset_version or gold_version
    retrieval_config = load_retrieval_config(args.retrieval_config)
    candidate_k = (2 * top_k) if args.candidate_k is None else args.candidate_k
    if candidate_k < top_k:
        print("error: --candidate-k must be >= --top-k", file=sys.stderr)
        return 2
    rrf_k = retrieval_config.rrf_k if args.rrf_k is None else args.rrf_k
    if rrf_k <= 0:
        print("error: --rrf-k must be positive", file=sys.stderr)
        return 2
    retrieval_config = replace(
        retrieval_config,
        top_k=top_k,
        candidate_k=candidate_k,
        rrf_k=rrf_k,
    )
    engine = create_engine(load_database_url())
    try:
        with engine.begin() as connection:
            stored = load_eval_items(connection, dataset_version)
            path_index = load_note_path_index(connection)
            items = bind_live_gold_items(stored, path_index, yaml_items)
    finally:
        engine.dispose()
    if not items:
        print(
            "error: no eval_items for dataset_version "
            f"{dataset_version}; run rag-cli eval load-gold first",
            file=sys.stderr,
        )
        return 2
    started = perf_counter()
    with open_live_session(
        method=method,
        retrieval_config=retrieval_config,
        model_config_path=args.model_config,
        batch_config_path=args.batch_config,
        qdrant_config_path=args.qdrant_config,
        top_k=top_k,
        candidate_k=candidate_k,
        rrf_k=rrf_k,
        enable_rerank=enable_rerank,
    ) as session:
        results, artifacts = run_live_eval(items, session.search, k=top_k)
        info = session.info
    duration = perf_counter() - started
    summary = macro_average(results, k=top_k)
    rerank_label = "enable_rerank" if enable_rerank else "disable_rerank"
    payload: dict[str, object] = {
        "dataset_version": dataset_version,
        "run_kind": "live",
        "retrieval_method": method.value,
        "collection_name": info.collection_name,
        "chunking_version": info.chunking_version,
        "k": top_k,
        "top_k": info.top_k,
        "candidate_k": info.candidate_k,
        "rrf_k": info.rrf_k,
        "enable_rerank": enable_rerank,
        "rerank_label": rerank_label,
        "question_count": summary.question_count,
        "scored_count": summary.scored_count,
        "skipped_count": summary.skipped_count,
        "duration_seconds": duration,
    }
    payload.update(scored_metrics_for_log(summary))
    if args.log_mlflow:
        experiment_name = None
        run_name = f"eval-live-{method.value}"
        if method is RetrievalMethod.HYBRID:
            experiment_name = RERANK_EVAL_EXPERIMENT_NAME
            run_name = f"eval-live-hybrid-{rerank_label}"
        payload["mlflow_run_id"] = log_eval_harness_run(
            dataset_version=dataset_version,
            run_kind="live",
            metrics=summary,
            duration_seconds=duration,
            extra_params=_live_params(
                info,
                gold_path=args.gold,
                k=top_k,
                enable_rerank=enable_rerank,
            ),
            extra_metrics={"rrf_k": float(info.rrf_k)},
            extra_tags={
                "retrieval_method": method.value,
                "collection_name": info.collection_name,
                "rerank_label": rerank_label,
                "enable_rerank": str(enable_rerank).lower(),
            },
            artifact={"items": artifacts},
            run_name=run_name,
            experiment_name=experiment_name,
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _run_cache(args: argparse.Namespace) -> int:
    load_dotenv(ENV_FILE)
    top_k = args.top_k
    if top_k <= 0:
        print("error: --top-k must be positive", file=sys.stderr)
        return 2
    method = RetrievalMethod(args.method)
    enable_cache = bool(args.enable_cache)
    dataset_version, groups = load_cache_paraphrase_yaml(args.paraphrase_set)
    started = perf_counter()
    rows, summary = run_cache_eval_sync(
        groups,
        dataset_version=dataset_version,
        base_url=args.api_base_url.rstrip("/"),
        method=method,
        top_k=top_k,
        enable_cache=enable_cache,
    )
    duration = perf_counter() - started
    label = "semantic-cache-on" if enable_cache else "semantic-cache-off"
    payload: dict[str, object] = {
        "dataset_version": dataset_version,
        "run_kind": "cache_paraphrase",
        "cache_label": label,
        "cache_enabled": enable_cache,
        "retrieval_method": method.value,
        "top_k": top_k,
        "group_count": summary.group_count,
        "canonical_count": summary.canonical_count,
        "paraphrase_count": summary.paraphrase_count,
        "paraphrase_hits": summary.paraphrase_hits,
        "hit_rate": summary.hit_rate,
        "latency_p50_ms": summary.latency_p50_ms,
        "latency_p95_ms": summary.latency_p95_ms,
        "canonical_latency_p50_ms": summary.canonical_latency_p50_ms,
        "pass1_tokens": summary.pass1_tokens,
        "pass2_tokens": summary.pass2_tokens,
        "tokens_saved": summary.tokens_saved,
        "avg_latency_ms": summary.avg_latency_ms,
        "canonical_avg_latency_ms": summary.canonical_avg_latency_ms,
        "paraphrase_avg_latency_ms": summary.paraphrase_avg_latency_ms,
        "paraphrase_hit_avg_latency_ms": summary.paraphrase_hit_avg_latency_ms,
        "paraphrase_miss_avg_latency_ms": summary.paraphrase_miss_avg_latency_ms,
        "duration_seconds": duration,
    }
    if args.log_mlflow:
        payload["mlflow_run_id"] = log_cache_eval_run(
            dataset_version=dataset_version,
            summary=summary,
            rows=rows,
            duration_seconds=duration,
            enable_cache=enable_cache,
            extra_params={
                "paraphrase_set": str(args.paraphrase_set),
                "api_base_url": args.api_base_url.rstrip("/"),
                "retrieval_method": method.value,
                "top_k": top_k,
            },
            run_name=label,
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _run_budget(args: argparse.Namespace) -> int:
    import os

    from rag_based_on_obsidian.llm.contracts import LLMUnavailableError

    load_dotenv(ENV_FILE)
    config = load_budget_config(args.config)
    budgets_override = _parse_budgets_arg(args.budgets)
    budgets = budgets_override or config.budgets
    ragas_enabled = config.ragas_enabled and not args.no_ragas
    gold_version, all_items = load_gold_yaml(config.gold_path)
    dataset_version = config.dataset_version or gold_version
    items = select_gold_slice(
        all_items,
        subset_size=config.subset_size,
        full_set=config.full_set,
    )
    llm_config = load_llm_config(DEFAULT_LLM_CONFIG_PATH)
    llm_config = replace(llm_config, model=config.generate_model)
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    judge = None
    if ragas_enabled:
        if not api_key:
            print("error: OPENROUTER_API_KEY is required for RAGAS judge", file=sys.stderr)
            return 2
        judge = build_generation_judge(config, llm_config, api_key)
    started = perf_counter()
    try:
        results = run_budget_eval_sync(
            items,
            config,
            budgets=budgets,
            judge=judge,
            ragas_enabled=ragas_enabled,
        )
    except LLMUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    duration = perf_counter() - started
    comparison: list[dict[str, object]] = []
    mlflow_runs: dict[int, str | None] = {}
    for budget in budgets:
        rows, summary = results[budget]
        comparison.append(
            {
                "budget": budget,
                "mean_prompt_tokens": summary.mean_prompt_tokens,
                "mean_faithfulness": summary.mean_faithfulness,
                "mean_answer_relevancy": summary.mean_answer_relevancy,
                "mean_latency_ms": summary.mean_latency_ms,
                "refusal_rate": summary.refusal_rate,
            }
        )
        if args.log_mlflow:
            mlflow_runs[budget] = log_budget_eval_run(
                dataset_version=dataset_version,
                summary=summary,
                rows=rows,
                duration_seconds=duration / len(budgets),
                experiment_name=config.experiment_name,
                extra_params={
                    "config_path": str(args.config),
                    "api_base_url": config.api_base_url,
                    "retrieval_method": config.method.value,
                    "top_k": config.top_k,
                    "subset_size": config.subset_size,
                    "ragas_enabled": ragas_enabled,
                    "generate_model": config.generate_model,
                    "judge_model": config.judge_model,
                    "judge_backend": config.judge_backend,
                },
                run_name=f"budget-{budget}",
            )
    payload: dict[str, object] = {
        "dataset_version": dataset_version,
        "run_kind": "token_budget",
        "budgets": list(budgets),
        "question_count": len(items),
        "ragas_enabled": ragas_enabled,
        "duration_seconds": duration,
        "comparison": comparison,
    }
    if args.log_mlflow:
        payload["mlflow_run_ids"] = mlflow_runs
    print(json.dumps(payload, ensure_ascii=False))
    _print_budget_table(comparison)
    return 0


def _parse_budgets_arg(raw: str | None) -> tuple[int, ...] | None:
    if raw is None or not raw.strip():
        return None
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise ValueError("each budget must be positive")
        values.append(value)
    if not values:
        return None
    return tuple(values)


def _print_budget_table(rows: list[dict[str, object]]) -> None:
    header = (
        f"{'budget':>8}  {'prompt_tok':>10}  {'faithful':>9}  "
        f"{'relevancy':>9}  {'latency_ms':>10}  {'refusal':>8}"
    )
    print(header, file=sys.stderr)
    for row in rows:
        print(
            f"{row['budget']:>8}  "
            f"{_fmt(row.get('mean_prompt_tokens')):>10}  "
            f"{_fmt(row.get('mean_faithfulness')):>9}  "
            f"{_fmt(row.get('mean_answer_relevancy')):>9}  "
            f"{_fmt(row.get('mean_latency_ms')):>10}  "
            f"{_fmt(row.get('refusal_rate')):>8}",
            file=sys.stderr,
        )


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _live_params(
    info: LiveSessionInfo,
    *,
    gold_path: Path,
    k: int,
    enable_rerank: bool,
) -> dict[str, object]:
    params: dict[str, object] = {
        "k": k,
        "retrieval_method": info.method.value,
        "collection_name": info.collection_name,
        "chunking_version": info.chunking_version,
        "top_k": info.top_k,
        "candidate_k": info.candidate_k,
        "rrf_k": info.rrf_k,
        "model_name": info.model_name,
        "model_revision": info.model_revision,
        "device": info.device,
        "dimension": info.dimension,
        "normalized": info.normalized,
        "max_length": info.max_length,
        "batch_size": info.batch_size,
        "gold_path": str(gold_path),
        "enable_rerank": enable_rerank,
        "rerank_label": "enable_rerank" if enable_rerank else "disable_rerank",
    }
    if info.rerank_model_name is not None:
        params["rerank_model_name"] = info.rerank_model_name
    if info.rerank_max_length is not None:
        params["rerank_max_length"] = info.rerank_max_length
    if info.rerank_batch_size is not None:
        params["rerank_batch_size"] = info.rerank_batch_size
    return params


def _load_rankings(path: Path) -> dict[str, tuple[str, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(raw_items, list):
        raise TypeError("rankings JSON must contain an items list")
    rankings: dict[str, tuple[str, ...]] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise TypeError("each ranking item must be a mapping")
        item_id = raw_item.get("id")
        ranked_paths = raw_item.get("ranked_paths")
        if not isinstance(item_id, str) or not item_id:
            raise ValueError("ranking item id must be a non-empty string")
        if not isinstance(ranked_paths, list):
            raise TypeError(f"{item_id} ranked_paths must be a list")
        rankings[item_id] = tuple(str(path) for path in ranked_paths)
    return rankings
