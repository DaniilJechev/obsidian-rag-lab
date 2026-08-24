"""LLM provider contracts, OpenRouter adapter, and RAG generate pipeline."""

from rag_based_on_obsidian.llm.contracts import (
    LLMMessage,
    LLMMetadata,
    LLMProvider,
    LLMResponseError,
    LLMResult,
    LLMUnavailableError,
    LLMUsage,
)
from rag_based_on_obsidian.llm.openrouter import OpenRouterLLMProvider
from rag_based_on_obsidian.llm.pipeline import run_rag_generate
from rag_based_on_obsidian.llm.settings import LLMConfig, load_llm_config

__all__ = [
    "LLMConfig",
    "LLMMessage",
    "LLMMetadata",
    "LLMProvider",
    "LLMResponseError",
    "LLMResult",
    "LLMUnavailableError",
    "LLMUsage",
    "OpenRouterLLMProvider",
    "load_llm_config",
    "run_rag_generate",
]
