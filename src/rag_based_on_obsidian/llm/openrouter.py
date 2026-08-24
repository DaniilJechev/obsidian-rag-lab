"""OpenRouter chat completions adapter. The API key never enters logs."""

from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter
from typing import Any

import httpx

from rag_based_on_obsidian.llm.contracts import (
    LLMMessage,
    LLMMetadata,
    LLMResult,
    LLMUnavailableError,
    LLMUsage,
)
from rag_based_on_obsidian.llm.settings import LLMConfig

_CHAT_PATH = "/chat/completions"


class OpenRouterLLMProvider:
    """POST /chat/completions against OpenRouter's OpenAI-compatible API."""

    def __init__(
        self,
        config: LLMConfig,
        *,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise LLMUnavailableError("OPENROUTER_API_KEY is not configured")
        self._config = config
        self._api_key = api_key.strip()
        self._transport = transport

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(provider="openrouter", model=self._config.model)

    async def generate(self, messages: Sequence[LLMMessage]) -> LLMResult:
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._config.http_referer.strip():
            headers["HTTP-Referer"] = self._config.http_referer.strip()
        if self._config.app_title.strip():
            headers["X-Title"] = self._config.app_title.strip()

        url = self._config.base_url.rstrip("/") + _CHAT_PATH
        started = perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError("openrouter timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError("openrouter is unreachable") from exc

        latency_ms = max(int((perf_counter() - started) * 1000), 0)
        if response.status_code in {401, 403}:
            raise LLMUnavailableError("openrouter rejected the API key")
        if response.status_code == 429:
            raise LLMUnavailableError("openrouter rate limit exceeded")
        if response.status_code >= 500:
            raise LLMUnavailableError("openrouter is unavailable")
        if response.status_code >= 400:
            raise LLMUnavailableError(
                f"openrouter request failed ({response.status_code})"
            )
        try:
            body: Any = response.json()
        except ValueError as exc:
            raise LLMUnavailableError("openrouter returned non-JSON") from exc
        return _result_from_body(
            body,
            latency_ms=latency_ms,
            fallback_model=self._config.model,
        )


def _result_from_body(
    body: Any,
    *,
    latency_ms: int,
    fallback_model: str,
) -> LLMResult:
    if not isinstance(body, dict):
        raise LLMUnavailableError("openrouter returned an unexpected payload")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMUnavailableError("openrouter returned no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise LLMUnavailableError("openrouter returned an unexpected choice")
    message = first.get("message")
    if not isinstance(message, dict):
        raise LLMUnavailableError("openrouter returned no message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMUnavailableError("openrouter returned empty content")
    model = body.get("model")
    if isinstance(model, str) and model.strip():
        model_name = model.strip()
    else:
        model_name = fallback_model
    usage = _parse_usage(body.get("usage"))
    return LLMResult(
        content=content,
        model=model_name,
        latency_ms=latency_ms,
        usage=usage,
    )


def _parse_usage(raw: Any) -> LLMUsage | None:
    if not isinstance(raw, dict):
        return None
    prompt = raw.get("prompt_tokens")
    generated = raw.get("completion_tokens")
    if not isinstance(prompt, int) or not isinstance(generated, int):
        return None
    return LLMUsage(prompt_tokens=prompt, generated_tokens=generated)
