"""Cosine similarity helpers for semantic cache lookup."""

from __future__ import annotations

from collections.abc import Sequence


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    """Dot product for L2-normalized vectors (E5 output)."""
    if len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    if not left:
        return 0.0
    return float(sum(a * b for a, b in zip(left, right, strict=True)))
