"""Load the git-authored gold YAML without touching PostgreSQL."""

from pathlib import Path
from typing import Any

import yaml

from rag_based_on_obsidian.eval.contracts import GoldItem


class GoldYamlError(ValueError):
    """Raised when the gold YAML is missing required fields."""


def load_gold_yaml(path: Path) -> tuple[str, tuple[GoldItem, ...]]:
    """Parse note-level gold items from the authoring YAML file."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GoldYamlError("gold file must be a mapping")
    dataset_version = _required_str(payload, "dataset_version")
    corpus_scope = _required_str(payload, "corpus_scope")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise GoldYamlError("gold file must contain a non-empty items list")

    items: list[GoldItem] = []
    seen_ids: set[str] = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise GoldYamlError("each gold item must be a mapping")
        item_id = _required_str(raw_item, "id")
        if item_id in seen_ids:
            raise GoldYamlError(f"duplicate gold item id: {item_id}")
        seen_ids.add(item_id)
        notes = raw_item.get("relevant_notes")
        if not isinstance(notes, list) or not notes:
            raise GoldYamlError(f"{item_id} must list relevant_notes")
        paths = tuple(_required_path(note) for note in notes)
        items.append(
            GoldItem(
                item_id=item_id,
                question=_required_str(raw_item, "question"),
                corpus_scope=corpus_scope,
                relevant_note_paths=paths,
                dataset_version=dataset_version,
                source_directory=_required_str(raw_item, "source_directory"),
            )
        )
    return dataset_version, tuple(items)


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoldYamlError(f"{key} must be a non-empty string")
    return value.strip()


def _required_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoldYamlError("relevant note path must be a non-empty string")
    return value.strip().replace("\\", "/")
