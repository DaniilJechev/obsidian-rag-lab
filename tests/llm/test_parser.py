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
