"""Parse the LLM JSON blob into citations that match packed chunks."""

from __future__ import annotations

import json
import re
from typing import Any

from rag_based_on_obsidian.llm.contracts import LLMResponseError
from rag_based_on_obsidian.llm.packing import PackedChunk

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def parse_generation_json(
    raw: str,
    packed: list[PackedChunk],
) -> tuple[str, list[dict[str, object]], float]:
    """Return answer, citations, confidence. Unknown chunk ids are dropped."""
    payload = _load_object(raw)
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise LLMResponseError("structured output is missing answer")
    confidence = _parse_confidence(payload.get("confidence"))
    allowed = {item.chunk_id: item.note_path for item in packed}
    citations: list[dict[str, object]] = []
    raw_citations = payload.get("citations", [])
    if raw_citations is None:
        raw_citations = []
    if not isinstance(raw_citations, list):
        raise LLMResponseError("citations must be a list")
    seen: set[int] = set()
    for item in raw_citations:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        if not isinstance(chunk_id, int) or chunk_id in seen:
            continue
        if chunk_id not in allowed:
            continue
        seen.add(chunk_id)
        citations.append(
            {
                "chunk_id": chunk_id,
                "note_path": allowed[chunk_id],
            }
        )
    return answer.strip(), citations, confidence


def _load_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced is not None:
        text = fenced.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMResponseError("structured output is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise LLMResponseError("structured output must be a JSON object")
    return payload


def _parse_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise LLMResponseError("confidence must be a number")
    return min(max(float(value), 0.0), 1.0)
