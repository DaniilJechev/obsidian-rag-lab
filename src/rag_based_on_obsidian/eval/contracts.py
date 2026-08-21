"""Contracts for gold items, note rankings and metric results."""

from collections.abc import Sequence
from dataclasses import dataclass

from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk


@dataclass(frozen=True)
class GoldItem:
    """One gold question before note_id resolution."""

    item_id: str
    question: str
    corpus_scope: str
    relevant_note_paths: tuple[str, ...]
    dataset_version: str
    source_directory: str
    relevant_chunk_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class RankedNote:
    """One unique note after collapsing a chunk ranking."""

    note_id: int
    rank: int
    source_path: str | None = None


@dataclass(frozen=True)
class QuestionMetrics:
    """Retrieval metrics for one question at a caller-supplied k, or a skip."""

    item_id: str
    skipped: bool
    k: int | None = None
    skip_reason: str | None = None
    ndcg: float | None = None
    mrr: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    hit: float | None = None
    average_precision: float | None = None
    r_precision: float | None = None


@dataclass(frozen=True)
class DatasetMetrics:
    """Macro-average over scored (non-skipped) questions at one k."""

    question_count: int
    scored_count: int
    skipped_count: int
    k: int | None = None
    ndcg: float | None = None
    mrr: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    hit: float | None = None
    average_precision: float | None = None
    r_precision: float | None = None


SCORED_METRIC_FIELDS: tuple[str, ...] = (
    "ndcg",
    "mrr",
    "precision",
    "recall",
    "f1",
    "hit",
    "average_precision",
    "r_precision",
)

_SCORED_METRIC_LOG_BASENAME: dict[str, str] = {
    "ndcg": "ndcg",
    "mrr": "mrr",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "hit": "hit",
    "average_precision": "map",
    "r_precision": "r_precision",
}


def scored_metric_log_name(field: str, k: int | None) -> str:
    """Return the MLflow-safe name, with _at_k for cutoff metrics."""
    base = _SCORED_METRIC_LOG_BASENAME[field]
    if field == "r_precision" or k is None:
        return base
    return f"{base}_at_{k}"


def scored_metrics_for_log(metrics: DatasetMetrics) -> dict[str, float]:
    """Serialize scored fields under names like precision_at_5 and map_at_5."""
    logged: dict[str, float] = {}
    for name in SCORED_METRIC_FIELDS:
        value = getattr(metrics, name)
        if value is None:
            continue
        logged[scored_metric_log_name(name, metrics.k)] = float(value)
    return logged


@dataclass(frozen=True)
class StoredEvalItem:
    """One gold row as stored in PostgreSQL eval_items."""

    eval_item_id: int
    question: str
    corpus_scope: str
    relevant_note_ids: tuple[int, ...]
    dataset_version: str


@dataclass(frozen=True)
class LiveGoldItem:
    """One runtime gold question with note ids, paths and a stable item_id."""

    item_id: str
    eval_item_id: int
    question: str
    relevant_note_ids: tuple[int, ...]
    relevant_note_paths: tuple[str, ...]
    dataset_version: str


def note_id_from_chunk(chunk: RetrievedChunk) -> int:
    """Read the payload note identity used for note-level ranking."""
    value = chunk.metadata.get("note_id")
    if not isinstance(value, int) or value <= 0:
        raise ValueError(
            f"chunk {chunk.chunk_id} is missing a positive metadata note_id"
        )
    return value


def collapse_chunks_to_notes(chunks: Sequence[RetrievedChunk]) -> list[RankedNote]:
    """Keep the first occurrence of each note_id in chunk rank order."""
    ranked: list[RankedNote] = []
    seen: set[int] = set()
    for chunk in chunks:
        note_id = note_id_from_chunk(chunk)
        if note_id in seen:
            continue
        seen.add(note_id)
        source_path = chunk.metadata.get("source_path")
        ranked.append(
            RankedNote(
                note_id=note_id,
                rank=len(ranked) + 1,
                source_path=source_path if isinstance(source_path, str) else None,
            )
        )
    return ranked
