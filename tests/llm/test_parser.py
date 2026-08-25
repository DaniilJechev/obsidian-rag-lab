"""Structured-output parser. No network."""

import json

import pytest

from rag_based_on_obsidian.llm.contracts import LLMResponseError
from rag_based_on_obsidian.llm.packing import PackedChunk
from rag_based_on_obsidian.llm.parser import parse_generation_json

_PACKED = [
    PackedChunk(chunk_id=1, note_path="DLS2/RoPE.md", text="rope", score=0.9),
    PackedChunk(chunk_id=2, note_path="DLS1/BERT.md", text="bert", score=0.8),
]


def test_parse_accepts_fenced_json_and_drops_unknown_ids() -> None:
    raw = (
        "```json\n"
        + json.dumps(
            {
                "answer": "RoPE rotates queries.",
                "citations": [
                    {"chunk_id": 1, "note_path": "ignored"},
                    {"chunk_id": 99, "note_path": "nope"},
                ],
                "confidence": 1.5,
            }
        )
        + "\n```"
    )
    answer, citations, confidence = parse_generation_json(raw, _PACKED)
    assert answer.startswith("RoPE")
    assert citations == [{"chunk_id": 1, "note_path": "DLS2/RoPE.md"}]
    assert confidence == 1.0


def test_parse_rejects_non_json() -> None:
    with pytest.raises(LLMResponseError, match="valid JSON"):
        parse_generation_json("not json", _PACKED)


def test_parse_tolerates_raw_latex_backslashes_in_answer() -> None:
    # Gemini-style: TeX commands written as JSON escapes without doubling.
    raw = (
        '{"answer":"Use x \\approx 0 when n \\ge 1 and '
        'integrate \\int_0^1 f.",'
        '"citations":[{"chunk_id":1}],'
        '"confidence":0.8}'
    )
    answer, citations, confidence = parse_generation_json(raw, _PACKED)
    assert "\\approx" in answer
    assert "\\ge" in answer
    assert "\\int" in answer
    assert citations == [{"chunk_id": 1, "note_path": "DLS2/RoPE.md"}]
    assert confidence == 0.8


def test_parse_keeps_valid_json_escapes_with_latex() -> None:
    raw = (
        '{"answer":"line1\\nthen x \\\\approx 0",'
        '"citations":[{"chunk_id":1}],'
        '"confidence":0.5}'
    )
    answer, _, _ = parse_generation_json(raw, _PACKED)
    assert "line1\nthen" in answer
    assert "\\approx" in answer


def test_parse_extracts_object_when_wrapped_in_prose() -> None:
    raw = (
        "Here you go:\n"
        '{"answer":"ok","citations":[{"chunk_id":1}],"confidence":0.1}\n'
        "thanks"
    )
    answer, _, _ = parse_generation_json(raw, _PACKED)
    assert answer == "ok"
