"""CLI for live RAGAS generation eval against POST /generate."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

from rag_based_on_obsidian.config import (
    DEFAULT_LLM_CONFIG_PATH,
    DEFAULT_RAGAS_CONFIG_PATH,
    ENV_FILE,
)
from rag_based_on_obsidian.eval.gold_yaml import load_gold_yaml
from rag_based_on_obsidian.eval.human_review import (
    load_human_sample_ids,
    write_human_review,
)
from rag_based_on_obsidian.eval.judge import JUDGE_SYSTEM
from rag_based_on_obsidian.eval.judge_factory import (
    build_generation_judge,
    judge_scale,
)
from rag_based_on_obsidian.eval.progress import (
    EvalProgress,
    configure_eval_logging,
    eval_tqdm,
)
from rag_based_on_obsidian.eval.ragas.ragas_mlflow import (
    log_ragas_run,
    mlflow_generate_run_name,
)
from rag_based_on_obsidian.eval.ragas.ragas_runner import (
    run_ragas_eval,
    select_gold_slice,
)
from rag_based_on_obsidian.eval.ragas.ragas_settings import (
    RagasRunConfig,
    load_ragas_config,
)
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError
from rag_based_on_obsidian.llm.packing import SYSTEM_PROMPT
from rag_based_on_obsidian.llm.settings import LLMConfig, load_llm_config


def build_parser() -> argparse.ArgumentParser:
    """Build the RAGAS live-eval command."""
    parser = argparse.ArgumentParser(
        prog="rag-cli ragas",
        description="Score generate answers via the HTTP API and a JSON or ragas judge.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_RAGAS_CONFIG_PATH,
    )
    run_parser.add_argument(
        "--llm-config",
        type=Path,
        default=DEFAULT_LLM_CONFIG_PATH,
    )
    run_parser.add_argument(
        "--generate-model",
        type=str,
        default=None,
        help=(
            "OpenRouter model id for POST /generate. "
            "Defaults to generate_model in ragas.yaml."
        ),
    )
    run_parser.add_argument(
        "--full-set",
        action="store_true",
        help="Score the whole gold file, ignoring YAML subset_size.",
    )
    run_parser.add_argument(
        "--log-mlflow",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one RAGAS CLI operation."""
    args = build_parser().parse_args(argv)
    if args.operation == "run":
        return asyncio.run(_run_live(args))
    print("error: ragas requires run", file=sys.stderr)
    return 2


