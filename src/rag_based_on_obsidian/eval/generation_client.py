"""HTTP client for live ``POST /generate``. Measures the running API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from rag_based_on_obsidian.eval.ragas_contracts import PackedContext
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


class GenerateApiError(Exception):
    """The generate API returned an error or an unexpected payload."""


@dataclass(frozen=True)
class GenerateCallResult:
    """One ``/generate`` JSON body plus HTTP outcome."""

    query: str
    method: str
    top_k: int
    answer: str | None
    refused: bool
    refusal_reason: str | None
    model: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    generated_tokens: int | None
    contexts: tuple[PackedContext, ...]
    citations: tuple[tuple[int, str], ...]


async def call_generate(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    query: str,
    method: RetrievalMethod,
    top_k: int,
    model: str | None = None,
) -> GenerateCallResult:
    """POST one generate request. Raises ``GenerateApiError`` on HTTP failure."""
    url = f"{base_url.rstrip('/')}/generate"
    body: dict[str, object] = {
        "query": query,
        "method": method.value,
        "top_k": top_k,
    }
    if model is not None and model.strip():
        body["model"] = model.strip()
    try:
        response = await client.post(url, json=body)
    except httpx.TimeoutException as exc:
        raise GenerateApiError("generate API timed out") from exc
    except httpx.HTTPError as exc:
        raise GenerateApiError("generate API is unreachable") from exc
    if response.status_code >= 400:
        detail = _error_detail(response)
        raise GenerateApiError(
            f"generate API failed ({response.status_code}): {detail}"
        )
    try:
        response_body: Any = response.json()
    except ValueError as exc:
        raise GenerateApiError("generate API returned non-JSON") from exc
    if not isinstance(response_body, dict):
        raise GenerateApiError("generate API returned an unexpected payload")
    return _parse_generate_body(response_body, query=query)


def _parse_generate_body(body: dict[str, Any], *, query: str) -> GenerateCallResult:
    refused = bool(body.get("refused"))
    usage = body.get("usage")
    prompt_tokens = None
    generated_tokens = None
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens")
        generated = usage.get("generated_tokens")
        if isinstance(prompt, int):
            prompt_tokens = prompt
        if isinstance(generated, int):
            generated_tokens = generated
    contexts = tuple(_parse_contexts(body.get("contexts")))
    citations_raw = body.get("citations")
    citations: list[tuple[int, str]] = []
    if isinstance(citations_raw, list):
        for item in citations_raw:
            if not isinstance(item, dict):
                continue
            chunk_id = item.get("chunk_id")
            note_path = item.get("note_path")
            if isinstance(chunk_id, int) and isinstance(note_path, str):
                citations.append((chunk_id, note_path))
    answer = body.get("answer")
    model = body.get("model")
    latency = body.get("latency_ms")
    method = body.get("method")
    top_k = body.get("top_k")
    return GenerateCallResult(
        query=query,
        method=method if isinstance(method, str) else "hybrid",
        top_k=top_k if isinstance(top_k, int) else 0,
        answer=answer if isinstance(answer, str) else None,
        refused=refused,
        refusal_reason=(
            body.get("refusal_reason")
            if isinstance(body.get("refusal_reason"), str)
            else None
        ),
        model=model if isinstance(model, str) else None,
        latency_ms=latency if isinstance(latency, int) else None,
        prompt_tokens=prompt_tokens,
        generated_tokens=generated_tokens,
        contexts=contexts,
        citations=tuple(citations),
    )


def _parse_contexts(raw: object) -> list[PackedContext]:
    if not isinstance(raw, list):
        return []
    packed: list[PackedContext] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        note_path = item.get("note_path")
        text = item.get("text")
        if (
            isinstance(chunk_id, int)
            and isinstance(note_path, str)
            and isinstance(text, str)
        ):
            packed.append(
                PackedContext(chunk_id=chunk_id, note_path=note_path, text=text)
            )
    return packed


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return response.text[:200]
