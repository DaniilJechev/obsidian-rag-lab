"""Note-level Context Precision / Recall when gold has notes, not answers."""

from collections.abc import Sequence
from statistics import mean


def unique_note_paths(paths: Sequence[str]) -> tuple[str, ...]:
    """Keep first occurrence of each vault-relative note path."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in paths:
        path = raw.replace("\\", "/").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


def context_precision(
    packed_paths: Sequence[str],
    gold_paths: Sequence[str],
) -> float:
    """Average precision of packed notes against gold notes, in pack order."""
    gold = set(unique_note_paths(gold_paths))
    if not gold:
        raise ValueError("gold_paths must not be empty")
    ranked = unique_note_paths(packed_paths)
    hits = 0
    precisions: list[float] = []
    for rank, path in enumerate(ranked, start=1):
        if path not in gold:
            continue
        hits += 1
        precisions.append(hits / rank)
    if not precisions:
        return 0.0
    return mean(precisions)


def context_recall(
    packed_paths: Sequence[str],
    gold_paths: Sequence[str],
) -> float:
    """Fraction of gold notes that appear at least once in packed context."""
    gold = unique_note_paths(gold_paths)
    if not gold:
        raise ValueError("gold_paths must not be empty")
    packed = set(unique_note_paths(packed_paths))
    found = packed.intersection(gold)
    return len(found) / len(gold)
