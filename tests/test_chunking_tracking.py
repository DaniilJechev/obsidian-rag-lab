from pathlib import Path, PurePosixPath

from rag_based_on_obsidian.chunking.section_tree import build_section_tree
from rag_based_on_obsidian.chunking.tracking import sectionization_metrics
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def test_sectionization_metrics_count_structural_output(tmp_path: Path) -> None:
    path = tmp_path / "DLS1" / "note.md"
    path.parent.mkdir()
    path.write_text("# Heading\n\nText", encoding="utf-8")
    parsed = parse_markdown_file(
        DiscoveredFile(
            absolute_path=path,
            relative_path=PurePosixPath("DLS1/note.md"),
        )
    )
    tree = build_section_tree(
        parsed,
        source_content_hash="hash",
        parser_version="parser-v1",
    )

    metrics = sectionization_metrics([tree], duration_seconds=0.25)

    assert metrics["documents_processed"] == 1
    assert metrics["sections_total"] == 1
    assert metrics["blocks_total"] == 2
    assert metrics["block_type_counts"] == {"heading": 1, "paragraph": 1}
    assert metrics["langchain_documents_total"] == 1
    assert metrics["invalid_offset_count"] == 0
    assert metrics["sectionization_duration_seconds"] == 0.25
