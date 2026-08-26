"""Typed state for the Sprint 24 generate graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


class GenerateGraphState(TypedDict, total=False):
    """In-process graph state. Not checkpointed; objects stay in memory.

    ``chunks`` / ``packed`` stay as ``list[Any]`` so LangGraph can resolve
    hints without importing ``llm.packing`` (avoids a cycle with ``pipeline``).

    ``path`` uses an add-reducer so each node appends its name without
    clobbering earlier hops.
    """

    query: str
    method: RetrievalMethod
    top_k: int
    chunks: list[Any]
    packed: list[Any]
    refuse_reason: str | None
    path: Annotated[list[str], operator.add]
    answer: str | None
    citations: list[dict[str, Any]]
    contexts: list[dict[str, Any]]
    confidence: float
    refused: bool
    model: str | None
    latency_ms: int | None
    usage: dict[str, int] | None
