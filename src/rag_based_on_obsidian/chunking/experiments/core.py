"""Pure experiment contracts, execution, metrics and local artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml

from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.records import ChunkRecord, estimated_token_count
from rag_based_on_obsidian.chunking.recursive import chunk_section_tree
from rag_based_on_obsidian.chunking.section_tree import SectionTree

TreeSource = tuple[SectionTree, str]
SHORT_CHUNK_FRACTION = 0.25


@dataclass(frozen=True)
class ExperimentConfig:
    """Validated policy identity used to reproduce one experiment run."""

    policy: ChunkingPolicy
    config_path: Path
    config_sha256: str

    @property
    def chunking_version(self) -> str:
        return self.policy.chunking_version


@dataclass(frozen=True)
class ExperimentProtocol:
    """Versioned matrix and metric rules for one experiment campaign."""

    name: str
    protocol_version: str
    short_chunk_fraction: float
    policy_paths: tuple[Path, ...]
    allowed_corpus_directories: tuple[str, ...]
    deterministic_ordering: bool
    selective_overlap_for_oversized_sections: bool


@dataclass(frozen=True)
class ExperimentResult:
    """Chunk outputs and scalar metrics for one candidate policy."""

    config: ExperimentConfig
    metrics: dict[str, float | int]
    chunks: tuple[ChunkRecord, ...]
    short_chunk_fraction: float


def load_experiment_protocol(path: Path) -> ExperimentProtocol:
    """Load a versioned experiment protocol and resolve its policy paths."""
    resolved_path = path.expanduser().resolve(strict=True)
    raw_config = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(raw_config, dict):
        raise TypeError("experiment protocol YAML must contain a mapping")
    policy_values = raw_config.get("policies")
    allowed_directories = raw_config.get("allowed_corpus_directories")
    if not isinstance(policy_values, list) or not policy_values:
        raise ValueError("experiment protocol must define policies")
    if not isinstance(allowed_directories, list) or not allowed_directories:
        raise ValueError(
            "experiment protocol must define allowed_corpus_directories"
        )
    fraction = raw_config.get("short_chunk_fraction", SHORT_CHUNK_FRACTION)
    if not isinstance(fraction, (float, int)) or not 0 < fraction < 1:
        raise ValueError("short_chunk_fraction must be between 0 and 1")
    policy_paths = tuple(
        (resolved_path.parent / str(policy_value)).resolve(strict=True)
        for policy_value in policy_values
    )
    return ExperimentProtocol(
        name=_required_protocol_string(raw_config, "name"),
        protocol_version=_required_protocol_string(
            raw_config,
            "protocol_version",
        ),
        short_chunk_fraction=float(fraction),
        policy_paths=policy_paths,
        allowed_corpus_directories=tuple(
            str(directory) for directory in allowed_directories
        ),
        deterministic_ordering=bool(raw_config.get("deterministic_ordering", True)),
        selective_overlap_for_oversized_sections=bool(
            raw_config.get("selective_overlap_for_oversized_sections", True)
        ),
    )


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load a YAML policy and preserve its bytes for experiment provenance."""
    resolved_path = path.expanduser().resolve(strict=True)
    raw_bytes = resolved_path.read_bytes()
    raw_config = yaml.safe_load(raw_bytes.decode("utf-8"))
    if not isinstance(raw_config, dict):
        raise TypeError("experiment YAML must contain a mapping")
    policy = ChunkingPolicy.model_validate(raw_config)
    return ExperimentConfig(
        policy=policy,
        config_path=resolved_path,
        config_sha256=hashlib.sha256(raw_bytes).hexdigest(),
    )


def run_experiment(
    config: ExperimentConfig,
    tree_sources: tuple[TreeSource, ...],
    *,
    short_chunk_fraction: float = SHORT_CHUNK_FRACTION,
) -> ExperimentResult:
    """Run one policy deterministically over already parsed note sources."""
    started = perf_counter()
    chunks: list[ChunkRecord] = []
    oversized_sections = 0
    for tree, source_text in tree_sources:
        oversized_sections += sum(
            estimated_token_count(source_text[section.start_offset : section.end_offset])
            > config.policy.chunk_size
            for section in tree.sections
        )
        chunks.extend(
            chunk_section_tree(
                tree,
                source_text=source_text,
                policy=config.policy,
                chunking_version=config.chunking_version,
            )
        )
    metrics = collect_metrics(
        tuple(chunks),
        tree_sources=tree_sources,
        policy=config.policy,
        oversized_sections=oversized_sections,
        short_chunk_fraction=short_chunk_fraction,
        generation_latency_seconds=perf_counter() - started,
    )
    return ExperimentResult(
        config=config,
        metrics=metrics,
        chunks=tuple(chunks),
        short_chunk_fraction=short_chunk_fraction,
    )


