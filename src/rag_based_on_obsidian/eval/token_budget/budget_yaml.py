"""Load Sprint 29 token budget eval YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag_based_on_obsidian.config import PROJECT_ROOT
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


class BudgetYamlError(ValueError):
    """Raised when the budget eval YAML is invalid."""


@dataclass(frozen=True)
class BudgetRunConfig:
    """One token budget ablation run over a gold subset."""

    name: str
    gold_path: Path
    dataset_version: str
    subset_size: int
    full_set: bool
    method: RetrievalMethod
    top_k: int
    budgets: tuple[int, ...] # in token of context for retriever
    api_base_url: str
    enable_cache: bool
    generate_timeout_seconds: float
    concurrency: int
    generate_model: str
    judge_model: str
    judge_backend: str
    ragas_enabled: bool
    experiment_name: str


def load_budget_config(path: Path) -> BudgetRunConfig:
    """Parse and validate one budget eval YAML file."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BudgetYamlError("budget eval file must be a mapping")
    gold_path = _required_str(payload, "gold_path")
    resolved_gold = Path(gold_path)
    if not resolved_gold.is_absolute():
        resolved_gold = PROJECT_ROOT / resolved_gold
    method_raw = payload.get("method", "hybrid")
    if not isinstance(method_raw, str):
        raise BudgetYamlError("method must be a string")
    top_k = _positive_int(payload, "top_k")
    subset_size = _positive_int(payload, "subset_size")
    concurrency = _positive_int(payload, "concurrency")
    if concurrency > 10:
        raise BudgetYamlError("concurrency must be <= 10")
    timeout = payload.get("generate_timeout_seconds", 120)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise BudgetYamlError("generate_timeout_seconds must be positive")
    full_set = payload.get("full_set", False)
    if not isinstance(full_set, bool):
        raise BudgetYamlError("full_set must be a boolean")
    raw_budgets = payload.get("budgets")
    if not isinstance(raw_budgets, list) or not raw_budgets:
        raise BudgetYamlError("budgets must be a non-empty list")
    budgets = tuple(_positive_int({"value": item}, "value") for item in raw_budgets)
    enable_cache = payload.get("enable_cache", False)
    if not isinstance(enable_cache, bool):
        raise BudgetYamlError("enable_cache must be a boolean")
    ragas_enabled = payload.get("ragas_enabled", True)
    if not isinstance(ragas_enabled, bool):
        raise BudgetYamlError("ragas_enabled must be a boolean")
    judge_backend = payload.get("judge_backend", "ragas")
    if judge_backend not in {"json", "ragas"}:
        raise BudgetYamlError("judge_backend must be 'json' or 'ragas'")
    return BudgetRunConfig(
        name=_required_str(payload, "name"),
        gold_path=resolved_gold,
        dataset_version=_required_str(payload, "dataset_version"),
        subset_size=subset_size,
        full_set=full_set,
        method=RetrievalMethod(method_raw),
        top_k=top_k,
        budgets=budgets,
        api_base_url=_required_str(payload, "api_base_url").rstrip("/"),
        enable_cache=enable_cache,
        generate_timeout_seconds=float(timeout),
        concurrency=concurrency,
        generate_model=_required_str(payload, "generate_model"),
        judge_model=_required_str(payload, "judge_model"),
        judge_backend=judge_backend,
        ragas_enabled=ragas_enabled,
        experiment_name=_required_str(payload, "experiment_name"),
    )


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BudgetYamlError(f"{key} must be a non-empty string")
    return value.strip()


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise BudgetYamlError(f"{key} must be a positive integer")
    return value
