"""OpenRouter adapter against httpx.MockTransport. No live API key."""

import asyncio
import json

import httpx
import pytest

from rag_based_on_obsidian.llm.contracts import LLMMessage, LLMUnavailableError
from rag_based_on_obsidian.llm.openrouter import OpenRouterLLMProvider
from rag_based_on_obsidian.llm.settings import LLMConfig

_CONFIG = LLMConfig(
    name="test",
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    timeout_seconds=5.0,
)


def _provider(handler: httpx.MockTransport) -> OpenRouterLLMProvider:
    return OpenRouterLLMProvider(
        _CONFIG,
        api_key="test-secret-key",
        transport=handler,
    )


def test_openrouter_parses_chat_completion() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["url"] = str(request.url)
        body = json.loads(request.content.decode())
        captured["model"] = body["model"]
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-4o-mini",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok","citations":[],"confidence":0.5}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    result = asyncio.run(
        provider.generate([LLMMessage(role="user", content="What is RoPE?")])
    )
    assert captured["authorization"] == "Bearer test-secret-key"
    assert captured["url"].endswith("/chat/completions")
    assert captured["model"] == "openai/gpt-4o-mini"
    assert "test-secret-key" not in result.content
    assert result.usage is not None
    assert result.usage.prompt_tokens == 11
    assert result.usage.generated_tokens == 7


def test_openrouter_401_is_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(LLMUnavailableError, match="API key"):
        asyncio.run(provider.generate([LLMMessage(role="user", content="q")]))


def test_openrouter_rejects_empty_key() -> None:
    with pytest.raises(LLMUnavailableError, match="OPENROUTER_API_KEY"):
        OpenRouterLLMProvider(_CONFIG, api_key="  ")
