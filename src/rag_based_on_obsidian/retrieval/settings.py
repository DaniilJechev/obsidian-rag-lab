"""Validated configuration for synthetic retrieval runs."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag_based_on_obsidian.retrieval.rerank_settings import (
    RerankConfig,
    default_rerank_config,
    parse_rerank_config,
)


@dataclass(frozen=True)
class RetrievalConfig:
    """Settings shared by dense, BM25 and RRF retrieval."""

    name: str
    chunking_version: str
    top_k: int = 5
    candidate_k: int = 20
    rrf_k: int = 60
    postgres_batch_size: int = 256
    show_scores: bool = True
    filters: dict[str, object] = field(default_factory=dict)
    rerank: RerankConfig = field(default_factory=default_rerank_config)

    def __post_init__(self) -> None:
        """Reject settings that could make ranking ambiguous."""
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.candidate_k < self.top_k:
            raise ValueError("candidate_k must be at least top_k")
        if self.rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        if self.postgres_batch_size <= 0:
            raise ValueError("postgres_batch_size must be positive")


def load_retrieval_config(path: Path) -> RetrievalConfig:
    """Load one validated retrieval YAML configuration (includes optional ``rerank``)."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("retrieval YAML must contain a mapping")
    payload = dict(raw_config)
    rerank_raw = payload.pop("rerank", None)
    if rerank_raw is None:
        rerank = default_rerank_config()
    elif isinstance(rerank_raw, dict):
        rerank = parse_rerank_config(rerank_raw)
    else:
        raise TypeError("retrieval YAML rerank must be a mapping when set")
    return RetrievalConfig(**payload, rerank=rerank)
