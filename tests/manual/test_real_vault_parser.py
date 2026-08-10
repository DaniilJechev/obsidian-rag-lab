from collections import Counter
from pathlib import Path

import pytest

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


@pytest.mark.manual
def test_real_vault_parser_is_read_only() -> None:
    """Smoke-test parser compatibility with the configured external vault."""

    config = load_config()
    discovered_files = discover_markdown_files(
        config.vault_root,
        config.allowed_corpus_directories,
    )
    before = {
        item.absolute_path: _file_fingerprint(item.absolute_path)
        for item in discovered_files
    }

    parsed_documents = [
        parse_markdown_file(discovered_file)
        for discovered_file in discovered_files
    ]

    after = {
        path: _file_fingerprint(path)
        for path in before
    }
    counts = Counter(
        (
            bool(document.frontmatter),
            bool(document.headings),
            bool(document.wikilinks),
            bool(document.image_links),
        )
        for document in parsed_documents
    )
    empty_documents = sum(not document.raw_text.strip() for document in parsed_documents)

    print(f"Discovered files: {len(discovered_files)}")
    print(f"Parsed files: {len(parsed_documents)}")
    print(f"Files with frontmatter: {sum(key[0] * value for key, value in counts.items())}")
    print(f"Files with headings: {sum(key[1] * value for key, value in counts.items())}")
    print(f"Files with wikilinks: {sum(key[2] * value for key, value in counts.items())}")
    print(f"Files with image links: {sum(key[3] * value for key, value in counts.items())}")
    print(f"Empty files: {empty_documents}")
    print("Vault modified: no" if before == after else "Vault modified: yes")

    assert len(parsed_documents) == len(discovered_files)
    assert before == after


def _file_fingerprint(path: Path) -> tuple[int, int]:
    """Return non-content metadata used to detect accidental writes."""

    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns
