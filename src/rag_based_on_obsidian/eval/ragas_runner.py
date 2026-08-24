"""Run generation eval: HTTP generate, note-level proxy, LLM judge."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from statistics import mean, median

import httpx
from tqdm import tqdm

from rag_based_on_obsidian.eval.context_proxy import (
    context_precision,
    context_recall,
    unique_note_paths,
)
from rag_based_on_obsidian.eval.contracts import GoldItem
from rag_based_on_obsidian.eval.generation_client import (
    GenerateApiError,
    call_generate,
)
from rag_based_on_obsidian.eval.judge import GenerationJudge
from rag_based_on_obsidian.eval.progress import EvalProgress, eval_tqdm
from rag_based_on_obsidian.eval.ragas_contracts import (
    SCORED_RAGAS_FIELDS,
    RagasDatasetMetrics,
    RagasItemMetrics,
)
from rag_based_on_obsidian.eval.ragas_settings import RagasRunConfig
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError


def select_gold_slice(
    items: Sequence[GoldItem],
    config: RagasRunConfig,
) -> tuple[GoldItem, ...]:
    """Take YAML order: subset_size items, or the full gold list."""
    if not items:
        raise ValueError("gold items must not be empty")
    if config.full_set:
        return tuple(items)
    if config.subset_size > len(items):
        raise ValueError(
            f"subset_size {config.subset_size} exceeds gold size {len(items)}"
        )
    return tuple(items[: config.subset_size])


async def run_ragas_eval(
    items: Sequence[GoldItem],
    config: RagasRunConfig,
    judge: GenerationJudge,
    *,
    progress: EvalProgress | None = None,
    client: httpx.AsyncClient | None = None,
) -> tuple[RagasDatasetMetrics, list[dict[str, object]]]:
    """Generate via the API, then score each item. One failed item is a skip."""
    own_client = client is None
    http_client = client or httpx.AsyncClient(
        timeout=config.generate_timeout_seconds,
    )
    semaphore = asyncio.Semaphore(config.concurrency)
    bar = (
        eval_tqdm(total=len(items), desc="ragas questions", unit="q")
        if progress is not None
        else None
    )
    counts = {"scored": 0, "skipped": 0}

    async def tracked(item: GoldItem) -> tuple[RagasItemMetrics, dict[str, object]]:
        row = await _score_one(
            item,
            config=config,
            judge=judge,
            client=http_client,
            semaphore=semaphore,
        )
        if bar is not None:
            if row[0].skipped:
                counts["skipped"] += 1
            else:
                counts["scored"] += 1
            bar.update(1)
            bar.set_postfix(
                scored=counts["scored"],
                skipped=counts["skipped"],
                last=row[0].item_id,
            )
        return row

    try:
        scored = await asyncio.gather(*[tracked(item) for item in items])
    finally:
        if bar is not None:
            bar.close()
        if own_client:
            await http_client.aclose()
    results = [row[0] for row in scored]
    artifacts = [row[1] for row in scored]
    if progress is not None:
        skip_summary = _skip_reason_summary(results)
        progress.mark(
            "score_items",
            questions=len(results),
            skipped=sum(1 for row in results if row.skipped),
            **({"skip_reasons": skip_summary} if skip_summary else {}),
        )
        if skip_summary:
            tqdm.write(f"skip_reasons: {skip_summary}")
    return _macro_average(results), artifacts


def _skip_reason_summary(results: Sequence[RagasItemMetrics]) -> str:
    """Compact skip reasons for stderr, e.g. 'openrouter rejected the API key×12'."""
    reasons = Counter(row.skip_reason or "unknown" for row in results if row.skipped)
    if not reasons:
        return ""
    return "; ".join(f"{reason}×{count}" for reason, count in reasons.most_common(3))


async def _score_one(
    item: GoldItem,
    *,
    config: RagasRunConfig,
    judge: GenerationJudge,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> tuple[RagasItemMetrics, dict[str, object]]:
    async with semaphore:
        try:
            generated = await call_generate(
                client,
                base_url=config.api_base_url,
                query=item.question,
                method=config.method,
                top_k=config.top_k,
            )
        except GenerateApiError as exc:
            metrics = RagasItemMetrics(
                item_id=item.item_id,
                skipped=True,
                skip_reason=str(exc),
                packed_note_paths=(),
            )
            return metrics, _artifact(item, metrics, packed_paths=())

    packed_paths = tuple(context.note_path for context in generated.contexts)
    packed_contexts = tuple(
        {
            "chunk_id": context.chunk_id,
            "note_path": context.note_path,
            "text": context.text,
        }
        for context in generated.contexts
    )
    if generated.refused or generated.answer is None or not generated.answer.strip():
        metrics = RagasItemMetrics(
            item_id=item.item_id,
            skipped=True,
            skip_reason=generated.refusal_reason or "refused or empty answer",
            refused=True,
            model=generated.model,
            latency_ms=generated.latency_ms,
            prompt_tokens=generated.prompt_tokens,
            generated_tokens=generated.generated_tokens,
            packed_note_paths=unique_note_paths(packed_paths),
        )
        return metrics, _artifact(
            item,
            metrics,
            packed_paths=packed_paths,
            answer=generated.answer,
            contexts=packed_contexts,
        )

    try:
        precision = context_precision(packed_paths, item.relevant_note_paths)
        recall = context_recall(packed_paths, item.relevant_note_paths)
        faithfulness, relevancy = await judge.score(
            question=item.question,
            answer=generated.answer,
            contexts=generated.contexts,
        )
    except (LLMUnavailableError, ValueError) as exc:
        metrics = RagasItemMetrics(
            item_id=item.item_id,
            skipped=True,
            skip_reason=str(exc),
            refused=False,
            model=generated.model,
            latency_ms=generated.latency_ms,
            prompt_tokens=generated.prompt_tokens,
            generated_tokens=generated.generated_tokens,
            packed_note_paths=unique_note_paths(packed_paths),
        )
        return metrics, _artifact(
            item,
            metrics,
            packed_paths=packed_paths,
            answer=generated.answer,
            contexts=packed_contexts,
        )

    metrics = RagasItemMetrics(
        item_id=item.item_id,
        skipped=False,
        faithfulness=faithfulness,
        answer_relevancy=relevancy,
        context_precision=precision,
        context_recall=recall,
        refused=False,
        model=generated.model,
        latency_ms=generated.latency_ms,
        prompt_tokens=generated.prompt_tokens,
        generated_tokens=generated.generated_tokens,
        packed_note_paths=unique_note_paths(packed_paths),
    )
    return metrics, _artifact(
        item,
        metrics,
        packed_paths=packed_paths,
        answer=generated.answer,
        contexts=packed_contexts,
    )


def _macro_average(results: Sequence[RagasItemMetrics]) -> RagasDatasetMetrics:
    scored = [row for row in results if not row.skipped]
    skipped = [row for row in results if row.skipped]
    refused_count = sum(1 for row in results if row.refused)
    averages: dict[str, float | None] = {}
    for field in SCORED_RAGAS_FIELDS:
        values = [
            getattr(row, field)
            for row in scored
            if getattr(row, field) is not None
        ]
        averages[field] = mean(values) if values else None
    latencies = [row.latency_ms for row in scored if row.latency_ms is not None]
    prompt_values = [
        row.prompt_tokens for row in results if row.prompt_tokens is not None
    ]
    generated_values = [
        row.generated_tokens for row in results if row.generated_tokens is not None
    ]
    notes = unique_note_paths(
        [path for row in results for path in row.packed_note_paths]
    )
    prompt_total, prompt_mean, prompt_median = _token_stats(prompt_values)
    generated_total, generated_mean, generated_median = _token_stats(
        generated_values
    )
    return RagasDatasetMetrics(
        question_count=len(results),
        scored_count=len(scored),
        skipped_count=len(skipped),
        refused_count=refused_count,
        faithfulness=averages["faithfulness"],
        answer_relevancy=averages["answer_relevancy"],
        context_precision=averages["context_precision"],
        context_recall=averages["context_recall"],
        mean_latency_ms=mean(latencies) if latencies else None,
        notes_processed=len(notes),
        total_prompt_tokens=prompt_total,
        mean_prompt_tokens=prompt_mean,
        median_prompt_tokens=prompt_median,
        total_generated_tokens=generated_total,
        mean_generated_tokens=generated_mean,
        median_generated_tokens=generated_median,
    )


def _token_stats(
    values: Sequence[int],
) -> tuple[int, float | None, float | None]:
    """Return total, mean and median. Empty → zeros / None."""
    if not values:
        return 0, None, None
    return sum(values), float(mean(values)), float(median(values))


def _artifact(
    item: GoldItem,
    metrics: RagasItemMetrics,
    *,
    packed_paths: tuple[str, ...],
    answer: str | None = None,
    contexts: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "question": item.question,
        "answer": answer,
        "skipped": metrics.skipped,
        "skip_reason": metrics.skip_reason,
        "refused": metrics.refused,
        "packed_paths": list(packed_paths),
        "relevant_paths": list(item.relevant_note_paths),
        "contexts": [dict(context) for context in contexts],
        "faithfulness": metrics.faithfulness,
        "answer_relevancy": metrics.answer_relevancy,
        "context_precision": metrics.context_precision,
        "context_recall": metrics.context_recall,
        "model": metrics.model,
        "latency_ms": metrics.latency_ms,
        "prompt_tokens": metrics.prompt_tokens,
        "generated_tokens": metrics.generated_tokens,
    }
