"""Two-pass semantic cache eval against POST /generate."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from statistics import median

import httpx

from rag_based_on_obsidian.eval.cache.cache_yaml import ParaphraseGroup
from rag_based_on_obsidian.eval.generation_client import (
    GenerateApiError,
    GenerateCallResult,
    call_generate,
)
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


@dataclass(frozen=True)
class CacheQueryResult:
    """One generate call annotated with group and pass metadata."""

    group_id: str
    pass_name: str
    query: str
    cache_hit: bool
    cache_similarity: float | None
    cache_matched_query: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    generated_tokens: int | None
    refused: bool
    refusal_reason: str | None
    model: str | None
    answer: str | None


@dataclass(frozen=True)
class CacheEvalSummary:
    """Aggregated cache eval metrics for one run."""

    dataset_version: str
    group_count: int
    canonical_count: int
    paraphrase_count: int
    paraphrase_hits: int
    hit_rate: float
    latency_p50_ms: float
    latency_p95_ms: float
    canonical_latency_p50_ms: float
    pass1_tokens: int
    pass2_tokens: int
    tokens_saved: int
    avg_latency_ms: float
    canonical_avg_latency_ms: float
    paraphrase_avg_latency_ms: float
    paraphrase_hit_avg_latency_ms: float
    paraphrase_miss_avg_latency_ms: float


async def run_cache_eval(
    groups: tuple[ParaphraseGroup, ...],
    *,
    dataset_version: str,
    base_url: str,
    method: RetrievalMethod,
    top_k: int,
    enable_cache: bool,
    timeout_seconds: float = 120.0,
) -> tuple[list[CacheQueryResult], CacheEvalSummary]:
    """Pass 1: canonical queries. Pass 2: paraphrases. Returns rows + summary."""
    if not groups:
        raise ValueError("paraphrase groups must not be empty")
    rows: list[CacheQueryResult] = []
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        for group in groups:
            result = await call_generate(
                client,
                base_url=base_url,
                query=group.canonical,
                method=method,
                top_k=top_k,
                enable_cache=enable_cache,
            )
            rows.append(_row_from_call(group.group_id, "canonical", group.canonical, result))
        for group in groups:
            for paraphrase in group.paraphrases:
                result = await call_generate(
                    client,
                    base_url=base_url,
                    query=paraphrase,
                    method=method,
                    top_k=top_k,
                    enable_cache=enable_cache,
                )
                rows.append(_row_from_call(group.group_id, "paraphrase", paraphrase, result))
    paraphrase_rows = [row for row in rows if row.pass_name == "paraphrase"]
    canonical_rows = [row for row in rows if row.pass_name == "canonical"]
    paraphrase_hits = sum(1 for row in paraphrase_rows if row.cache_hit)
    paraphrase_count = len(paraphrase_rows)
    hit_rate = (paraphrase_hits / paraphrase_count) if paraphrase_count else 0.0
    latencies = [float(row.latency_ms) for row in rows if row.latency_ms is not None]
    canonical_latencies = [
        float(row.latency_ms) for row in canonical_rows if row.latency_ms is not None
    ]
    pass1_tokens = _total_tokens(canonical_rows)
    pass2_tokens = _total_tokens(paraphrase_rows)
    tokens_saved = max(pass1_tokens - pass2_tokens, 0)
    paraphrase_hits_rows = [row for row in paraphrase_rows if row.cache_hit]
    paraphrase_miss_rows = [row for row in paraphrase_rows if not row.cache_hit]
    summary = CacheEvalSummary(
        dataset_version=dataset_version,
        group_count=len(groups),
        canonical_count=len(canonical_rows),
        paraphrase_count=paraphrase_count,
        paraphrase_hits=paraphrase_hits,
        hit_rate=hit_rate,
        latency_p50_ms=_percentile(latencies, 50),
        latency_p95_ms=_percentile(latencies, 95),
        canonical_latency_p50_ms=_percentile(canonical_latencies, 50),
        pass1_tokens=pass1_tokens,
        pass2_tokens=pass2_tokens,
        tokens_saved=tokens_saved,
        avg_latency_ms=_avg_latency(rows),
        canonical_avg_latency_ms=_avg_latency(canonical_rows),
        paraphrase_avg_latency_ms=_avg_latency(paraphrase_rows),
        paraphrase_hit_avg_latency_ms=_avg_latency(paraphrase_hits_rows),
        paraphrase_miss_avg_latency_ms=_avg_latency(paraphrase_miss_rows),
    )
    return rows, summary


def run_cache_eval_sync(
    groups: tuple[ParaphraseGroup, ...],
    *,
    dataset_version: str,
    base_url: str,
    method: RetrievalMethod,
    top_k: int,
    enable_cache: bool,
    timeout_seconds: float = 120.0,
) -> tuple[list[CacheQueryResult], CacheEvalSummary]:
    """Sync wrapper for CLI entrypoints."""
    return asyncio.run(
        run_cache_eval(
            groups,
            dataset_version=dataset_version,
            base_url=base_url,
            method=method,
            top_k=top_k,
            enable_cache=enable_cache,
            timeout_seconds=timeout_seconds,
        )
    )


def _row_from_call(
    group_id: str,
    pass_name: str,
    query: str,
    result: GenerateCallResult,
) -> CacheQueryResult:
    return CacheQueryResult(
        group_id=group_id,
        pass_name=pass_name,
        query=query,
        cache_hit=result.cache_hit,
        cache_similarity=result.cache_similarity,
        cache_matched_query=result.cache_matched_query,
        latency_ms=result.latency_ms,
        prompt_tokens=result.prompt_tokens,
        generated_tokens=result.generated_tokens,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        model=result.model,
        answer=result.answer,
    )


def _avg_latency(rows: list[CacheQueryResult]) -> float:
    values = [float(row.latency_ms) for row in rows if row.latency_ms is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _total_tokens(rows: list[CacheQueryResult]) -> int:
    total = 0
    for row in rows:
        if row.prompt_tokens is not None:
            total += row.prompt_tokens
        if row.generated_tokens is not None:
            total += row.generated_tokens
    return total


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def median_latency_ms(rows: list[CacheQueryResult]) -> float:
    """Median latency helper for tests."""
    values = [float(row.latency_ms) for row in rows if row.latency_ms is not None]
    return float(median(values)) if values else 0.0


__all__ = [
    "CacheEvalSummary",
    "CacheQueryResult",
    "GenerateApiError",
    "median_latency_ms",
    "run_cache_eval",
    "run_cache_eval_sync",
]
