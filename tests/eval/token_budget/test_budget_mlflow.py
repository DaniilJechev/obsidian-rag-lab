"""Tests for budget eval MLflow payload builders."""

from rag_based_on_obsidian.eval.token_budget.budget_mlflow import (
    build_budget_eval_artifacts,
    query_record,
)
from rag_based_on_obsidian.eval.token_budget.budget_runner import (
    BudgetEvalSummary,
    BudgetQueryResult,
)


def test_build_budget_eval_artifacts_includes_gate_trace() -> None:
    row = BudgetQueryResult(
        item_id="q1",
        budget=800,
        query="What is RoPE?",
        prompt_tokens=120,
        generated_tokens=40,
        latency_ms=900,
        packed_chunks=2,
        est_tokens=110,
        refused=False,
        refusal_reason=None,
        model="openai/gpt-4o-mini",
        answer="RoPE rotates embeddings.",
        packed_note_paths=("DLS2/RoPE.md",),
        ndcg_at_k=0.8,
        mrr_at_k=1.0,
        faithfulness=0.9,
        answer_relevancy=0.85,
        gate_trace="packed=2 budget=800 est_tokens=110 refused=false",
    )
    summary = BudgetEvalSummary(
        budget=800,
        question_count=1,
        scored_count=1,
        skipped_count=0,
        refused_count=0,
        mean_prompt_tokens=120.0,
        median_prompt_tokens=120.0,
        p95_prompt_tokens=120.0,
        mean_generated_tokens=40.0,
        mean_latency_ms=900.0,
        p50_latency_ms=900.0,
        p95_latency_ms=900.0,
        mean_packed_chunks=2.0,
        mean_est_tokens=110.0,
        mean_ndcg_at_k=0.8,
        mean_mrr_at_k=1.0,
        mean_faithfulness=0.9,
        mean_answer_relevancy=0.85,
        refusal_rate=0.0,
    )
    artifacts = build_budget_eval_artifacts(
        dataset_version="phase7_GT_note_level_v0",
        summary=summary,
        rows=[row],
        duration_seconds=1.5,
    )
    per_query = artifacts["per_query"]
    assert isinstance(per_query, list)
    assert per_query[0]["gate_trace"] == row.gate_trace
    record = query_record(row, index=1)
    assert record["budget"] == 800
    assert record["prompt_tokens"] == 120
