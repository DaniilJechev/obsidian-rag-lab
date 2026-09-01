"""Tests for cache eval MLflow payload builders."""

from rag_based_on_obsidian.eval.cache.cache_mlflow import (
    build_cache_eval_artifacts,
    per_query_mlflow_metrics,
    query_record,
)
from rag_based_on_obsidian.eval.cache.cache_runner import (
    CacheEvalSummary,
    CacheQueryResult,
)


def _row(
    *,
    group_id: str = "s001",
    pass_name: str = "paraphrase",
    cache_hit: bool = True,
    latency_ms: int = 120,
) -> CacheQueryResult:
    return CacheQueryResult(
        group_id=group_id,
        pass_name=pass_name,
        query="test query",
        cache_hit=cache_hit,
        cache_similarity=0.95 if cache_hit else None,
        cache_matched_query="canonical" if cache_hit else None,
        latency_ms=latency_ms,
        prompt_tokens=10,
        generated_tokens=20,
        refused=False,
        refusal_reason=None,
        model="openai/gpt-4o-mini",
        answer="answer text",
    )


def _summary() -> CacheEvalSummary:
    return CacheEvalSummary(
        dataset_version="cache_paraphrase_smoke_v0",
        group_count=1,
        canonical_count=1,
        paraphrase_count=1,
        paraphrase_hits=1,
        hit_rate=1.0,
        latency_p50_ms=120.0,
        latency_p95_ms=120.0,
        canonical_latency_p50_ms=500.0,
        pass1_tokens=30,
        pass2_tokens=30,
        tokens_saved=0,
        avg_latency_ms=310.0,
        canonical_avg_latency_ms=500.0,
        paraphrase_avg_latency_ms=120.0,
        paraphrase_hit_avg_latency_ms=120.0,
        paraphrase_miss_avg_latency_ms=0.0,
    )


def test_query_record_includes_cache_hit_and_latency() -> None:
    record = query_record(_row(), index=1)
    assert record["cache_hit"] is True
    assert record["latency_ms"] == 120
    assert record["avg_latency_ms"] == 120.0
    assert record["cache_similarity"] == 0.95
    assert record["answer"] == "answer text"


def test_per_query_mlflow_metrics_names() -> None:
    rows = [
        _row(group_id="s001", pass_name="canonical", cache_hit=False, latency_ms=400),
        _row(group_id="s001", pass_name="paraphrase", cache_hit=True, latency_ms=50),
    ]
    metrics = per_query_mlflow_metrics(rows)
    assert metrics["q_s001_canonical_cache_hit"] == 0.0
    assert metrics["q_s001_canonical_latency_ms"] == 400.0
    assert metrics["q_s001_paraphrase_cache_hit"] == 1.0
    assert metrics["q_s001_paraphrase_latency_ms"] == 50.0
    assert metrics["q_s001_paraphrase_cache_similarity"] == 0.95


def test_build_cache_eval_artifacts_has_summary_and_per_query() -> None:
    rows = [_row()]
    payload = build_cache_eval_artifacts(
        dataset_version="cache_paraphrase_smoke_v0",
        summary=_summary(),
        rows=rows,
        enable_cache=True,
        duration_seconds=12.5,
        extra_params={"top_k": 5},
    )
    assert payload["summary"]["hit_rate"] == 1.0
    assert payload["summary"]["paraphrase_avg_latency_ms"] == 120.0
    assert payload["summary"]["run_params"] == {"top_k": 5}
    assert len(payload["per_query"]) == 1
    assert payload["per_query"][0]["group_id"] == "s001"
