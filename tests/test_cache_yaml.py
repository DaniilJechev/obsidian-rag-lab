"""Tests for paraphrase eval YAML loader."""

from pathlib import Path

from rag_based_on_obsidian.eval.cache.cache_yaml import load_cache_paraphrase_yaml


def test_load_cache_paraphrase_v0_yaml() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "eval"
        / "cache"
        / "cache_paraphrase_v0.yaml"
    )
    dataset_version, groups = load_cache_paraphrase_yaml(path)
    assert dataset_version == "cache_paraphrase_v0"
    assert len(groups) == 12
    assert groups[0].group_id == "g001"
    assert len(groups[0].paraphrases) == 2


def test_load_cache_paraphrase_smoke_yaml() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "eval"
        / "cache"
        / "cache_paraphrase_smoke_v0.yaml"
    )
    dataset_version, groups = load_cache_paraphrase_yaml(path)
    assert dataset_version == "cache_paraphrase_smoke_v0"
    assert len(groups) == 5
    assert all(len(group.paraphrases) == 1 for group in groups)
