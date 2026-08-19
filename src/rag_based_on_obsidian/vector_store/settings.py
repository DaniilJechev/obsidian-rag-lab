"""Configuration for the Qdrant vector store."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class QdrantConfig:
    """Validated connection and operational settings for Qdrant."""

    url: str
    collection: str
    scroll_page_size: int = 256
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0
    bm25_avg_len: float = 191.0
    bm25_model: str = "Qdrant/bm25"

    def __post_init__(self) -> None:
        """Reject settings that could make storage operations ambiguous."""
        if not self.url.strip():
            raise ValueError("url must not be empty")
        if not self.collection.strip():
            raise ValueError("collection must not be empty")
        if self.scroll_page_size <= 0:
            raise ValueError("scroll_page_size must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative")
        if self.bm25_avg_len <= 0:
            raise ValueError("bm25_avg_len must be positive")
        if not self.bm25_model.strip():
            raise ValueError("bm25_model must not be empty")


def load_qdrant_config(path: Path) -> QdrantConfig:
    """Load one validated Qdrant configuration from YAML."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("Qdrant YAML must contain a mapping")
    return QdrantConfig(**raw_config)
