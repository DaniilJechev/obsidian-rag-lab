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


@dataclass(frozen=True)
class BatchEmbeddingConfig:
    """Configuration for one version-aware batch embedding run."""

    name: str
    chunking_version: str
    artifact_dir: Path
    batch_size: int
    max_retries: int = 2
    retry_backoff_seconds: float = 0.0
    tracking_uri: str = "http://127.0.0.1:5000"
    experiment_name: str = "sprint-11-batch-embedding"
    run_name: str = "batch-embedding"
    show_progress: bool = True

    def __post_init__(self) -> None:
        """Reject settings that could make a run ambiguous or unbounded."""
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative")
        if not self.tracking_uri.strip():
            raise ValueError("tracking_uri must not be empty")
        if not self.experiment_name.strip():
            raise ValueError("experiment_name must not be empty")
        if not self.run_name.strip():
            raise ValueError("run_name must not be empty")


def load_embedding_model_config(path: Path) -> EmbeddingModelConfig:
    """Load one validated embedding model configuration from YAML."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("embedding model YAML must contain a mapping")
    return EmbeddingModelConfig(**raw_config)


def load_batch_embedding_config(path: Path) -> BatchEmbeddingConfig:
    """Load one validated batch embedding configuration from YAML."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("batch embedding YAML must contain a mapping")
    raw_config["artifact_dir"] = Path(raw_config["artifact_dir"])
    return BatchEmbeddingConfig(**raw_config)
