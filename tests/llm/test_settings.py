"""LLM YAML loader."""

from pathlib import Path

from rag_based_on_obsidian.config import DEFAULT_LLM_CONFIG_PATH
from rag_based_on_obsidian.llm.settings import load_llm_config


def test_load_checked_in_openrouter_config() -> None:
    config = load_llm_config(DEFAULT_LLM_CONFIG_PATH)
    assert config.model == "openai/gpt-4o-mini"
    assert config.base_url.startswith("https://openrouter.ai")
    assert config.max_context_tokens > 0


def test_load_llm_config_from_temp(tmp_path: Path) -> None:
    path = tmp_path / "llm.yaml"
    path.write_text(
        (
            "name: tmp\n"
            "model: openai/gpt-4o-mini\n"
            "base_url: https://openrouter.ai/api/v1\n"
        ),
        encoding="utf-8",
    )
    config = load_llm_config(path)
    assert config.name == "tmp"
    assert config.timeout_seconds == 30.0
