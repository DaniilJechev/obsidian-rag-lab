"""Token budget ablation: budgets × gold subset via POST /generate."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from statistics import mean, median

import httpx

from rag_based_on_obsidian.eval.context_proxy import unique_note_paths
from rag_based_on_obsidian.eval.contracts import GoldItem
from rag_based_on_obsidian.eval.generation_client import (
    GenerateApiError,
    call_generate,
)
from rag_based_on_obsidian.eval.judge import GenerationJudge
from rag_based_on_obsidian.eval.metrics import mrr_at_k, ndcg_at_k
from rag_based_on_obsidian.eval.token_budget.budget_yaml import BudgetRunConfig
from rag_based_on_obsidian.llm.contracts import LLMUnavailableError

_GATE_EST_TOKENS = re.compile(r"est_tokens=(\d+)")
_GATE_PACKED = re.compile(r"packed=(\d+)")


@dataclass(frozen=True)
class BudgetQueryResult:
    """One generate call at a fixed max_context_tokens budget."""

    item_id: str
    budget: int
    query: str
    prompt_tokens: int | None
    generated_tokens: int | None
    latency_ms: int | None
    packed_chunks: int
    est_tokens: int | None
    refused: bool
    refusal_reason: str | None
    model: str | None
    answer: str | None
    packed_note_paths: tuple[str, ...]
    ndcg_at_k: float | None
    mrr_at_k: float | None
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    skipped: bool = False
    skip_reason: str | None = None
    gate_trace: str | None = None


@dataclass(frozen=True)
class BudgetEvalSummary:
    """Aggregated metrics for one budget value."""

    budget: int
    question_count: int
    scored_count: int
    skipped_count: int
    refused_count: int
    mean_prompt_tokens: float | None
    median_prompt_tokens: float | None
    p95_prompt_tokens: float | None
    mean_generated_tokens: float | None
    mean_latency_ms: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    mean_packed_chunks: float | None
    mean_est_tokens: float | None
    mean_ndcg_at_k: float | None
    mean_mrr_at_k: float | None
    mean_faithfulness: float | None
    mean_answer_relevancy: float | None
    refusal_rate: float


async def run_budget_eval(
    items: tuple[GoldItem, ...],
    config: BudgetRunConfig,
    *,
    budgets: tuple[int, ...] | None = None,
    judge: GenerationJudge | None = None,
    ragas_enabled: bool | None = None,
) -> dict[int, tuple[list[BudgetQueryResult], BudgetEvalSummary]]:
    """Run budget grid. Returns {budget: (rows, summary)}."""
    if not items:
        raise ValueError("gold items must not be empty")
    budget_values = budgets or config.budgets
    if not budget_values:
        raise ValueError("budgets must not be empty")
    use_ragas = config.ragas_enabled if ragas_enabled is None else ragas_enabled
    if use_ragas and judge is None:
        raise ValueError("ragas_enabled requires a judge")
    results: dict[int, tuple[list[BudgetQueryResult], BudgetEvalSummary]] = {}
    async with httpx.AsyncClient(timeout=config.generate_timeout_seconds) as client:
        semaphore = asyncio.Semaphore(config.concurrency)
        for budget in budget_values:
            rows = await asyncio.gather(
                *[
                    _score_one(
                        item,
                        budget=budget,
                        config=config,
                        client=client,
                        semaphore=semaphore,
                        judge=judge if use_ragas else None,
                    )
                    for item in items
                ]
            )
            results[budget] = (list(rows), _summarize(budget, rows))
    return results


def run_budget_eval_sync(
    items: tuple[GoldItem, ...],
    config: BudgetRunConfig,
    *,
    budgets: tuple[int, ...] | None = None,
    judge: GenerationJudge | None = None,
    ragas_enabled: bool | None = None,
) -> dict[int, tuple[list[BudgetQueryResult], BudgetEvalSummary]]:
    """Sync wrapper for CLI entrypoints."""
    return asyncio.run(
        run_budget_eval(
            items,
            config,
            budgets=budgets,
            judge=judge,
            ragas_enabled=ragas_enabled,
        )
    )


async def _score_one(
    item: GoldItem,
    *,
    budget: int,
    config: BudgetRunConfig,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    judge: GenerationJudge | None,
) -> BudgetQueryResult:
    async with semaphore:
        try:
            generated = await call_generate(
                client,
                base_url=config.api_base_url,
                query=item.question,
                method=config.method,
                top_k=config.top_k,
                model=config.generate_model,
                enable_cache=config.enable_cache,
                max_context_tokens=budget,
            )
        except GenerateApiError as exc:
            return BudgetQueryResult(
                item_id=item.item_id,
                budget=budget,
                query=item.question,
                prompt_tokens=None,
                generated_tokens=None,
                latency_ms=None,
                packed_chunks=0,
                est_tokens=None,
                refused=False,
                refusal_reason=None,
                model=None,
                answer=None,
                packed_note_paths=(),
                ndcg_at_k=None,
                mrr_at_k=None,
                skipped=True,
                skip_reason=str(exc),
            )

    packed_paths = tuple(context.note_path for context in generated.contexts)
    unique_paths = unique_note_paths(packed_paths)
    gate_trace = _gate_trace_snippet(generated.graph_trace)
    est_tokens = _parse_gate_est_tokens(gate_trace)
    packed_count = _parse_gate_packed(gate_trace) or len(generated.contexts)
    ndcg = mrr = None
    if unique_paths and item.relevant_note_paths:
        ndcg = ndcg_at_k(unique_paths, item.relevant_note_paths, config.top_k)
        mrr = mrr_at_k(unique_paths, item.relevant_note_paths, config.top_k)

    faithfulness: float | None = None
    relevancy: float | None = None
    skipped = False
    skip_reason: str | None = None

    if generated.refused or generated.answer is None or not generated.answer.strip():
        return BudgetQueryResult(
            item_id=item.item_id,
            budget=budget,
            query=item.question,
            prompt_tokens=generated.prompt_tokens,
            generated_tokens=generated.generated_tokens,
            latency_ms=generated.latency_ms,
            packed_chunks=packed_count,
            est_tokens=est_tokens,
            refused=True,
            refusal_reason=generated.refusal_reason or "refused or empty answer",
            model=generated.model,
            answer=generated.answer,
            packed_note_paths=unique_paths,
            ndcg_at_k=ndcg,
            mrr_at_k=mrr,
            skipped=False,
            gate_trace=gate_trace,
        )

    if judge is not None:
        try:
            faithfulness, relevancy = await judge.score(
                question=item.question,
                answer=generated.answer,
                contexts=generated.contexts,
            )
        except (LLMUnavailableError, ValueError) as exc:
            skipped = True
            skip_reason = str(exc)

    return BudgetQueryResult(
        item_id=item.item_id,
        budget=budget,
        query=item.question,
        prompt_tokens=generated.prompt_tokens,
        generated_tokens=generated.generated_tokens,
        latency_ms=generated.latency_ms,
        packed_chunks=packed_count,
        est_tokens=est_tokens,
        refused=False,
        refusal_reason=None,
        model=generated.model,
        answer=generated.answer,
        packed_note_paths=unique_paths,
        ndcg_at_k=ndcg,
        mrr_at_k=mrr,
        faithfulness=faithfulness,
        answer_relevancy=relevancy,
        skipped=skipped,
        skip_reason=skip_reason,
        gate_trace=gate_trace,
    )


def _summarize(budget: int, rows: list[BudgetQueryResult]) -> BudgetEvalSummary:
    question_count = len(rows)
    skipped = [row for row in rows if row.skipped]
    refused = [row for row in rows if row.refused and not row.skipped]
    scored = [row for row in rows if not row.skipped and not row.refused]
    prompt_values = [
        float(row.prompt_tokens)
        for row in rows
        if row.prompt_tokens is not None and not row.skipped
    ]
    generated_values = [
        float(row.generated_tokens)
        for row in rows
        if row.generated_tokens is not None and not row.skipped
    ]
    latency_values = [
        float(row.latency_ms)
        for row in rows
        if row.latency_ms is not None and not row.skipped
    ]
    packed_values = [
        float(row.packed_chunks) for row in rows if not row.skipped
    ]
    est_values = [
        float(row.est_tokens)
        for row in rows
        if row.est_tokens is not None and not row.skipped
    ]
    ndcg_values = [
        row.ndcg_at_k for row in scored if row.ndcg_at_k is not None
    ]
    mrr_values = [row.mrr_at_k for row in scored if row.mrr_at_k is not None]
    faith_values = [
        row.faithfulness
        for row in scored
        if row.faithfulness is not None
    ]
    rel_values = [
        row.answer_relevancy
        for row in scored
        if row.answer_relevancy is not None
    ]
    return BudgetEvalSummary(
        budget=budget,
        question_count=question_count,
        scored_count=len(scored),
        skipped_count=len(skipped),
        refused_count=len(refused),
        mean_prompt_tokens=_mean(prompt_values),
        median_prompt_tokens=float(median(prompt_values)) if prompt_values else None,
        p95_prompt_tokens=_percentile(prompt_values, 95),
        mean_generated_tokens=_mean(generated_values),
        mean_latency_ms=_mean(latency_values),
        p50_latency_ms=_percentile(latency_values, 50),
        p95_latency_ms=_percentile(latency_values, 95),
        mean_packed_chunks=_mean(packed_values),
        mean_est_tokens=_mean(est_values),
        mean_ndcg_at_k=_mean(ndcg_values),
        mean_mrr_at_k=_mean(mrr_values),
        mean_faithfulness=_mean(faith_values),
        mean_answer_relevancy=_mean(rel_values),
        refusal_rate=(len(refused) / question_count) if question_count else 0.0,
    )


def _mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _gate_trace_snippet(graph_trace: tuple[dict[str, str], ...] | None) -> str | None:
    if not graph_trace:
        return None
    for entry in graph_trace:
        if entry.get("node") == "gate":
            return entry.get("reason")
    return None


def _parse_gate_est_tokens(reason: str | None) -> int | None:
    if reason is None:
        return None
    match = _GATE_EST_TOKENS.search(reason)
    return int(match.group(1)) if match else None


def _parse_gate_packed(reason: str | None) -> int | None:
    if reason is None:
        return None
    match = _GATE_PACKED.search(reason)
    return int(match.group(1)) if match else None
