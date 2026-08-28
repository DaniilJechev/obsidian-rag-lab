"""Typed state for the generate LangGraph (Sprint 24–25)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


class GenerateGraphState(TypedDict, total=False):
    """In-process graph state. Not checkpointed; objects stay in memory.

    ``chunks`` / ``packed`` stay as ``list[Any]`` so LangGraph can resolve
    hints without importing ``llm.packing`` (avoids a cycle with ``pipeline``).

    ``path`` and ``trace`` use add-reducers so nodes append without clobbering.
    """

    query: str
    original_query: str
    method: RetrievalMethod
    top_k: int
    chunks: list[Any]
    packed: list[Any]
    refuse_reason: str | None
    classify_label: str
    retry_count: int
    self_check_ok: bool | None
    self_check_reason: str | None
    path: Annotated[list[str], operator.add]
    trace: Annotated[list[dict[str, str]], operator.add]
    answer: str | None
    citations: list[dict[str, Any]]
    contexts: list[dict[str, Any]]
    confidence: float
    refused: bool
    model: str | None
    latency_ms: int | None
    usage: dict[str, int] | None
    cache_hit: bool
    cache_similarity: float | None
    cache_matched_query: str | None
