"""Build the human-review pack from a live RAGAS run."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml


def load_human_sample_ids(path: Path) -> tuple[str, ...]:
    """Read gold item ids from the human score sheet, in file order."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("human sample file must be a mapping")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("human sample file must contain a non-empty items list")
    ids: list[str] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise TypeError("each human sample item must be a mapping")
        item_id = raw_item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("human sample id must be a non-empty string")
        ids.append(item_id.strip())
    return tuple(ids)


def write_human_review(
    path: Path,
    artifacts: Sequence[Mapping[str, Any]],
    sample_ids: Sequence[str],
) -> int:
    """Write question, packed chunks and model answer for the sample ids."""
    by_id = {
        str(item["item_id"]): item
        for item in artifacts
        if isinstance(item.get("item_id"), str)
    }
    review_items: list[dict[str, object]] = []
    for item_id in sample_ids:
        artifact = by_id.get(item_id)
        if artifact is None:
            review_items.append(
                {
                    "id": item_id,
                    "missing": True,
                    "reason": "id was not in this live slice",
                }
            )
            continue
        review_items.append(
            {
                "id": item_id,
                "question": artifact.get("question"),
                "answer": artifact.get("answer"),
                "refused": artifact.get("refused"),
                "skip_reason": artifact.get("skip_reason"),
                "contexts": artifact.get("contexts") or [],
                "judge": {
                    "faithfulness": artifact.get("faithfulness"),
                    "answer_relevancy": artifact.get("answer_relevancy"),
                },
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "instructions": (
                    "Прочитай question, contexts и answer. Оценки — целые 0–5; "
                    "запиши их в evals/human/sprint22_sample.yaml, не в этот файл."
                ),
                "items": review_items,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return sum(1 for item in review_items if not item.get("missing"))
