"""Contracts for one RAGAS generation-eval example and dataset averages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PackedContext:
    """One packed chunk the generate model actually saw."""

    chunk_id: int
    note_path: str
    text: str


@dataclass(frozen=True)
class RagasItemMetrics:
    """Four v1 metrics for one gold question, or a skip.

    Faithfulness and answer_relevancy are JSON-judge integers 0–5.
    Context precision/recall stay in [0, 1] (note-level proxy).
    """

    item_id: str
    skipped: bool
    skip_reason: str | None = None
    faithfulness: int | None = None
    answer_relevancy: int | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    refused: bool = False
    model: str | None = None
    latency_ms: int | None = None
    prompt_tokens: int | None = None
    generated_tokens: int | None = None
    packed_note_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class RagasDatasetMetrics:
    """Macro-average over scored (non-skipped) generation-eval items."""

    question_count: int
    scored_count: int
    skipped_count: int
    refused_count: int
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    mean_latency_ms: float | None = None
    notes_processed: int = 0
    total_prompt_tokens: int = 0
    mean_prompt_tokens: float | None = None
    median_prompt_tokens: float | None = None
    total_generated_tokens: int = 0
    mean_generated_tokens: float | None = None
    median_generated_tokens: float | None = None


SCORED_RAGAS_FIELDS: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)
