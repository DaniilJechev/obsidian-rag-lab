"""Persist one HTTP /search attempt. Failures must not break the response."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import Engine, insert

from rag_based_on_obsidian.db.schema import query_logs
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod

logger = logging.getLogger(__name__)


def write_query_log(
    engine: Engine | None,
    *,
    query: str,
    method: RetrievalMethod,
    top_k: int,
    latency_ms: int,
    result_count: int,
    error: str | None,
) -> None:
    """Insert one log row. Swallow DB errors so search still returns."""
    if engine is None:
        logger.warning("query log skipped: no PostgreSQL engine")
        return
    try:
        with engine.begin() as connection:
            connection.execute(
                insert(query_logs).values(
                    created_at=datetime.now(UTC),
                    query=query,
                    method=method.value,
                    top_k=top_k,
                    latency_ms=max(latency_ms, 0),
                    result_count=result_count,
                    error=error,
                )
            )
    except Exception:
        logger.exception("failed to persist query log")
