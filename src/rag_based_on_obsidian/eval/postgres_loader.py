"""Persist gold YAML into PostgreSQL eval_items."""

from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection

from rag_based_on_obsidian.db.schema import eval_items, notes
from rag_based_on_obsidian.eval.contracts import GoldItem


class UnresolvedGoldNotesError(ValueError):
    """Raised when YAML paths do not match notes.relative_path."""

    def __init__(self, missing_paths: Sequence[str]) -> None:
        self.missing_paths = tuple(missing_paths)
        listed = ", ".join(self.missing_paths)
        super().__init__(f"gold note paths are missing from notes: {listed}")


def load_note_path_index(connection: Connection) -> dict[str, int]:
    """Map notes.relative_path to note_id."""
    rows = connection.execute(select(notes.c.relative_path, notes.c.note_id))
    return {str(path): int(note_id) for path, note_id in rows}


def resolve_note_ids(
    items: Sequence[GoldItem],
    path_index: Mapping[str, int],
) -> dict[str, tuple[int, ...]]:
    """Resolve YAML relative paths to note_id values."""
    missing: list[str] = []
    resolved: dict[str, tuple[int, ...]] = {}
    for item in items:
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
