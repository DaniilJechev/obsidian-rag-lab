"""Unit tests for Sprint 25 rule-based graph policies."""

from rag_based_on_obsidian.lang_graph.policies import (
    classify_query,
    rewrite_query,
    self_check_generation,
)


def test_classify_refuse_short_and_accept_question() -> None:
    assert classify_query("??")[0] == "refuse"
    assert classify_query("What is RoPE?")[0] == "rag_qa"


def test_rewrite_adds_vault_hint_on_first_attempt() -> None:
    out = rewrite_query("What is RoPE?", attempt=0)
    assert "What is RoPE?" in out
    assert "vault" in out.lower() or "заметк" in out.lower()


def test_self_check_rejects_low_confidence() -> None:
    ok, reason = self_check_generation(
        answer="x",
        confidence=0.1,
        citations=[{"chunk_id": 1}],
        refused=False,
    )
    assert ok is False
    assert "confidence" in reason
