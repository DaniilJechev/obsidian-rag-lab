from math import log2

import pytest

from rag_based_on_obsidian.eval.metrics import (
    hit_at_k,
    macro_average,
    mrr_at_k,
    ndcg_at_k,
    recall_at_k,
    score_question,
)


def test_ndcg_mrr_recall_match_hand_calculated_ranking() -> None:
    predicted = ("A", "X", "B")
    relevant = {"A", "B"}
    dcg = 1 / log2(2) + 1 / log2(4)
    idcg = 1 / log2(2) + 1 / log2(3)
    expected_ndcg = dcg / idcg

    assert ndcg_at_k(predicted, relevant, 3) == pytest.approx(expected_ndcg)
    assert ndcg_at_k(predicted, relevant, 5) == pytest.approx(expected_ndcg)
    assert ndcg_at_k(predicted, relevant, 10) == pytest.approx(expected_ndcg)
    assert mrr_at_k(predicted, relevant, 10) == pytest.approx(1.0)
    assert recall_at_k(predicted, relevant, 5) == pytest.approx(1.0)
    assert hit_at_k(predicted, relevant, 10) == pytest.approx(1.0)


def test_late_relevant_item_lowers_ndcg_and_mrr() -> None:
    predicted = ("X", "Y", "A")
    relevant = {"A"}
    expected_ndcg = (1 / log2(4)) / (1 / log2(2))

    assert ndcg_at_k(predicted, relevant, 10) == pytest.approx(expected_ndcg)
    assert mrr_at_k(predicted, relevant, 10) == pytest.approx(1 / 3)
    assert recall_at_k(predicted, relevant, 5) == pytest.approx(1.0)
    assert recall_at_k(predicted, relevant, 2) == pytest.approx(0.0)
    assert hit_at_k(predicted, relevant, 10) == pytest.approx(1.0)


def test_missed_gold_returns_zero_metrics() -> None:
    predicted = ("X", "Y")
    relevant = {"A"}

    assert ndcg_at_k(predicted, relevant, 10) == 0.0
    assert mrr_at_k(predicted, relevant, 10) == 0.0
    assert recall_at_k(predicted, relevant, 10) == 0.0
    assert hit_at_k(predicted, relevant, 10) == 0.0


def test_empty_gold_is_skipped_instead_of_nan() -> None:
    result = score_question(item_id="q-empty", predicted=("A",), relevant=())

    assert result.skipped is True
    assert result.skip_reason == "empty_gold"
    assert result.ndcg_at_10 is None


def test_empty_relevant_raises_on_direct_metric_calls() -> None:
    with pytest.raises(ValueError, match="relevant set"):
        ndcg_at_k(("A",), (), 5)


def test_macro_average_ignores_skipped_questions() -> None:
    scored = score_question(item_id="q1", predicted=("A",), relevant={"A"})
    skipped = score_question(item_id="q2", predicted=("A",), relevant=())
    summary = macro_average([scored, skipped])

    assert summary.question_count == 2
    assert summary.scored_count == 1
    assert summary.skipped_count == 1
    assert summary.ndcg_at_10 == pytest.approx(1.0)
    assert summary.mrr_at_10 == pytest.approx(1.0)
