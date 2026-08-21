"""Binary note-level ranking metrics for Phase 7."""

from collections.abc import Collection, Sequence
from math import log2
from statistics import mean

from rag_based_on_obsidian.eval.contracts import (
    SCORED_METRIC_FIELDS,
    DatasetMetrics,
    QuestionMetrics,
)


def ndcg_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return nDCG@k for binary relevance. Empty gold is invalid."""
    _require_positive_k(k)
    relevant_set = _require_nonempty_relevant(relevant)
    gains = _binary_gains(predicted, relevant_set, k)
    dcg = _dcg(gains)
    ideal_count = min(len(relevant_set), k)
    idcg = _dcg([1] * ideal_count)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def mrr_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return reciprocal rank of the first relevant item in top-k."""
    _require_positive_k(k)
    relevant_set = _require_nonempty_relevant(relevant)
    for rank, item in enumerate(predicted[:k], start=1):
        if item in relevant_set:
            return 1.0 / rank
    return 0.0


def precision_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return the fraction of the top-k ranking that is gold."""
    _require_positive_k(k)
    relevant_set = _require_nonempty_relevant(relevant)
    found = relevant_set.intersection(predicted[:k])
    return len(found) / k


def recall_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return the fraction of gold items found in the top-k ranking."""
    _require_positive_k(k)
    relevant_set = _require_nonempty_relevant(relevant)
    found = relevant_set.intersection(predicted[:k])
    return len(found) / len(relevant_set)


def f1_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return the harmonic mean of precision@k and recall@k."""
    precision = precision_at_k(predicted, relevant, k)
    recall = recall_at_k(predicted, relevant, k)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def hit_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return 1.0 if any gold item appears in top-k, else 0.0."""
    return 1.0 if recall_at_k(predicted, relevant, k) > 0 else 0.0


def average_precision_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return TREC average precision over the top-k, divided by |gold|."""
    _require_positive_k(k)
    relevant_set = _require_nonempty_relevant(relevant)
    hits = 0
    precision_sum = 0.0
    for rank, item in enumerate(predicted[:k], start=1):
        if item not in relevant_set:
            continue
        hits += 1
        precision_sum += hits / rank
    return precision_sum / len(relevant_set)


def r_precision(
    predicted: Sequence[object],
    relevant: Collection[object],
) -> float:
    """Return precision at rank |gold| (R-Precision)."""
    relevant_set = _require_nonempty_relevant(relevant)
    return precision_at_k(predicted, relevant_set, len(relevant_set))


def score_question(
    *,
    item_id: str,
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> QuestionMetrics:
    """Score one question at k, or skip it when gold is empty."""
    _require_positive_k(k)
    if not relevant:
        return QuestionMetrics(
            item_id=item_id,
            skipped=True,
            k=k,
            skip_reason="empty_gold",
        )
    return QuestionMetrics(
        item_id=item_id,
        skipped=False,
        k=k,
        ndcg=ndcg_at_k(predicted, relevant, k),
        mrr=mrr_at_k(predicted, relevant, k),
        precision=precision_at_k(predicted, relevant, k),
        recall=recall_at_k(predicted, relevant, k),
        f1=f1_at_k(predicted, relevant, k),
        hit=hit_at_k(predicted, relevant, k),
        average_precision=average_precision_at_k(predicted, relevant, k),
        r_precision=r_precision(predicted, relevant),
    )


def macro_average(
    results: Sequence[QuestionMetrics],
    *,
    k: int,
) -> DatasetMetrics:
    """Average non-skipped questions at the same k. All-skipped sets have None metrics."""
    _require_positive_k(k)
    scored = [item for item in results if not item.skipped]
    skipped_count = len(results) - len(scored)
    empty = {name: None for name in SCORED_METRIC_FIELDS}
    if not scored:
        return DatasetMetrics(
            question_count=len(results),
            scored_count=0,
            skipped_count=skipped_count,
            k=k,
            **empty,
        )
    averaged = {
        name: mean(_required(getattr(item, name)) for item in scored)
        for name in SCORED_METRIC_FIELDS
    }
    return DatasetMetrics(
        question_count=len(results),
        scored_count=len(scored),
        skipped_count=skipped_count,
        k=k,
        **averaged,
    )


def _binary_gains(
    predicted: Sequence[object],
    relevant: set[object],
    k: int,
) -> list[int]:
    return [1 if item in relevant else 0 for item in predicted[:k]]


def _dcg(gains: Sequence[int]) -> float:
    return sum(gain / log2(index + 2) for index, gain in enumerate(gains))


def _require_positive_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be positive")


def _require_nonempty_relevant(relevant: Collection[object]) -> set[object]:
    relevant_set = set(relevant)
    if not relevant_set:
        raise ValueError("relevant set must not be empty")
    return relevant_set


def _required(value: float | None) -> float:
    if value is None:
        raise ValueError("scored question is missing a metric")
    return value
