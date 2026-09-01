"""YAML settings for the Phase 10 RAGAS generation eval harness."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag_based_on_obsidian.config import PROJECT_ROOT
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


@dataclass(frozen=True)
class RagasRunConfig:
    """One live RAGAS run: API generate + judge pin + gold slice."""

    name: str
    gold_path: Path
    dataset_version: str
    api_base_url: str
    method: RetrievalMethod
    top_k: int
    subset_size: int
    full_set: bool
    concurrency: int
    generate_model: str
    judge_model: str
    judge_backend: str
    generate_timeout_seconds: float
    human_sample_path: Path | None = None
    human_review_path: Path | None = None


def load_ragas_config(path: Path) -> RagasRunConfig:
    """Load and validate one RAGAS harness YAML file."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("RAGAS YAML must contain a mapping")
    gold_path = raw_config.get("gold_path")
    if not isinstance(gold_path, str) or not gold_path.strip():
        raise ValueError("gold_path must be a non-empty string")
    resolved_gold = Path(gold_path)
    if not resolved_gold.is_absolute():
        resolved_gold = PROJECT_ROOT / resolved_gold
    method_raw = raw_config.get("method", "hybrid")
    if not isinstance(method_raw, str):
        raise TypeError("method must be a string")
    top_k = _positive_int(raw_config, "top_k")
    subset_size = _positive_int(raw_config, "subset_size")
    concurrency = _positive_int(raw_config, "concurrency")
    if concurrency > 10:
        raise ValueError("concurrency must be <= 10")
    timeout = raw_config.get("generate_timeout_seconds", 60)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("generate_timeout_seconds must be positive")
    full_set = raw_config.get("full_set", False)
    if not isinstance(full_set, bool):
        raise TypeError("full_set must be a boolean")
    human_sample_path = _optional_project_path(raw_config, "human_sample_path")
    human_review_path = _optional_project_path(raw_config, "human_review_path")
    if (human_sample_path is None) != (human_review_path is None):
        raise ValueError(
            "human_sample_path and human_review_path must be set together"
        )
    judge_backend = raw_config.get("judge_backend", "json")
    if judge_backend not in {"json", "ragas"}:
        raise ValueError("judge_backend must be 'json' or 'ragas'")
    return RagasRunConfig(
        name=_required_str(raw_config, "name"),
        gold_path=resolved_gold,
        dataset_version=_required_str(raw_config, "dataset_version"),
        api_base_url=_required_str(raw_config, "api_base_url").rstrip("/"),
        method=RetrievalMethod(method_raw),
        top_k=top_k,
        subset_size=subset_size,
        full_set=full_set,
        concurrency=concurrency,
        generate_model=_required_str(raw_config, "generate_model"),
        judge_model=_required_str(raw_config, "judge_model"),
        judge_backend=str(judge_backend),
        generate_timeout_seconds=float(timeout),
        human_sample_path=human_sample_path,
        human_review_path=human_review_path,
    )


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_project_path(payload: dict[str, Any], key: str) -> Path | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when set")
    resolved = Path(value.strip())
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def _positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value