async def _run_live(args: argparse.Namespace) -> int:
    configure_eval_logging()
    progress = EvalProgress()
    stages = eval_tqdm(total=7, desc="ragas run", unit="stage")

    def tick(name: str) -> None:
        stages.set_postfix_str(name)
        stages.update(1)

    try:
        load_dotenv(ENV_FILE)
        config = load_ragas_config(args.config)
        if args.full_set:
            config = replace(config, full_set=True)
        if args.generate_model is not None:
            override = args.generate_model.strip()
            if not override:
                print("error: --generate-model must not be empty", file=sys.stderr)
                return 2
            config = replace(config, generate_model=override)
        progress.mark(
            "load_config",
            name=config.name,
            full_set=config.full_set,
            generate_model=config.generate_model,
        )
        tick("load_config")
        gold_version, items = load_gold_yaml(config.gold_path)
        if gold_version != config.dataset_version:
            print(
                "error: gold dataset_version "
                f"{gold_version} != config {config.dataset_version}",
                file=sys.stderr,
            )
            return 2
        tick("load_gold")
        try:
            selected = select_gold_slice(items, config)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        progress.mark("select_slice", items=len(selected))
        tick("select_slice")
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        llm_config = _judge_llm_config(load_llm_config(args.llm_config), config)
        try:
            judge = build_generation_judge(config, llm_config, api_key)
        except LLMUnavailableError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        tick("init_judge")
        generate_model = config.generate_model
        started = perf_counter()
        summary, artifacts = await run_ragas_eval(
            selected,
            config,
            judge,
            progress=progress,
        )
        duration = perf_counter() - started
        tick("score")
        payload: dict[str, object] = {
            "dataset_version": config.dataset_version,
            "run_kind": "ragas_live",
            "config_name": config.name,
            "api_base_url": config.api_base_url,
            "method": config.method.value,
            "top_k": config.top_k,
            "subset_size": len(selected),
            "full_set": config.full_set,
            "concurrency": config.concurrency,
            "generate_model": generate_model,
            "judge_model": config.judge_model,
            "judge_backend": config.judge_backend,
            "judge_scale": judge_scale(config.judge_backend),
            "question_count": summary.question_count,
            "scored_count": summary.scored_count,
            "skipped_count": summary.skipped_count,
            "refused_count": summary.refused_count,
            "faithfulness": summary.faithfulness,
            "answer_relevancy": summary.answer_relevancy,
            "context_precision": summary.context_precision,
            "context_recall": summary.context_recall,
            "mean_latency_ms": summary.mean_latency_ms,
            "notes_processed": summary.notes_processed,
            "total_prompt_tokens": summary.total_prompt_tokens,
            "mean_prompt_tokens": summary.mean_prompt_tokens,
            "median_prompt_tokens": summary.median_prompt_tokens,
            "total_generated_tokens": summary.total_generated_tokens,
            "mean_generated_tokens": summary.mean_generated_tokens,
            "median_generated_tokens": summary.median_generated_tokens,
            "duration_seconds": duration,
        }
        if (
            config.human_sample_path is not None
            and config.human_review_path is not None
        ):
            try:
                sample_ids = load_human_sample_ids(config.human_sample_path)
                written = write_human_review(
                    config.human_review_path,
                    artifacts,
                    sample_ids,
                )
            except (OSError, TypeError, ValueError) as exc:
                print(f"error: human review pack: {exc}", file=sys.stderr)
                return 2
            payload["human_review_path"] = str(config.human_review_path)
            payload["human_review_count"] = written
        tick("human_review")
        if args.log_mlflow:
            prompts = _run_prompts(config.judge_backend)
            payload["mlflow_run_id"] = log_ragas_run(
                dataset_version=config.dataset_version,
                metrics=summary,
                duration_seconds=duration,
                extra_params={
                    "config_name": config.name,
                    "api_base_url": config.api_base_url,
                    "method": config.method.value,
                    "top_k": config.top_k,
                    "subset_size": len(selected),
                    "full_set": config.full_set,
                    "concurrency": config.concurrency,
                    "generate_model": generate_model,
                    "judge_model": config.judge_model,
                    "judge_backend": config.judge_backend,
                    "judge_scale": judge_scale(config.judge_backend),
                    "gold_path": str(config.gold_path),
                },
                extra_tags={
                    "generate_api": config.api_base_url,
                    "generate_model": generate_model,
                    "judge_model": config.judge_model,
                    "judge_backend": config.judge_backend,
                    "judge_scale": judge_scale(config.judge_backend),
                    "sprint": "23",
                    "task": "MLOPS-002",
                },
                artifact={"items": artifacts},
                prompts=prompts,
                run_name=mlflow_generate_run_name(generate_model),
            )
        tick("mlflow")
        progress.mark("done")
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    finally:
        stages.close()


def _judge_llm_config(llm_config: LLMConfig, config: RagasRunConfig) -> LLMConfig:
    """Pin the judge model from ragas.yaml without rewriting generate YAML."""
    if llm_config.model == config.judge_model:
        return llm_config
    return replace(llm_config, model=config.judge_model)


def _run_prompts(judge_backend: str) -> dict[str, str]:
    """Generate system prompt + evaluation prompts for MLflow artifacts."""
    prompts = {"generate_system": SYSTEM_PROMPT}
    if judge_backend == "json":
        prompts["evaluation_system"] = JUDGE_SYSTEM
        return prompts
    # Lazy import: keep JSON-only paths from loading ragas at CLI import time
    # when factory already loads it — still isolate dump helper.
    from rag_based_on_obsidian.eval.ragas.ragas_judge import dump_ragas_metric_prompts

    prompts["evaluation_system"] = dump_ragas_metric_prompts()
    return prompts