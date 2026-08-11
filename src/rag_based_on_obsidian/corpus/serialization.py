"""JSON serialization for corpus inventory entities."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rag_based_on_obsidian.corpus.inventory_entities import CorpusInventory


def inventory_to_dict(inventory: CorpusInventory) -> dict[str, Any]:
    """Convert the immutable inventory contract into JSON-compatible data."""

    data = asdict(inventory)
    for document_data, document in zip(
        data["documents"],
        inventory.documents,
        strict=True,
    ):
        document_data["source"] = {
            "relative_path": document.source.relative_path.as_posix(),
        }
    return data


def write_inventory_json(
    inventory: CorpusInventory,
    output_path: Path,
) -> None:
    """Write a deterministic, UTF-8 JSON inventory artifact."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            inventory_to_dict(inventory),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
