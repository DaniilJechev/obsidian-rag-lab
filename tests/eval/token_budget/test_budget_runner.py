"""Tests for budget runner aggregation helpers."""

from rag_based_on_obsidian.eval.token_budget.budget_runner import (
    BudgetQueryResult,
    _parse_gate_est_tokens,
    _summarize,
)


def test_parse_gate_est_tokens_from_trace() -> None:
    reason = "packed=3 budget=1200 est_tokens=450 refused=false"
    assert _parse_gate_est_tokens(reason) == 450


def test_summarize_computes_refusal_rate() -> None:
    rows = [
        BudgetQueryResult(
            item_id="q1",
            budget=800,
            query="q",
            prompt_tokens=100,
            generated_tokens=20,
            latency_ms=500,
            packed_chunks=1,
            est_tokens=90,
            refused=False,
            refusal_reason=None,
            model="m",
            answer="a",
            packed_note_paths=("DLS2/RoPE.md",),
            ndcg_at_k=1.0,
            mrr_at_k=1.0,
        ),
        BudgetQueryResult(
            item_id="q2",
            budget=800,
            query="q2",
            prompt_tokens=None,
            generated_tokens=None,
            latency_ms=None,
            packed_chunks=0,
            est_tokens=None,
            refused=True,
            refusal_reason="no retrieved context",
            model=None,
            answer=None,
            packed_note_paths=(),
            ndcg_at_k=None,
            mrr_at_k=None,
        ),
    ]
    summary = _summarize(800, rows)
    assert summary.question_count == 2
    assert summary.refused_count == 1
    assert summary.refusal_rate == 0.5
    assert summary.mean_prompt_tokens == 100.0
