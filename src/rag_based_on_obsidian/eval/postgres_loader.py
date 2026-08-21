"""Persist gold YAML into PostgreSQL eval_items."""

import sys
from collections.abc import Iterable, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection
from tqdm import tqdm

from rag_based_on_obsidian.db.schema import eval_items, notes
from rag_based_on_obsidian.eval.contracts import (
    GoldItem,
    LiveGoldItem,
    StoredEvalItem,
)


class UnresolvedGoldNotesError(ValueError):
    """Raised when YAML paths do not match notes.relative_path."""

    def __init__(self, missing_paths: Sequence[str]) -> None:
        self.missing_paths = tuple(missing_paths)
        listed = ", ".join(self.missing_paths)
        super().__init__(f"gold note paths are missing from notes: {listed}")


def load_note_path_index(
    connection: Connection,
    *,
    show_progress: bool = False,
) -> dict[str, int]:
    """Map notes.relative_path to note_id."""
    rows = connection.execute(select(notes.c.relative_path, notes.c.note_id))
    indexed: Iterable[tuple[object, object]] = rows
    if show_progress:
        indexed = tqdm(
            rows,
            desc="index notes.relative_path",
            file=sys.stderr,
            unit="note",
        )
    return {str(path): int(note_id) for path, note_id in indexed}


def resolve_note_ids(
    items: Sequence[GoldItem],
    path_index: Mapping[str, int],
    *,
    show_progress: bool = False,
) -> dict[str, tuple[int, ...]]:
    """Resolve YAML relative paths to note_id values."""
    missing: list[str] = []
    resolved: dict[str, tuple[int, ...]] = {}
    iterator: Iterable[GoldItem] = items
    if show_progress:
        iterator = tqdm(
            items,
            desc="resolve gold notes",
            file=sys.stderr,
            unit="q",
        )
    for item in iterator:
        note_ids: list[int] = []
        for path in item.relevant_note_paths:
            note_id = path_index.get(path)
            if note_id is None:
                missing.append(path)
                continue
            note_ids.append(note_id)
        resolved[item.item_id] = tuple(dict.fromkeys(note_ids))
    if missing:
        raise UnresolvedGoldNotesError(tuple(dict.fromkeys(missing)))
    return resolved


def clear_eval_items(connection: Connection) -> int:
    """Delete every gold row so load-gold keeps a single current set."""
    result = connection.execute(eval_items.delete())
    return int(result.rowcount or 0)


def upsert_eval_items(
    connection: Connection,
    items: Sequence[GoldItem],
    resolved_note_ids: Mapping[str, Sequence[int]],
) -> int:
    """Insert or update gold rows keyed by dataset_version + question."""
    if not items:
        return 0
    rows = [
        {
            "question": item.question,
            "corpus_scope": item.corpus_scope,
            "relevant_note_ids": list(resolved_note_ids[item.item_id]),
            "relevant_chunk_ids": list(item.relevant_chunk_ids),
            "dataset_version": item.dataset_version,
        }
        for item in items
    ]
    statement = pg_insert(eval_items).values(rows)
    statement = statement.on_conflict_do_update(
        constraint="uq_eval_items_dataset_question",
        set_={
            "corpus_scope": statement.excluded.corpus_scope,
            "relevant_note_ids": statement.excluded.relevant_note_ids,
            "relevant_chunk_ids": statement.excluded.relevant_chunk_ids,
        },
    )
    result = connection.execute(statement)
    return int(result.rowcount or 0)


class UnresolvedEvalNoteIdsError(ValueError):
    """Raised when eval_items note ids are missing from notes."""

    def __init__(self, missing_ids: Sequence[int]) -> None:
        self.missing_ids = tuple(missing_ids)
        listed = ", ".join(str(note_id) for note_id in self.missing_ids)
        super().__init__(f"eval_items note ids are missing from notes: {listed}")


def load_eval_items(
    connection: Connection,
    dataset_version: str,
) -> tuple[StoredEvalItem, ...]:
    """Load gold rows for one dataset_version, ordered by eval_item_id."""
    if not dataset_version.strip():
        raise ValueError("dataset_version must not be empty")
    rows = connection.execute(
        select(
            eval_items.c.eval_item_id,
            eval_items.c.question,
            eval_items.c.corpus_scope,
            eval_items.c.relevant_note_ids,
            eval_items.c.dataset_version,
        )
        .where(eval_items.c.dataset_version == dataset_version)
        .order_by(eval_items.c.eval_item_id)
    )
    return tuple(stored_eval_item_from_mapping(row._mapping) for row in rows)


def stored_eval_item_from_mapping(row: Mapping[str, object]) -> StoredEvalItem:
    """Parse one eval_items row into a typed gold record."""
    eval_item_id = row["eval_item_id"]
    question = row["question"]
    corpus_scope = row["corpus_scope"]
    dataset_version = row["dataset_version"]
    if not isinstance(eval_item_id, int) or eval_item_id <= 0:
        raise ValueError("eval_item_id must be a positive integer")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if not isinstance(corpus_scope, str) or not corpus_scope.strip():
        raise ValueError("corpus_scope must be a non-empty string")
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ValueError("dataset_version must be a non-empty string")
    return StoredEvalItem(
        eval_item_id=eval_item_id,
        question=question.strip(),
        corpus_scope=corpus_scope.strip(),
        relevant_note_ids=_as_positive_int_tuple(row["relevant_note_ids"]),
        dataset_version=dataset_version.strip(),
    )


def bind_live_gold_items(
    stored: Sequence[StoredEvalItem],
    path_index: Mapping[str, int],
    yaml_items: Sequence[GoldItem] | None = None,
) -> tuple[LiveGoldItem, ...]:
    """Attach relative_path values and optional YAML item ids to Postgres gold."""
    id_to_path = {note_id: path for path, note_id in path_index.items()}
    question_to_item_id = {
        item.question: item.item_id for item in (yaml_items or ())
    }
    missing: list[int] = []
    bound: list[LiveGoldItem] = []
    for item in stored:
        paths: list[str] = []
        for note_id in item.relevant_note_ids:
            path = id_to_path.get(note_id)
            if path is None:
                missing.append(note_id)
                continue
            paths.append(path)
        bound.append(
            LiveGoldItem(
                item_id=question_to_item_id.get(
                    item.question,
                    f"eval-{item.eval_item_id}",
                ),
                eval_item_id=item.eval_item_id,
                question=item.question,
                relevant_note_ids=item.relevant_note_ids,
                relevant_note_paths=tuple(paths),
                dataset_version=item.dataset_version,
            )
        )
    if missing:
        raise UnresolvedEvalNoteIdsError(tuple(dict.fromkeys(missing)))
    return tuple(bound)


def _as_positive_int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise TypeError("relevant_note_ids must be a list")
    note_ids: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool) or item <= 0:
            raise ValueError("relevant_note_ids must contain positive integers")
        note_ids.append(item)
    return tuple(note_ids)
