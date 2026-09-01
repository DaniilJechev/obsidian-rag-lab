"""Shared gold subset selection for eval harnesses."""

from __future__ import annotations

from collections.abc import Sequence

from rag_based_on_obsidian.eval.contracts import GoldItem


def select_gold_slice(
    items: Sequence[GoldItem],
    *,
    subset_size: int,
    full_set: bool = False,
) -> tuple[GoldItem, ...]:
    """Take YAML order: first ``subset_size`` items, or the full gold list."""
    if not items:
        raise ValueError("gold items must not be empty")
    if full_set:
        return tuple(items)
    if subset_size > len(items):
        raise ValueError(f"subset_size {subset_size} exceeds gold size {len(items)}")
    return tuple(items[:subset_size])
