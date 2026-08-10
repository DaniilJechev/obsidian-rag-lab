from pathlib import Path, PurePosixPath

import pytest

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_entities import (
    Heading,
    ImageLink,
    Wikilink,
)
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def discovered_file(tmp_path: Path, content: str) -> DiscoveredFile:
    """Create one discovered-file boundary for parser tests."""

    path = tmp_path / "DLS1" / "Parser note.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return DiscoveredFile(
        absolute_path=path,
        relative_path=PurePosixPath("DLS1/Parser note.md"),
    )


def test_parser_populates_all_markdown_entities(tmp_path: Path) -> None:
    content = """---
title: Parser note
tags:
  - rag
  - nlp
---
# Introduction

Text with [[RAG]] and [[BERT|Encoder model]].

![[Pasted image.png]]
"""
    source = discovered_file(tmp_path, content)

    parsed = parse_markdown_file(source)

    assert parsed.source == source
    assert parsed.raw_text == content
    assert parsed.frontmatter == {
        "title": "Parser note",
        "tags": ["rag", "nlp"],
    }
    assert parsed.headings == (
        Heading(level=1, text="Introduction", line_number=7),
    )
    assert parsed.wikilinks == (
        Wikilink(target="RAG", raw="[[RAG]]"),
        Wikilink(
            target="BERT",
            raw="[[BERT|Encoder model]]",
            alias="Encoder model",
        ),
    )
    assert parsed.image_links == (
        ImageLink(
            target="Pasted image.png",
            raw="![[Pasted image.png]]",
        ),
    )
    assert parsed.filename == "Parser note.md"
    assert parsed.folder == "DLS1"


def test_parser_supports_missing_and_empty_frontmatter(tmp_path: Path) -> None:
    without_frontmatter = discovered_file(tmp_path, "# Note")
    parsed_without = parse_markdown_file(without_frontmatter)
    assert parsed_without.frontmatter == {}

    empty_frontmatter = discovered_file(tmp_path, "---\n---\n# Note")
    parsed_empty = parse_markdown_file(empty_frontmatter)
    assert parsed_empty.frontmatter == {}


def test_parser_preserves_empty_headings_and_ignores_fenced_code(
    tmp_path: Path,
) -> None:
    content = """#
## Real heading

```markdown
# Code heading
[[Code link]]
![[code.png]]
```
"""
    parsed = parse_markdown_file(discovered_file(tmp_path, content))

    assert parsed.headings == (
        Heading(level=1, text="", line_number=1),
        Heading(level=2, text="Real heading", line_number=2),
    )
    assert parsed.wikilinks == ()
    assert parsed.image_links == ()


def test_parser_raises_for_unclosed_or_non_mapping_frontmatter(
    tmp_path: Path,
) -> None:
    unclosed = discovered_file(tmp_path, "---\ntitle: Note\n# Heading")
    with pytest.raises(ValueError, match="Unclosed YAML frontmatter"):
        parse_markdown_file(unclosed)

    non_mapping = discovered_file(tmp_path, "---\n- item\n---\n# Heading")
    with pytest.raises(TypeError, match="must contain a mapping"):
        parse_markdown_file(non_mapping)


def test_parser_does_not_modify_source_file(tmp_path: Path) -> None:
    content = "# Note\n\n[[RAG]]"
    source = discovered_file(tmp_path, content)
    before = source.absolute_path.stat().st_mtime_ns

    parse_markdown_file(source)

    assert source.absolute_path.read_text(encoding="utf-8") == content
    assert source.absolute_path.stat().st_mtime_ns == before
