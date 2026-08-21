from pathlib import Path

import pytest

from rag_based_on_obsidian.config import DEFAULT_EVAL_GOLD_PATH
from rag_based_on_obsidian.eval.gold_yaml import GoldYamlError, load_gold_yaml


def test_frozen_gold_yaml_has_fifty_note_level_items() -> None:
    dataset_version, items = load_gold_yaml(DEFAULT_EVAL_GOLD_PATH)

    assert dataset_version == "phase7_GT_note_level_v0"
    assert len(items) == 50
    assert {item.item_id for item in items} == {
        *(f"q{index:03d}" for index in range(1, 8)),
        *(f"q{index:03d}" for index in range(9, 52)),
    }
    assert all(2 <= len(item.relevant_note_paths) <= 3 for item in items)
    directories = {item.source_directory for item in items}
    assert directories == {"DLS1", "DLS2"}
    assert all(item.relevant_chunk_ids == () for item in items)


def test_gold_yaml_rejects_empty_items(tmp_path: Path) -> None:
    path = tmp_path / "gold.yaml"
    path.write_text(
        "dataset_version: x\ncorpus_scope: DLS1+DLS2\nitems: []\n",
        encoding="utf-8",
    )
    with pytest.raises(GoldYamlError, match="items"):
        load_gold_yaml(path)


def test_eval_config_points_at_gt_gold_yaml() -> None:
    from rag_based_on_obsidian.config import (
        DEFAULT_EVAL_DATASET_VERSION,
        DEFAULT_EVAL_GOLD_PATH,
    )

    assert DEFAULT_EVAL_GOLD_PATH.name == "phase7_GT_note_level_v0.yaml"
    assert DEFAULT_EVAL_GOLD_PATH.is_file()
    assert DEFAULT_EVAL_DATASET_VERSION == "phase7_GT_note_level_v0"
