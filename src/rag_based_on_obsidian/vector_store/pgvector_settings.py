"""Configuration for the experimental PostgreSQL + pgvector store."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag_based_on_obsidian.db.pgvector_schema import DEFAULT_PGVECTOR_TABLE


@dataclass(frozen=True)
class PgvectorConfig:
    """Validated operational settings for the pgvector comparison store."""

    table: str = DEFAULT_PGVECTOR_TABLE
    max_retries: int = 2
    retry_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        """Reject settings that would make upsert or search ambiguous."""
        if not self.table.strip():
            raise ValueError("table must not be empty")
        if not self.table.isidentifier():
            raise ValueError("table must be a plain SQL identifier")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")


def load_pgvector_config(path: Path) -> PgvectorConfig:
    """Load one validated pgvector YAML configuration."""
    with path.open(encoding="utf-8") as config_file:
        raw_config: Any = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("pgvector YAML must contain a mapping")
    return PgvectorConfig(**raw_config)
