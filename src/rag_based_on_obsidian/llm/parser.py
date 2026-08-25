"""Parse the LLM JSON blob into citations that match packed chunks."""

from __future__ import annotations

import json
import re
from typing import Any

from rag_based_on_obsidian.llm.contracts import LLMResponseError
from rag_based_on_obsidian.llm.packing import PackedChunk

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_HEX = frozenset("0123456789abcdefABCDEF")
_SIMPLE_ESCAPES = frozenset('"\\/bfnrt')


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
    text = _candidate_json(raw)
    payload = _loads_json(text)
    if payload is None:
        repaired = _repair_invalid_escapes(text)
        if repaired != text:
            payload = _loads_json(repaired)
    if payload is None:
        raise LLMResponseError("structured output is not valid JSON")
    if not isinstance(payload, dict):
        raise LLMResponseError("structured output must be a JSON object")
    return payload


def _candidate_json(raw: str) -> str:
    """Strip fences and keep the outermost object when prose wraps it."""
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced is not None:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _loads_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _repair_invalid_escapes(text: str) -> str:
    """Double backslashes that are not valid JSON escapes (e.g. LaTeX ``\\approx``).

    Models often emit raw TeX inside JSON strings: ``\\approx``, ``\\ge``,
    ``\\int``. Those are illegal JSON escapes; ``json.loads`` then fails even
    when the answer text itself is fine. Valid escapes (``\\"``, ``\\\\``,
    ``\\n``, ``\\uXXXX``, …) are left unchanged.
    """
    out: list[str] = []
    in_string = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if not in_string:
            if ch == '"':
                in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_string = False
            out.append(ch)
            i += 1
            continue
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= length:
            out.append("\\\\")
            i += 1
            continue
        nxt = text[i + 1]
        if nxt in _SIMPLE_ESCAPES:
            out.append(ch)
            out.append(nxt)
            i += 2
            continue
        if nxt == "u" and i + 5 < length and all(
            text[j] in _HEX for j in range(i + 2, i + 6)
        ):
            out.append(text[i : i + 6])
            i += 6
            continue
        # Invalid escape (LaTeX command, lone backslash, truncated \\uXXXX).
        out.append("\\\\")
        i += 1
    return "".join(out)


def _parse_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise LLMResponseError("confidence must be a number")
    return min(max(float(value), 0.0), 1.0)
