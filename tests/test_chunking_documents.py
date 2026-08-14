from pathlib import Path, PurePosixPath

from langchain_core.documents import Document

from rag_based_on_obsidian.chunking.documents import section_to_document
from rag_based_on_obsidian.chunking.section_tree import build_section_tree
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_entities import ParsedDocument
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def parse_document(tmp_path: Path, content: str) -> ParsedDocument:
    path = tmp_path / "DLS1" / "note.md"
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")
    return parse_markdown_file(
        DiscoveredFile(
            absolute_path=path,
            relative_path=PurePosixPath("DLS1/note.md"),
        )
    )


def test_section_to_document_preserves_heading_and_metadata(tmp_path: Path) -> None:
    tree = build_section_tree(
        parse_document(
            tmp_path,
            """---
tags:
  - rag
---
# Retrieval

Dense search uses vectors.
""",
        ),
        note_id=7,
        source_content_hash="sha256:note",
        parser_version="parser-v1",
    )

    document = section_to_document(tree.sections[0])

    assert isinstance(document, Document)
    assert document.page_content == "# Retrieval\n\nDense search uses vectors."
    assert document.metadata["note_id"] == 7
    assert document.metadata["relative_path"] == "DLS1/note.md"
    assert document.metadata["source_content_hash"] == "sha256:note"
    assert document.metadata["parser_version"] == "parser-v1"
    assert document.metadata["section_path"] == ["Retrieval"]


def test_section_to_document_keeps_frontmatter_and_wikilinks_in_metadata(
    tmp_path: Path,
) -> None:
    tree = build_section_tree(
        parse_document(
            tmp_path,
            """---
course: rag
---
# Retrieval

See [[Embeddings]] for dense representations.
""",
        ),
        source_content_hash="hash",
        parser_version="parser-v1",
    )

    document = section_to_document(tree.sections[0])

    assert "course" not in document.page_content
    assert "[[Embeddings]]" in document.page_content
    assert document.metadata["frontmatter"] == {"course": "rag"}
    assert [link.target for link in document.metadata["wikilinks"]] == ["Embeddings"]


def test_section_to_document_uses_pre_heading_body_without_synthetic_heading(
    tmp_path: Path,
) -> None:
    tree = build_section_tree(
        parse_document(tmp_path, "Text before the first heading."),
        source_content_hash="hash",
        parser_version="parser-v1",
    )

    document = section_to_document(tree.sections[0])

    assert document.page_content == "Text before the first heading."
    assert document.metadata["section_type"] == "pre_heading"
    assert document.metadata["display_title"] == "(pre-heading)"
