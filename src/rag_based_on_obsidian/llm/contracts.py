"""Provider boundary for chat LLMs. HTTP details stay in the adapter."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class LLMUnavailableError(Exception):
    """The provider cannot be reached, authenticated, or scheduled."""


class LLMResponseError(Exception):
    """The provider returned a body that is not usable structured output."""


@dataclass(frozen=True)
class LLMMetadata:
    """Identity of one configured chat model."""

    provider: str
    model: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")


@dataclass(frozen=True)
class LLMMessage:
    """One chat message in provider-neutral form."""

    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise ValueError("role must be system, user, or assistant")
        if not self.content.strip():
            raise ValueError("content must not be empty")


@dataclass(frozen=True)
class LLMUsage:
    """Token counts reported by the provider for one call."""

    prompt_tokens: int
    generated_tokens: int

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens must be non-negative")
        if self.generated_tokens < 0:
            raise ValueError("generated_tokens must be non-negative")


@dataclass(frozen=True)
class LLMResult:
    """One completed generation: raw text plus optional usage."""

    content: str
    model: str
    latency_ms: int
    usage: LLMUsage | None = None

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("content must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")


class LLMProvider(Protocol):
    """Swap OpenRouter for vLLM later without rewriting the RAG packer."""

    @property
    def metadata(self) -> LLMMetadata:
        """Return the configured provider and model id."""

    async def generate(
        self,
        messages: Sequence[LLMMessage],
    ) -> LLMResult:
        """Complete one chat request. Raise unavailable/response errors."""
