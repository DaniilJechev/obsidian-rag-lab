"""Score live retrieval rankings against Postgres gold items."""

from collections.abc import Callable, Sequence
from dataclasses import asdict

from rag_based_on_obsidian.eval.contracts import (
    LiveGoldItem,
    QuestionMetrics,
    collapse_chunks_to_notes,
)
from rag_based_on_obsidian.eval.metrics import score_question
from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk

RetrieveFn = Callable[[str], Sequence[RetrievedChunk]]


def run_live_eval(
    items: Sequence[LiveGoldItem],
    retrieve: RetrieveFn,
    *,
    k: int,
) -> tuple[list[QuestionMetrics], list[dict[str, object]]]:
    """Retrieve, collapse chunks to notes, and score each gold question at k."""
    results: list[QuestionMetrics] = []
    artifacts: list[dict[str, object]] = []
    for item in items:
        metrics, artifact = _score_live_item(item, retrieve, k=k)
        results.append(metrics)
        artifacts.append(artifact)
    return results, artifacts


def _score_live_item(
    item: LiveGoldItem,
    retrieve: RetrieveFn,
    *,
    k: int,
) -> tuple[QuestionMetrics, dict[str, object]]:
    try:
        chunks = retrieve(item.question)
        ranked = collapse_chunks_to_notes(chunks)
    except ValueError as exc:
        metrics = QuestionMetrics(
            item_id=item.item_id,
            skipped=True,
            k=k,
            skip_reason=str(exc),
        )
        return metrics, _artifact(
            item,
            metrics,
            predicted_note_ids=(),
            predicted_paths=(),
            chunk_count=0,
        )
    predicted_ids = tuple(note.note_id for note in ranked)
    predicted_paths = tuple(
        note.source_path for note in ranked if note.source_path is not None
    )
    metrics = score_question(
        item_id=item.item_id,
        predicted=predicted_ids,
        relevant=item.relevant_note_ids,
        k=k,
    )
    return metrics, _artifact(
        item,
        metrics,
        predicted_note_ids=predicted_ids,
        predicted_paths=predicted_paths,
        chunk_count=len(chunks),
    )


def _artifact(
    item: LiveGoldItem,
    metrics: QuestionMetrics,
    *,
    predicted_note_ids: tuple[int, ...],
    predicted_paths: tuple[str, ...],
    chunk_count: int,
) -> dict[str, object]:
    relevant = set(item.relevant_note_ids)
    predicted_set = set(predicted_note_ids)
    ranks = {
        str(note_id): rank
        for rank, note_id in enumerate(predicted_note_ids, start=1)
        if note_id in relevant
    }
    metric_values = {
        key: value
        for key, value in asdict(metrics).items()
        if key not in {"item_id", "skipped", "skip_reason"}
    }
    return {
        "item_id": item.item_id,
        "eval_item_id": item.eval_item_id,
        "question": item.question,
        "skipped": metrics.skipped,
        "skip_reason": metrics.skip_reason,
        "chunk_count": chunk_count,
        "predicted_note_ids": list(predicted_note_ids),
        "predicted_paths": list(predicted_paths),
        "relevant_note_ids": list(item.relevant_note_ids),
        "relevant_paths": list(item.relevant_note_paths),
        "hits": [note_id for note_id in predicted_note_ids if note_id in relevant],
        "misses": [
            note_id for note_id in item.relevant_note_ids if note_id not in predicted_set
        ],
        "relevant_ranks": ranks,
        "metrics": metric_values,
    }
