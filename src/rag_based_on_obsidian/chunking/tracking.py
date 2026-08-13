"""MLflow tracking for Sprint 7 sectionization evidence."""

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from time import perf_counter
from typing import Any

import mlflow

from rag_based_on_obsidian.chunking.section_tree import SectionTree

DEFAULT_ARTIFACT_DIR = (
    Path(__file__).resolve().parents[3]
    / "artifacts"
    / "chunking"
    / "sectionization"
)


def sectionization_metrics(
    trees: Sequence[SectionTree],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    """Calculate structural metrics without logging side effects."""
    sections = [section for tree in trees for section in tree.sections]
    blocks = [block for section in sections for block in section.blocks]
    type_counts: dict[str, int] = {}
    for block in blocks:
        type_counts[block.block_type.value] = type_counts.get(block.block_type.value, 0) + 1
    max_depth = max((len(section.section_path) for section in sections), default=0)
    invalid_offsets = sum(
        section.start_offset > section.end_offset
        or any(block.start_offset > block.end_offset for block in section.blocks)
        for section in sections
    )
    metadata_fields = ("relative_path", "source_content_hash", "parser_version")
    metadata_total = len(sections) * len(metadata_fields)
    metadata_present = sum(
        value is not None
        for section in sections
        for value in (section.metadata.get(field) for field in metadata_fields)
    )
    return {
        "documents_processed": len(trees),
        "sections_total": len(sections),
        "blocks_total": len(blocks),
        "block_type_counts": type_counts,
        "max_tree_depth": max_depth,
        "empty_heading_count": sum(section.is_empty_heading for section in sections),
        "pre_heading_count": sum(section.section_type == "pre_heading" for section in sections),
        "invalid_offset_count": invalid_offsets,
        "metadata_completeness": (
            metadata_present / metadata_total if metadata_total else 1.0
        ),
        "langchain_documents_total": len(sections),
        "sectionization_duration_seconds": duration_seconds,
    }


def track_sectionization(
    trees: Sequence[SectionTree],
    *,
    params: Mapping[str, Any],
    artifact_dir: Path | None = None,
    duration_seconds: float | None = None,
    experiment_name: str = "phase-3-sectionization",
    run_name: str = "sprint-7-section-tree",
) -> dict[str, Any]:
    """Log one Sprint 7 sectionization run and its generated artifacts."""
    artifact_dir = artifact_dir or DEFAULT_ARTIFACT_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    metrics = sectionization_metrics(
        trees,
        duration_seconds=duration_seconds or (perf_counter() - started),
    )
    summary_path = artifact_dir / "sectionization_summary.json"
    summary_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    counts_path = artifact_dir / "block_type_counts.csv"
    with counts_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("block_type", "count"))
        for block_type, count in sorted(metrics["block_type_counts"].items()):
            writer.writerow((block_type, count))

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(dict(params))
        scalar_metrics = {
            key: value
            for key, value in metrics.items()
            if isinstance(value, (int, float))
        }
        mlflow.log_metrics(scalar_metrics)
        mlflow.log_artifacts(str(artifact_dir))
        metrics["run_id"] = run.info.run_id
    return metrics
