from pathlib import Path, PurePosixPath

import pytest

from rag_based_on_obsidian.chunking.documents import section_to_document
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
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


def test_section_tree_preserves_hierarchy_siblings_and_blocks(tmp_path: Path) -> None:
    content = """# RAG

Intro.

## Chunking

Text.

### Overlap

- one

### Boundaries

```python
# not a heading
```

## Retrieval

Table:
| A | B |
|---|---|
"""
    tree = build_section_tree(
        parse_document(tmp_path, content),
        source_content_hash="hash",
        parser_version="parser-v1",
    )

    rag, chunking, overlap, boundaries, retrieval = tree.sections
    assert rag.parent_section_id is None
    assert chunking.parent_section_id == rag.section_id
    assert chunking.previous_sibling_id is None
    assert chunking.next_sibling_id == retrieval.section_id
    assert retrieval.previous_sibling_id == chunking.section_id
    assert overlap.parent_section_id == chunking.section_id
    assert overlap.next_sibling_id == boundaries.section_id
    assert boundaries.previous_sibling_id == overlap.section_id
    assert [block.block_type.value for block in overlap.blocks] == [
        "heading",
        "list",
    ]
    assert [block.block_type.value for block in boundaries.blocks] == [
        "heading",
        "code",
    ]
    assert [block.block_type.value for block in retrieval.blocks] == [
        "heading",
        "paragraph",
        "table",
        "table",
    ]
    for section in tree.sections:
        source_span = content[section.start_offset : section.end_offset]
        assert section.direct_body in source_span
        assert source_span.startswith("#")


def test_empty_heading_and_document_metadata(tmp_path: Path) -> None:
    content = "Before\n\n##\n\nBody"
    tree = build_section_tree(
        parse_document(tmp_path, content),
        note_id=42,
        source_content_hash="hash",
        parser_version="parser-v1",
    )

    pre_heading, empty_heading = tree.sections
    assert pre_heading.section_type == "pre_heading"
    assert pre_heading.display_title == "(pre-heading)"
    assert empty_heading.title is None
    assert empty_heading.is_empty_heading is True
    assert empty_heading.section_path == ("__empty_heading__",)

    document = section_to_document(empty_heading)
    assert document.page_content.startswith("## (empty heading)")
    assert document.metadata["note_id"] == 42
    assert document.metadata["start_offset"] == empty_heading.start_offset


def test_chunking_policy_validates_overlap_and_separators() -> None:
    policy = ChunkingPolicy(
        name="default",
        chunk_size=512,
        chunk_overlap=0,
        separators=["\n\n", "\n", " "],
    )
    assert policy.include_heading_context is True

    with pytest.raises(ValueError, match="smaller"):
        ChunkingPolicy(
            name="invalid",
            chunk_size=10,
            chunk_overlap=10,
            separators=[" "],
        )
    with pytest.raises(ValueError, match="empty"):
        ChunkingPolicy(
            name="invalid",
            chunk_size=10,
            chunk_overlap=0,
            separators=[""],
        )
