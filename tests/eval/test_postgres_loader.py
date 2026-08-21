from types import SimpleNamespace

import pytest

from rag_based_on_obsidian.db.schema import eval_items
from rag_based_on_obsidian.eval.contracts import GoldItem
from rag_based_on_obsidian.eval.postgres_loader import (
    UnresolvedGoldNotesError,
    clear_eval_items,
    resolve_note_ids,
)


def _item(*paths: str) -> GoldItem:
    return GoldItem(
        item_id="q001",
        question="What is dropout?",
        corpus_scope="DLS1+DLS2",
        relevant_note_paths=paths,
        dataset_version="phase7-note-level-v0-draft",
        source_directory="DLS1",
    )


def test_resolve_note_ids_maps_relative_paths() -> None:
    resolved = resolve_note_ids(
        [_item("DLS1/Dropout.md")],
        {"DLS1/Dropout.md": 42},
    )

    assert resolved == {"q001": (42,)}


def test_resolve_note_ids_lists_missing_paths() -> None:
    with pytest.raises(UnresolvedGoldNotesError) as error:
        resolve_note_ids([_item("DLS1/missing.md")], {"DLS1/Dropout.md": 1})

    assert error.value.missing_paths == ("DLS1/missing.md",)


def test_clear_eval_items_deletes_all_rows() -> None:
    executed: list[object] = []

    class FakeConnection:
        def execute(self, statement: object) -> SimpleNamespace:
            executed.append(statement)
            return SimpleNamespace(rowcount=100)

    deleted = clear_eval_items(FakeConnection())

    assert deleted == 100
    assert executed[0].table is eval_items
