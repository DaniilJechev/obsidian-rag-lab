"""Tests for embedding smoke metrics."""

import pytest

from rag_based_on_obsidian.embeddings.mlflow_tracking import embedding_metrics


def test_embedding_metrics_report_throughput_and_norms() -> None:
    metrics = embedding_metrics(
        [(0.6, 0.8), (1.0, 0.0)],
        duration_seconds=2.0,
    )

    assert metrics["documents_count"] == 2.0
    assert metrics["documents_per_second"] == 1.0
    assert metrics["vector_norm_mean"] == pytest.approx(1.0)
    assert metrics["vector_norm_min"] == pytest.approx(1.0)
    assert metrics["vector_norm_max"] == pytest.approx(1.0)


def test_embedding_metrics_reject_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="duration_seconds"):
        embedding_metrics([(1.0,)], duration_seconds=0.0)
