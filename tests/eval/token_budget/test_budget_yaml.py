"""Tests for token budget eval YAML loader."""

from pathlib import Path

from rag_based_on_obsidian.eval.token_budget.budget_yaml import load_budget_config
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


def test_load_budget_yaml_defaults() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "configs"
        / "eval"
        / "token_budget"
        / "budget.yaml"
    )
    config = load_budget_config(path)
    assert config.name == "sprint29-token-budget-eval"
    assert config.dataset_version == "phase7_GT_note_level_v0"
    assert config.subset_size == 15
    assert config.method is RetrievalMethod.HYBRID
    assert config.top_k == 5
    assert config.budgets == (800, 1200, 1800)
    assert config.enable_cache is False
    assert config.ragas_enabled is True
    assert config.experiment_name == "phase-13-token-budget-eval"
