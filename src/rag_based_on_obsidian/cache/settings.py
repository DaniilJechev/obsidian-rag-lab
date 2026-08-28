"""Validated configuration for semantic cache (Sprint 28)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CacheConfig:
    """Redis-backed semantic cache settings."""

    name: str
    enabled: bool = False
    cache_type: str = "semantic"
    similarity_threshold: float = 0.92
    max_entries: int = 500
    ttl_seconds: int = 86400
    refresh_ttl_on_hit: bool = True
    eviction_policy: str = "lru_when_full"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if self.cache_type != "semantic":
            raise ValueError("only cache_type=semantic is supported in Sprint 28")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be in [0, 1]")
        if self.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")


def default_cache_config() -> CacheConfig:
    """Disabled semantic cache defaults."""
    return CacheConfig(name="cache-off", enabled=False)


def parse_cache_config(raw_config: Mapping[str, Any]) -> CacheConfig:
    """Validate one cache YAML mapping."""
    return CacheConfig(**dict(raw_config))


def load_cache_config(path: Path) -> CacheConfig:
    """Load cache settings from YAML."""
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise TypeError("cache YAML must contain a mapping")
    return parse_cache_config(raw)
