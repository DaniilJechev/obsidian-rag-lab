import asyncio
import time

import pytest

from rag_based_on_obsidian.eval.ragas.ragas_contracts import PackedContext
from rag_based_on_obsidian.eval.ragas.ragas_judge import RagasFrameworkJudge
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError


def _contexts() -> list[PackedContext]:
    return [
        PackedContext(
            chunk_id=1,
            note_path="DLS1/Dropout.md",
            text="Dropout randomly drops units.",
        )
    ]


def test_ragas_framework_judge_parses_unit_scores() -> None:
    captured: dict[str, object] = {}

    def fake_evaluate(dataset: object, **kwargs: object) -> dict[str, float]:
        captured["dataset"] = dataset
        captured["kwargs"] = kwargs
        return {"faithfulness": 0.8, "answer_relevancy": 0.4}

    judge = RagasFrameworkJudge(
        llm="llm",
        embeddings="emb",
        evaluate_fn=fake_evaluate,
        metrics=("faithfulness", "answer_relevancy"),
    )
    faithfulness, relevancy = asyncio.run(
        judge.score(
            question="What is dropout?",
            answer="Dropout randomly disables neurons.",
            contexts=_contexts(),
        )
    )
    assert faithfulness == 0.8
    assert relevancy == 0.4
    assert captured["kwargs"]["llm"] == "llm"
    assert captured["kwargs"]["embeddings"] == "emb"


def test_ragas_framework_judge_reads_scores_list() -> None:
    class _Result:
        def __init__(self) -> None:
            self.scores = [{"faithfulness": 0.0, "answer_relevance": 1.0}]

    judge = RagasFrameworkJudge(
        llm=None,
        embeddings=None,
        evaluate_fn=lambda *_a, **_k: _Result(),
        metrics=(),
    )
    faithfulness, relevancy = asyncio.run(
        judge.score(
            question="q",
            answer="a",
            contexts=_contexts(),
        )
    )
    assert faithfulness == 0.0
    assert relevancy == 1.0


def test_ragas_framework_judge_serializes_evaluate() -> None:
    in_flight = 0
    max_in_flight = 0

    def fake_evaluate(*_args: object, **_kwargs: object) -> dict[str, float]:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        time.sleep(0.05)
        in_flight -= 1
        return {"faithfulness": 0.1, "answer_relevancy": 0.2}

    judge = RagasFrameworkJudge(
        llm=None,
        embeddings=None,
        evaluate_fn=fake_evaluate,
        metrics=(),
    )

    async def _both() -> None:
        await asyncio.gather(
            judge.score(question="q1", answer="a1", contexts=_contexts()),
            judge.score(question="q2", answer="a2", contexts=_contexts()),
        )

    asyncio.run(_both())
    assert max_in_flight == 1


def test_ragas_framework_judge_rejects_nan() -> None:
    judge = RagasFrameworkJudge(
        llm=None,
        embeddings=None,
        evaluate_fn=lambda *_a, **_k: {
            "faithfulness": float("nan"),
            "answer_relevancy": 0.5,
        },
        metrics=(),
    )
    with pytest.raises(LLMUnavailableError, match=r"\[0, 1\]"):
        asyncio.run(
            judge.score(
                question="q",
                answer="a",
                contexts=_contexts(),
            )
        )


def test_ragas_framework_judge_rejects_out_of_range() -> None:
    judge = RagasFrameworkJudge(
        llm=None,
        embeddings=None,
        evaluate_fn=lambda *_a, **_k: {"faithfulness": 1.2, "answer_relevancy": 0.5},
        metrics=(),
    )
    with pytest.raises(LLMUnavailableError, match=r"\[0, 1\]"):
        asyncio.run(
            judge.score(
                question="q",
                answer="a",
                contexts=_contexts(),
            )
        )
