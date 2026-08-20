"""CLI for gold loading and synthetic ranking evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from sqlalchemy import create_engine

from rag_based_on_obsidian.config import DEFAULT_EVAL_GOLD_PATH, ENV_FILE
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.eval.gold_yaml import load_gold_yaml
from rag_based_on_obsidian.eval.metrics import macro_average
from rag_based_on_obsidian.eval.mlflow_tracking import log_eval_harness_run
from rag_based_on_obsidian.eval.postgres_loader import (
    load_note_path_index,
    resolve_note_ids,
    upsert_eval_items,
)
from rag_based_on_obsidian.eval.scoring import score_path_rankings


def build_parser() -> argparse.ArgumentParser:
    """Build gold load and ranking-score commands."""
    parser = argparse.ArgumentParser(
        prog="rag-cli eval",
        description="Load gold items and score explicit note rankings.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    load_parser = subparsers.add_parser("load-gold")
    load_parser.add_argument("--gold", type=Path, default=DEFAULT_EVAL_GOLD_PATH)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("--gold", type=Path, default=DEFAULT_EVAL_GOLD_PATH)
    score_parser.add_argument("--rankings", type=Path, required=True)
    score_parser.add_argument("--log-mlflow", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one eval operation."""
    args = build_parser().parse_args(argv)
    if args.operation == "load-gold":
        return _load_gold(args.gold)
    if args.operation == "score":
        return _score_rankings(args.gold, args.rankings, args.log_mlflow)
    print("error: eval requires load-gold or score", file=sys.stderr)
    return 2


def _load_gold(gold_path: Path) -> int:
    load_dotenv(ENV_FILE)
    dataset_version, items = load_gold_yaml(gold_path)
    engine = create_engine(load_database_url())
    try:
        with engine.begin() as connection:
            path_index = load_note_path_index(connection)
            resolved = resolve_note_ids(items, path_index)
            written = upsert_eval_items(connection, items, resolved)
    finally:
        engine.dispose()
    print(
        json.dumps(
            {
                "dataset_version": dataset_version,
                "items": len(items),
                "upserted": written,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _score_rankings(gold_path: Path, rankings_path: Path, log_mlflow: bool) -> int:
    started = perf_counter()
    dataset_version, items = load_gold_yaml(gold_path)
    rankings = _load_rankings(rankings_path)
    results = score_path_rankings(items, rankings)
    summary = macro_average(results)
    duration = perf_counter() - started
    payload = {
        "dataset_version": dataset_version,
        "run_kind": "synthetic_harness",
        "question_count": summary.question_count,
        "scored_count": summary.scored_count,
        "skipped_count": summary.skipped_count,
        "ndcg_at_5": summary.ndcg_at_5,
        "ndcg_at_10": summary.ndcg_at_10,
        "mrr_at_10": summary.mrr_at_10,
        "recall_at_5": summary.recall_at_5,
        "recall_at_10": summary.recall_at_10,
        "hit_at_10": summary.hit_at_10,
        "duration_seconds": duration,
    }
    if log_mlflow:
        payload["mlflow_run_id"] = log_eval_harness_run(
            dataset_version=dataset_version,
            run_kind="synthetic_harness",
            metrics=summary,
            duration_seconds=duration,
            extra_params={"gold_path": str(gold_path)},
        )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


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
