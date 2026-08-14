from pathlib import Path, PurePosixPath

import mlflow

from rag_based_on_obsidian.chunking.section_tree import build_section_tree
from rag_based_on_obsidian.chunking.tracking import track_sectionization
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def test_track_sectionization_logs_metrics_and_artifacts(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "DLS1" / "note.md"
    source_path.parent.mkdir()
    source_path.write_text("# Heading\n\nText", encoding="utf-8")
    parsed = parse_markdown_file(
        DiscoveredFile(
            absolute_path=source_path,
            relative_path=PurePosixPath("DLS1/note.md"),
        )
    )
    tree = build_section_tree(
        parsed,
        source_content_hash="hash",
        parser_version="parser-v1",
    )
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)

    metrics = track_sectionization(
        [tree],
        params={"section_tree_version": "section-tree-v1"},
        artifact_dir=tmp_path / "artifacts",
        duration_seconds=0.25,
        experiment_name="test-sectionization",
        run_name="test-run",
    )

    assert metrics["run_id"]
    assert (tmp_path / "artifacts" / "sectionization_summary.json").exists()
    assert (tmp_path / "artifacts" / "block_type_counts.csv").exists()
