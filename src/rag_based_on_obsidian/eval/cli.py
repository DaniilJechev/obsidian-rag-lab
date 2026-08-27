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
    DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    DEFAULT_EVAL_DATASET_VERSION,
    DEFAULT_EVAL_GOLD_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
    DEFAULT_RETRIEVAL_CONFIG_PATH,
    ENV_FILE,
    RERANK_EVAL_EXPERIMENT_NAME,
)
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.eval.contracts import scored_metrics_for_log
from rag_based_on_obsidian.eval.gold_yaml import load_gold_yaml
from rag_based_on_obsidian.eval.live_runner import run_live_eval
from rag_based_on_obsidian.eval.live_session import LiveSessionInfo, open_live_session
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
from rag_based_on_obsidian.eval.scoring import score_path_rankings
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
    print("error: eval requires load-gold, score or run", file=sys.stderr)
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
