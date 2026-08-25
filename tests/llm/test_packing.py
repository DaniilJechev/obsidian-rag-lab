"""Packing and refuse heuristics. No network."""

from rag_based_on_obsidian.llm.packing import (
    SYSTEM_PROMPT,
    build_messages,
    estimate_tokens,
    pack_chunks,
    should_refuse,
)
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


def _chunk(*, chunk_id: int = 1, text: str = "hello world", score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=score,
        retrieval_method=RetrievalMethod.HYBRID,
        metadata={"source_path": "DLS2/RoPE.md"},
        chunking_version="sprint9-policy-512-v2",
        rank=1,
    )


def test_system_prompt_includes_one_shot_json_example() -> None:
    assert '"answer"' in SYSTEM_PROMPT
    assert '"citations"' in SYSTEM_PROMPT
    assert '"confidence"' in SYSTEM_PROMPT
    assert "no markdown fences" in SYSTEM_PROMPT
    assert "invalid JSON" in SYSTEM_PROMPT
    assert "concise" in SYSTEM_PROMPT
    messages = build_messages("What is RoPE?", pack_chunks([_chunk()], max_context_tokens=50))
    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT
    assert "Question: What is RoPE?" in messages[1].content


def test_should_refuse_empty_hits() -> None:
    assert should_refuse([], min_retrieval_score=0.0) == "no retrieved context"


def test_should_refuse_low_score() -> None:
    reason = should_refuse([_chunk(score=0.01)], min_retrieval_score=0.5)
    assert reason == "retrieved context is below the score threshold"


def test_should_not_refuse_positive_score() -> None:
    assert should_refuse([_chunk(score=0.02)], min_retrieval_score=0.0) is None


def test_pack_chunks_keeps_prefix_within_budget() -> None:
    chunks = [
        _chunk(chunk_id=1, text="aaaa " * 20),
        _chunk(chunk_id=2, text="bbbb " * 20),
    ]
    packed = pack_chunks(chunks, max_context_tokens=estimate_tokens("aaaa " * 20))
    assert [item.chunk_id for item in packed] == [1]


def test_pack_chunks_truncates_oversized_first_chunk() -> None:
    packed = pack_chunks(
        [_chunk(text="x" * 400)],
        max_context_tokens=10,
    )
    assert len(packed) == 1
    assert packed[0].chunk_id == 1
    assert estimate_tokens(packed[0].text) <= 10
