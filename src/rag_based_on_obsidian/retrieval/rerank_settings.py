"""Validated configuration for cross-encoder rerank (Sprint 26)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RerankConfig:
    """Settings for optional BGE cross-encoder after hybrid retrieval.

    Pool size is ``RetrievalConfig.candidate_k`` (RRF output = CE input), not a
    separate ``top_n``. Final cut after CE is request ``top_k``.
    """

    name: str
    model_name: str = "BAAI/bge-reranker-v2-m3"
    model_revision: str | None = None
    enabled: bool = False
    use_fp16: bool = True
    max_length: int = 512
    batch_size: int = 8
    warm_load: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty")
        if self.max_length <= 0:
            raise ValueError("max_length must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.model_revision is not None and not str(self.model_revision).strip():
            raise ValueError("model_revision must not be blank when set")


def default_rerank_config() -> RerankConfig:
    """Disabled CE defaults when ``retrieval.yaml`` omits the ``rerank`` block."""
    return RerankConfig(name="rerank-off", enabled=False)


def parse_rerank_config(raw_config: Mapping[str, Any]) -> RerankConfig:
    """Validate one ``rerank:`` mapping from ``retrieval.yaml``."""
    payload: dict[str, Any] = dict(raw_config)
    if "top_n" in payload:
        raise ValueError(
            "rerank.top_n is removed; use top-level candidate_k as the RRF→CE pool"
        )
    revision = payload.get("model_revision")
    if revision is not None:
        payload["model_revision"] = str(revision)
    return RerankConfig(**payload)
