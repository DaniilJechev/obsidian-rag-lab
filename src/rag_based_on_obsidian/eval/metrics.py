"""Binary note-level ranking metrics for Phase 7."""

from collections.abc import Collection, Sequence
from math import log2
from statistics import mean

from rag_based_on_obsidian.eval.contracts import DatasetMetrics, QuestionMetrics


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


def hit_at_k(
    predicted: Sequence[object],
    relevant: Collection[object],
    k: int,
) -> float:
    """Return 1.0 if any gold item appears in top-k, else 0.0."""
    return 1.0 if recall_at_k(predicted, relevant, k) > 0 else 0.0


def score_question(
    *,
    item_id: str,
    predicted: Sequence[object],
    relevant: Collection[object],
) -> QuestionMetrics:
    """Score one question or skip it when gold is empty."""
    if not relevant:
        return QuestionMetrics(
            item_id=item_id,
            skipped=True,
            skip_reason="empty_gold",
        )
    return QuestionMetrics(
        item_id=item_id,
        skipped=False,
        ndcg_at_5=ndcg_at_k(predicted, relevant, 5),
        ndcg_at_10=ndcg_at_k(predicted, relevant, 10),
        mrr_at_10=mrr_at_k(predicted, relevant, 10),
        recall_at_5=recall_at_k(predicted, relevant, 5),
        recall_at_10=recall_at_k(predicted, relevant, 10),
        hit_at_10=hit_at_k(predicted, relevant, 10),
    )


def macro_average(results: Sequence[QuestionMetrics]) -> DatasetMetrics:
    """Average non-skipped questions. All-skipped sets have None metrics."""
    scored = [item for item in results if not item.skipped]
    skipped_count = len(results) - len(scored)
    if not scored:
        return DatasetMetrics(
            question_count=len(results),
            scored_count=0,
            skipped_count=skipped_count,
            ndcg_at_5=None,
            ndcg_at_10=None,
            mrr_at_10=None,
            recall_at_5=None,
            recall_at_10=None,
            hit_at_10=None,
        )
    return DatasetMetrics(
        question_count=len(results),
        scored_count=len(scored),
        skipped_count=skipped_count,
        ndcg_at_5=mean(_required(item.ndcg_at_5) for item in scored),
        ndcg_at_10=mean(_required(item.ndcg_at_10) for item in scored),
        mrr_at_10=mean(_required(item.mrr_at_10) for item in scored),
        recall_at_5=mean(_required(item.recall_at_5) for item in scored),
        recall_at_10=mean(_required(item.recall_at_10) for item in scored),
        hit_at_10=mean(_required(item.hit_at_10) for item in scored),
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
