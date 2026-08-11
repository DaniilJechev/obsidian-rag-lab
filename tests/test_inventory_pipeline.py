from pathlib import Path, PurePosixPath

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.heading_sections import extract_heading_sections
from rag_based_on_obsidian.corpus.inventory import build_corpus_inventory
from rag_based_on_obsidian.corpus.language_classifier import (
    WordLanguage,
    classify_word,
)
from rag_based_on_obsidian.corpus.markdown_entities import Heading, ParsedDocument
from rag_based_on_obsidian.corpus.serialization import inventory_to_dict
from rag_based_on_obsidian.corpus.statistics import (
    calculate_document_statistics,
)
from rag_based_on_obsidian.corpus.word_tokenizer import tokenize_words


def _parsed_document(raw_text: str) -> ParsedDocument:
    path = Path("C:/vault/DLS2/Example.md")
    return ParsedDocument(
        source=DiscoveredFile(
            absolute_path=path,
            relative_path=PurePosixPath("DLS2/Example.md"),
        ),
        raw_text=raw_text,
        frontmatter={},
    )


def test_language_classifier_handles_russian_english_and_mixed_words() -> None:
    assert classify_word("модель") is WordLanguage.RUSSIAN
    assert classify_word("embedding") is WordLanguage.ENGLISH
    assert classify_word("BERT-модель") is WordLanguage.MIXED_OR_OTHER


def test_heading_sections_provide_direct_and_full_span_views() -> None:
    document = _parsed_document(
        "Введение.\n\n# BERT\nТекст A.\n\n## Encoder\nТекст B.\n\n"
        "### Attention\nТекст C.\n\n# Next\nТекст D."
    )
    document = ParsedDocument(
        source=document.source,
        raw_text=document.raw_text,
        frontmatter=document.frontmatter,
        headings=(
            Heading(1, "BERT", 3),
            Heading(2, "Encoder", 6),
            Heading(3, "Attention", 9),
            Heading(1, "Next", 12),
        ),
    )

    sections = extract_heading_sections(document)

    assert sections[0].level is None
    assert sections[0].direct_body == "Введение."
    assert sections[1].direct_body == "Текст A."
    assert "Текст B." in sections[1].full_span
    assert sections[2].direct_body == "Текст B."
    assert "Текст C." in sections[2].full_span


def test_document_statistics_include_analysis_and_hash() -> None:
    raw_text = "# BERT\n\nBERT-модель uses attention."
    statistics = calculate_document_statistics(_parsed_document(raw_text))

    assert statistics.analysis_text == " BERT\n\nBERT-модель uses attention."
    assert statistics.word_count == len(tokenize_words(statistics.analysis_text))
    assert statistics.file_size_bytes == len(raw_text.encode("utf-8"))
    assert statistics.content_hash is not None
    assert statistics.language_statistics.russian_word_count == 0
    assert statistics.language_statistics.english_word_count == 3
    assert statistics.language_statistics.mixed_or_other_word_count == 1


def test_batch_inventory_aggregates_documents_and_keeps_parse_failures(
    tmp_path: Path,
) -> None:
    valid_path = tmp_path / "DLS2" / "valid.md"
    invalid_path = tmp_path / "DLS2" / "invalid.md"
    valid_path.parent.mkdir()
    valid_path.write_text("# Note\nТекст.", encoding="utf-8")
    invalid_path.write_text("---\nnot: [closed\n", encoding="utf-8")
    files = [
        DiscoveredFile(valid_path, PurePosixPath("DLS2/valid.md")),
        DiscoveredFile(invalid_path, PurePosixPath("DLS2/invalid.md")),
    ]

    inventory = build_corpus_inventory(
        files,
        generated_at="2026-08-11T00:00:00Z",
        show_progress=False,
    )

    assert inventory.summary.documents_total == 2
    assert inventory.summary.documents_parsed == 1
    assert inventory.summary.documents_failed == 1
    failed_document = next(
        document
        for document in inventory.documents
        if document.parse_status == "failed"
    )
    assert failed_document.anomalies == ("malformed_frontmatter",)
    assert len(inventory.documents) == 2
    assert any(
        document.source.relative_path == PurePosixPath("DLS2/valid.md")
        for document in inventory.documents
    )
    serialized = inventory_to_dict(inventory)
    assert serialized["summary"]["documents_failed"] == 1
    assert next(
        document["error_type"]
        for document in serialized["documents"]
        if document["parse_status"] == "failed"
    ) == "ValueError"


def test_batch_inventory_groups_identical_content(tmp_path: Path) -> None:
    first = tmp_path / "DLS2" / "first.md"
    second = tmp_path / "DLS2" / "second.md"
    first.parent.mkdir()
    first.write_text("# Same\nText.", encoding="utf-8")
    second.write_text("# Same\nText.", encoding="utf-8")

    inventory = build_corpus_inventory(
        [
            DiscoveredFile(first, PurePosixPath("DLS2/first.md")),
            DiscoveredFile(second, PurePosixPath("DLS2/second.md")),
        ],
        generated_at="2026-08-11T00:00:00Z",
        show_progress=False,
    )

    assert inventory.summary.duplicate_groups == 1
    assert inventory.summary.duplicate_documents == 2
    assert inventory.duplicate_groups[0].relative_paths == (
        "DLS2/first.md",
        "DLS2/second.md",
    )
