import asyncio
import json

import pytest

from rag_based_on_obsidian.eval.judge import OpenRouterJsonJudge, _parse_judge_json
from rag_based_on_obsidian.eval.ragas.ragas_contracts import PackedContext
from rag_based_on_obsidian.llm.contracts import (
    LLMMessage,
    LLMMetadata,
    LLMResult,
    LLMUnavailableError,
)


def test_parse_judge_json_reads_integer_scores() -> None:
    faithfulness, relevancy = _parse_judge_json(
        '{"faithfulness": 3, "answer_relevancy": 5}'
    )
    assert faithfulness == 3
    assert relevancy == 5
    assert isinstance(faithfulness, int)
    assert isinstance(relevancy, int)


def test_parse_judge_json_accepts_whole_float() -> None:
    faithfulness, relevancy = _parse_judge_json(
        '{"faithfulness": 4.0, "answer_relevancy": 0.0}'
    )
    assert faithfulness == 4
    assert relevancy == 0


def test_parse_judge_json_rejects_fraction() -> None:
    with pytest.raises(LLMUnavailableError, match="must be an integer"):
        _parse_judge_json('{"faithfulness": 0.5, "answer_relevancy": 5}')


def test_parse_judge_json_rejects_out_of_range() -> None:
    with pytest.raises(LLMUnavailableError, match="from 0 to 5"):
        _parse_judge_json('{"faithfulness": 6, "answer_relevancy": 0}')


def test_openrouter_json_judge_sends_contexts() -> None:
    captured: list[list[LLMMessage]] = []

    class _FakeProvider:
        async def generate(self, messages: list[LLMMessage]) -> LLMResult:
            captured.append(list(messages))
            return LLMResult(
                content=json.dumps({"faithfulness": 4, "answer_relevancy": 2}),
                model="openai/gpt-4o-mini",
                latency_ms=1,
            )

        @property
        def metadata(self) -> LLMMetadata:
            return LLMMetadata(provider="fake", model="openai/gpt-4o-mini")

    judge = OpenRouterJsonJudge(_FakeProvider())
    faithfulness, relevancy = asyncio.run(
        judge.score(
            question="What is dropout?",
            answer="Dropout randomly disables neurons.",
            contexts=[
                PackedContext(
                    chunk_id=1,
                    note_path="DLS1/Dropout.md",
                    text="Dropout.",
                )
            ],
        )
    )
    assert faithfulness == 4
    assert relevancy == 2
    assert "DLS1/Dropout.md" in captured[0][1].content
    assert "integer 0, 1, 2, 3, 4, or 5" in captured[0][0].content
