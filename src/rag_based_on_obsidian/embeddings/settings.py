"""Typed configuration for local embedding model providers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EmbeddingModelConfig:
    """Configuration needed to load and run one embedding model."""

    name: str
    model_name: str
    model_revision: str
    device: str
    max_length: int
    batch_size: int
    normalized: bool
    document_prefix: str
    query_prefix: str
    show_progress: bool = True

    def __post_init__(self) -> None:
        """Reject invalid inference settings before model loading."""
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty")
        if not self.model_revision.strip():
            raise ValueError("model_revision must not be empty")
        if not self.device.strip():
            raise ValueError("device must not be empty")
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")


def load_embedding_model_config(path: Path) -> EmbeddingModelConfig:
    """Load one validated embedding model configuration from YAML."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("embedding model YAML must contain a mapping")
    return EmbeddingModelConfig(**raw_config)
