"""RAGAS-package Faithfulness and Answer Relevancy (native scale 0–1)."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from rag_based_on_obsidian.eval.ragas.ragas_import import import_ragas

# ragas 0.4.3 hard-imports removed Vertex modules; stub before `import ragas`.
import_ragas()

from datasets import Dataset
from langchain_openai import ChatOpenAI
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, faithfulness

from rag_based_on_obsidian.eval.ragas.ragas_contracts import PackedContext
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError
from rag_based_on_obsidian.llm.settings import LLMConfig

EvaluateFn = Callable[..., Any]


class RagasFrameworkJudge:
    """One ragas ``evaluate()`` call per question. Scores stay in [0, 1]."""

    def __init__(
        self,
        *,
        llm: Any,
        embeddings: Any,
        evaluate_fn: EvaluateFn,
        metrics: Sequence[Any],
    ) -> None:
        self._llm = llm
        self._embeddings = embeddings
        self._evaluate = evaluate_fn
        self._metrics = list(metrics)
        self._evaluate_lock = asyncio.Lock()

    @classmethod
    def from_openrouter(
        cls,
        llm_config: LLMConfig,
        api_key: str,
        embeddings: Any,
    ) -> RagasFrameworkJudge:
        """Wire ChatOpenAI → OpenRouter and local embeddings into ragas."""
        if not api_key.strip():
            raise LLMUnavailableError("OPENROUTER_API_KEY is not configured")
        chat = ChatOpenAI(
            model=llm_config.model,
            api_key=api_key.strip(),
            base_url=llm_config.base_url.rstrip("/"),
            temperature=llm_config.temperature,
            timeout=max(float(llm_config.timeout_seconds), 90.0),
            default_headers=_openrouter_headers(llm_config),
        )
        return cls(
            llm=LangchainLLMWrapper(chat),
            embeddings=LangchainEmbeddingsWrapper(embeddings),
            evaluate_fn=evaluate,
            metrics=(type(faithfulness)(), type(answer_relevancy)()),
        )

    async def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[PackedContext],
    ) -> tuple[float, float]:
        """Return (faithfulness, answer_relevancy) in [0, 1]."""
        dataset = _single_turn_dataset(question, answer, contexts)
        metrics = _fresh_metrics(self._metrics)
        async with self._evaluate_lock:
            try:
                result = await asyncio.to_thread(
                    self._evaluate,
                    dataset,
                    metrics=metrics,
                    llm=self._llm,
                    embeddings=self._embeddings,
                )
            except LLMUnavailableError:
                raise
            except Exception as exc:
                raise LLMUnavailableError("ragas evaluate failed") from exc
        return _parse_ragas_scores(result)


def dump_ragas_metric_prompts() -> str:
    """Serialize default ragas Faithfulness / Answer Relevancy prompt templates."""
    blocks: list[str] = [
        "backend=ragas",
        (
            "These are the package default prompt templates used by "
            "faithfulness and answer_relevancy (not our JSON Likert judge)."
        ),
        "",
    ]
    for label, metric in (
        ("faithfulness", type(faithfulness)()),
        ("answer_relevancy", type(answer_relevancy)()),
    ):
        blocks.append(f"=== {label} ===")
        getter = getattr(metric, "get_prompts", None)
        if not callable(getter):
            blocks.append("(get_prompts unavailable)")
            blocks.append("")
            continue
        try:
            prompts = getter()
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            blocks.append(f"(failed to read prompts: {exc})")
            blocks.append("")
            continue
        if isinstance(prompts, Mapping):
            for key, value in prompts.items():
                blocks.append(f"--- {key} ---")
                blocks.append(str(value))
                blocks.append("")
        else:
            blocks.append(str(prompts))
            blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def _fresh_metrics(metrics: Sequence[Any]) -> list[Any]:
    """New metric instances per evaluate(). Shared ragas singletons race on .llm."""
    fresh: list[Any] = []
    for metric in metrics:
        metric_cls = type(metric)
        if metric_cls is str:
            fresh.append(metric)
            continue
        try:
            fresh.append(metric_cls())
        except TypeError:
            fresh.append(metric)
    return fresh


def _openrouter_headers(llm_config: LLMConfig) -> dict[str, str]:
    headers: dict[str, str] = {}
    if llm_config.http_referer.strip():
        headers["HTTP-Referer"] = llm_config.http_referer.strip()
    if llm_config.app_title.strip():
        headers["X-Title"] = llm_config.app_title.strip()
    return headers


def _single_turn_dataset(
    question: str,
    answer: str,
    contexts: Sequence[PackedContext],
) -> Any:
    context_texts = [item.text for item in contexts if item.text.strip()]
    if not context_texts:
        context_texts = [""]
    return Dataset.from_dict(
        {
            "question": [question],
            "user_input": [question],
            "answer": [answer],
            "response": [answer],
            "contexts": [context_texts],
            "retrieved_contexts": [context_texts],
        }
    )


def _parse_ragas_scores(result: object) -> tuple[float, float]:
    mapping = _result_mapping(result)
    faithfulness = _unit_score(mapping, "faithfulness")
    relevancy = _unit_score(
        mapping,
        "answer_relevancy",
        "answer_relevance",
    )
    return faithfulness, relevancy


def _result_mapping(result: object) -> Mapping[str, Any]:
    if isinstance(result, dict):
        return result
    scores = getattr(result, "scores", None)
    if isinstance(scores, list) and scores and isinstance(scores[0], dict):
        return scores[0]
    to_pandas = getattr(result, "to_pandas", None)
    if callable(to_pandas):
        frame = to_pandas()
        row = frame.iloc[0]
        return {str(column): row[column] for column in frame.columns}
    raise LLMUnavailableError("ragas returned an unexpected payload")


def _unit_score(mapping: Mapping[str, Any], *keys: str) -> float:
    value: object = None
    for key in keys:
        if key in mapping:
            value = mapping[key]
            break
    if isinstance(value, bool):
        raise LLMUnavailableError("ragas score must be a number")
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise LLMUnavailableError("ragas score must be a number") from exc
    if math.isnan(score) or score < 0.0 or score > 1.0:
        raise LLMUnavailableError("ragas score must be in [0, 1]")
    return score
