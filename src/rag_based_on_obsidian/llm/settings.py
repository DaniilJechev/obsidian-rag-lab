"""YAML settings for the OpenRouter chat adapter."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LLMConfig:
    """One chat-model pin and request budget."""

    name: str
    model: str
    base_url: str
    timeout_seconds: float = 30.0
    temperature: float = 0.2
    max_output_tokens: int = 1024
    max_context_tokens: int = 1800
    min_retrieval_score: float = 0.0
    http_referer: str = ""
    app_title: str = "obsidian-rag-lab"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        if self.max_context_tokens <= 0:
            raise ValueError("max_context_tokens must be positive")


def load_llm_config(path: Path) -> LLMConfig:
    """Load one validated LLM YAML configuration."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("LLM YAML must contain a mapping")
    return LLMConfig(**raw_config)
