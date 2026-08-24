"""Tests for LLM contract validation."""

import pytest

from rag_based_on_obsidian.llm.contracts import LLMMessage, LLMMetadata, LLMResult


def test_llm_metadata_rejects_empty_model() -> None:
    with pytest.raises(ValueError, match="model"):
        LLMMetadata(provider="openrouter", model="  ")


def test_llm_message_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="role"):
        LLMMessage(role="tool", content="hi")


def test_llm_result_rejects_empty_content() -> None:
    with pytest.raises(ValueError, match="content"):
        LLMResult(content=" ", model="openai/gpt-4o-mini", latency_ms=1)
