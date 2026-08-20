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
    """Retrieval metrics for one question, or a skip marker."""

    item_id: str
    skipped: bool
    skip_reason: str | None = None
    ndcg_at_5: float | None = None
    ndcg_at_10: float | None = None
    mrr_at_10: float | None = None
    recall_at_5: float | None = None
    recall_at_10: float | None = None
    hit_at_10: float | None = None


@dataclass(frozen=True)
class DatasetMetrics:
    """Macro-average over scored (non-skipped) questions."""

    question_count: int
    scored_count: int
    skipped_count: int
    ndcg_at_5: float | None
    ndcg_at_10: float | None
    mrr_at_10: float | None
    recall_at_5: float | None
    recall_at_10: float | None
    hit_at_10: float | None


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
