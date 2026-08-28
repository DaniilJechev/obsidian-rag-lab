"""Load the Sprint 28 paraphrase eval YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class CacheParaphraseYamlError(ValueError):
    """Raised when the paraphrase YAML is missing required fields."""


@dataclass(frozen=True)
class ParaphraseGroup:
    """One canonical question and its paraphrases."""

    group_id: str
    canonical: str
    paraphrases: tuple[str, ...]


def load_cache_paraphrase_yaml(path: Path) -> tuple[str, tuple[ParaphraseGroup, ...]]:
    """Parse paraphrase groups from the authoring YAML file."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CacheParaphraseYamlError("cache paraphrase file must be a mapping")
    dataset_version = _required_str(payload, "dataset_version")
    raw_groups = payload.get("groups")
    if not isinstance(raw_groups, list) or not raw_groups:
        raise CacheParaphraseYamlError("groups must be a non-empty list")
    groups: list[ParaphraseGroup] = []
    seen_ids: set[str] = set()
    for raw_group in raw_groups:
        if not isinstance(raw_group, dict):
            raise CacheParaphraseYamlError("each group must be a mapping")
        group_id = _required_str(raw_group, "id")
        if group_id in seen_ids:
            raise CacheParaphraseYamlError(f"duplicate group id: {group_id}")
        seen_ids.add(group_id)
        canonical = _required_str(raw_group, "canonical")
        raw_paraphrases = raw_group.get("paraphrases")
        if not isinstance(raw_paraphrases, list) or not raw_paraphrases:
            raise CacheParaphraseYamlError(f"{group_id} must list paraphrases")
        paraphrases = tuple(_required_str({"value": item}, "value") for item in raw_paraphrases)
        groups.append(
            ParaphraseGroup(
                group_id=group_id,
                canonical=canonical,
                paraphrases=paraphrases,
            )
        )
    return dataset_version, tuple(groups)


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CacheParaphraseYamlError(f"{key} must be a non-empty string")
    return value.strip()
