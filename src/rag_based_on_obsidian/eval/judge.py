"""LLM-as-judge for Faithfulness and Answer Relevancy (RAGAS v1 axes)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Protocol

from rag_based_on_obsidian.eval.ragas_contracts import PackedContext
from rag_based_on_obsidian.llm.contracts import (
    LLMMessage,
    LLMProvider,
    LLMUnavailableError,
)

JUDGE_SYSTEM = (
    "You are a strict RAG evaluator. Use only the given question, answer, and "
    "contexts. Return a JSON object with keys faithfulness and answer_relevancy. "
    "Each value MUST be an integer 0, 1, 2, 3, 4, or 5 — never a fraction. "
    "faithfulness: 0 = the answer invents facts or ignores the contexts; "
    "5 = every claim is supported by the contexts. "
    "answer_relevancy: 0 = the answer does not address the question; "
    "5 = the answer directly and fully addresses the question. "
    "Do not add other keys."
)


class GenerationJudge(Protocol):
    """Score one generated answer against packed contexts."""

    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[PackedContext],
    ) -> tuple[float, float]:
        """Return (faithfulness, answer_relevancy).

        JSON backend: integers 0–5. Ragas backend: floats in [0, 1].
        Never rescale one scale into the other.
        """


class OpenRouterJsonJudge:
    """One JSON completion on OpenRouter; metric names match RAGAS v1."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[PackedContext],
    ) -> tuple[int, int]:
        blocks = [
            f"Question: {question.strip()}",
            f"Answer: {answer.strip()}",
            "Contexts:",
        ]
        if contexts:
            for item in contexts:
                blocks.append(f"[{item.note_path}]\n{item.text}")
        else:
            blocks.append("(none)")
        result = await self._provider.generate(
            [
                LLMMessage(role="system", content=JUDGE_SYSTEM),
                LLMMessage(role="user", content="\n\n".join(blocks)),
            ]
        )
        return _parse_judge_json(result.content)


def _parse_judge_json(content: str) -> tuple[int, int]:
    try:
        payload: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMUnavailableError("judge returned non-JSON") from exc
    if not isinstance(payload, dict):
        raise LLMUnavailableError("judge returned an unexpected payload")
    faithfulness = _likert_score(payload.get("faithfulness"), "faithfulness")
    relevancy = _likert_score(payload.get("answer_relevancy"), "answer_relevancy")
    return faithfulness, relevancy


def _likert_score(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMUnavailableError(f"judge {name} must be an integer")
    if isinstance(value, float) and not value.is_integer():
        raise LLMUnavailableError(f"judge {name} must be an integer")
    score = int(value)
    if score < 0 or score > 5:
        raise LLMUnavailableError(f"judge {name} must be an integer from 0 to 5")
    return score
