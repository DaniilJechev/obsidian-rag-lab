"""Rule-based policies for Sprint 25 graph nodes (no extra LLM calls).

Kept deterministic for CI. Latency/cost stay on retrieve+generate only;
rewrite/self-check are local heuristics with max one retry.
"""

from __future__ import annotations

from typing import Any

MAX_SELF_CHECK_RETRIES = 1
MIN_SELF_CHECK_CONFIDENCE = 0.4


def classify_query(query: str) -> tuple[str, str]:
    """Return ``(label, reason)`` with label ``rag_qa`` or ``refuse``."""
    stripped = query.strip()
    if len(stripped) < 3:
        return "refuse", "query too short"
    if not any(char.isalpha() for char in stripped):
        return "refuse", "query has no letters"
    return "rag_qa", "looks like a vault question"


def rewrite_query(query: str, *, attempt: int) -> str:
    """Light query rewrite for one controlled retry."""
    cleaned = " ".join(query.split())
    if attempt <= 0:
        return f"{cleaned} (кратко по заметкам vault, ключевые термины)"
    return cleaned


def self_check_generation(
    *,
    answer: str | None,
    confidence: float,
    citations: list[dict[str, Any]] | None,
    refused: bool,
) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for the generate output."""
    if refused:
        return True, "refused path needs no answer check"
    if answer is None or not str(answer).strip():
        return False, "empty answer"
    if float(confidence) < MIN_SELF_CHECK_CONFIDENCE:
        return False, "low confidence"
    if not citations:
        return False, "missing citations"
    return True, "answer looks grounded"
