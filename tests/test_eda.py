"""Tests for chunking-oriented EDA aggregation and report rendering."""

from pathlib import Path

from rag_based_on_obsidian.corpus.eda import (
    _paragraph_rows,
    create_eda_figures,
    write_eda_markdown,
)


def _inventory() -> dict:
    return {
        "summary": {
            "documents_total": 1,
            "documents_parsed": 1,
            "documents_failed": 0,
            "mean_file_size_bytes": 100.0,
            "median_file_size_bytes": 100.0,
            "duplicate_groups": 0,
            "duplicate_documents": 0,
        },
        "documents": [
            {
                "parse_status": "ok",
                "source": {"relative_path": "DLS1/example.md"},
                "language_statistics": {
                    "russian_word_count": 2,
                    "english_word_count": 2,
                    "mixed_or_other_word_count": 0,
                    "unknown_word_count": 0,
                },
                "heading_statistics": [
                    {
                        "level": 1,
                        "view": "direct_body",
                        "section_count": 1,
                        "mean_word_count": 4.0,
                        "median_word_count": 4.0,
                    }
                ],
                "paragraph_blocks": [
                    {
                        "level": 1,
                        "word_count": 4,
                        "token_count": 4,
                        "character_count": 20,
                        "byte_count": 20,
                        "russian_word_count": 2,
                        "english_word_count": 2,
                        "mixed_or_other_word_count": 0,
                        "unknown_word_count": 0,
                        "wikilink_count": 1,
                        "image_embed_count": 0,
                        "code_block_count": 0,
                        "list_item_count": 0,
                        "blockquote_line_count": 0,
                    }
                ],
                "anomalies": [],
            }
        ],
        "duplicate_groups": [],
    }


def test_paragraph_rows_omit_missing_levels() -> None:
    rows = _paragraph_rows(_inventory())

    assert [level for level, _ in rows] == ["H1", "all_levels"]


def test_report_uses_cursor_image_links_and_chunking_metrics(tmp_path: Path) -> None:
    report = tmp_path / "corpus_eda.md"

    write_eda_markdown(
        _inventory(),
        [tmp_path / "paragraph_length_distribution.png"],
        report,
    )

    content = report.read_text(encoding="utf-8")
    assert "![Paragraph Length Distribution](paragraph_length_distribution.png)" in content
    assert "Paragraph length distribution" in content
    assert "| Statistic | Value | Unit |" in content
    assert "Median words" in content
    assert "Token/word" in content
    assert "H1" in content
    assert "H2" not in content


def test_create_eda_figures_clears_previous_output(tmp_path: Path) -> None:
    output_directory = tmp_path / "eda"
    output_directory.mkdir()
    (output_directory / "stale.png").write_bytes(b"old")
    (output_directory / "old-report.md").write_text("old", encoding="utf-8")

    create_eda_figures(_inventory(), output_directory, show_progress=False)

    assert not (output_directory / "stale.png").exists()
    assert not (output_directory / "old-report.md").exists()