def collect_metrics(
    chunks: tuple[ChunkRecord, ...],
    *,
    tree_sources: tuple[TreeSource, ...],
    policy: ChunkingPolicy,
    oversized_sections: int,
    generation_latency_seconds: float,
    short_chunk_fraction: float = SHORT_CHUNK_FRACTION,
) -> dict[str, float | int]:
    """Calculate deterministic structural, provenance and cost metrics."""
    token_lengths = sorted(chunk.token_count for chunk in chunks)
    # A short chunk uses strictly less than 25% of the configured token budget.
    short_chunk_threshold = max(1, int(policy.chunk_size * short_chunk_fraction))
    metadata_fields = (
        "section_id",
        "section_path",
        "parser_version",
        "source_content_hash",
        "chunking_version",
    )
    metadata_total = len(chunks) * len(metadata_fields)
    metadata_present = sum(
        bool(getattr(chunk, field)) for chunk in chunks for field in metadata_fields
    )
    source_lengths = {
        tree.root.metadata.get("note_id"): len(source_text)
        for tree, source_text in tree_sources
    }
    offset_violations = sum(
        chunk.start_offset < 0
        or chunk.end_offset < chunk.start_offset
        or chunk.end_offset > source_lengths.get(chunk.note_id, float("inf"))
        for chunk in chunks
    )
    hashes = [hashlib.sha256(chunk.text.encode("utf-8")).hexdigest() for chunk in chunks]
    duplicate_hashes = len(hashes) - len(set(hashes))
    storage_bytes = sum(len(chunk.text.encode("utf-8")) for chunk in chunks)
    return {
        "chunks_total": len(chunks),
        "median_token_length": _percentile(token_lengths, 0.50),
        "p95_token_length": _percentile(token_lengths, 0.95),
        "mean_token_length": (
            sum(token_lengths) / len(token_lengths) if token_lengths else 0.0
        ),
        "short_chunk_threshold_tokens": short_chunk_threshold,
        "short_chunk_rate_below_25pct": (
            sum(length < short_chunk_threshold for length in token_lengths) / len(chunks)
            if chunks
            else 0.0
        ),
        "oversized_sections_total": oversized_sections,
        "overlap_enabled": int(policy.chunk_overlap > 0 and oversized_sections > 0),
        "boundary_violation_count": offset_violations,
        "duplicate_hash_count": duplicate_hashes,
        "metadata_completeness": (
            metadata_present / metadata_total if metadata_total else 1.0
        ),
        "storage_bytes": storage_bytes,
        "generation_latency_seconds": generation_latency_seconds,
    }


def write_experiment_artifacts(
    result: ExperimentResult,
    output_dir: Path,
) -> Path:
    """Write reviewable JSON/CSV/Markdown/YAML artifacts."""
    run_dir = output_dir / result.config.policy.name
    run_dir.mkdir(parents=True, exist_ok=True)
    config_snapshot = run_dir / result.config.config_path.name
    shutil.copyfile(result.config.config_path, config_snapshot)

    summary = {
        "config": {
            "name": result.config.policy.name,
            "chunking_version": result.config.chunking_version,
            "chunk_size": result.config.policy.chunk_size,
            "chunk_overlap": result.config.policy.chunk_overlap,
            "short_chunk_fraction": result.short_chunk_fraction,
            "config_sha256": result.config.config_sha256,
        },
        "metrics": result.metrics,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with (run_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("metric", "value"))
        writer.writerows(sorted(result.metrics.items()))

    rows = "\n".join(
        f"| `{name}` | `{value}` |" for name, value in sorted(result.metrics.items())
    )
    markdown = (
        f"# {result.config.policy.name}\n\n"
        f"- Chunking version: `{result.config.chunking_version}`\n"
        f"- Config SHA-256: `{result.config.config_sha256}`\n\n"
        "## Metrics\n\n| Metric | Value |\n|---|---:|\n"
        f"{rows}\n"
    )
    (run_dir / "report.md").write_text(markdown, encoding="utf-8")
    return run_dir


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    index = min(len(values) - 1, round((len(values) - 1) * quantile))
    return values[index]


def _required_protocol_string(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"experiment protocol requires non-empty {key}")
    return value
