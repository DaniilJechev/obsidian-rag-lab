import re
from collections import Counter
from pathlib import Path

import pytest

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files

EDGE_CASE_PATTERNS = {
    "wikilinks_with_heading_targets": re.compile(r"\[\[[^\]\n]+#[^\]\n]+\]\]"),
    "wikilinks_with_block_targets": re.compile(r"\[\[[^\]\n]+\^[^\]\n]+\]\]"),
    "image_embeds": re.compile(r"!\[\[[^\]\n]+\]\]"),
    "markdown_links": re.compile(r"(?<!!) \[[^\]\n]+\]\([^)]+\)", re.VERBOSE),
    "callouts": re.compile(r"(?m)^[ \t]*>[ \t]*\[![^\]\n]+\]"),
    "inline_code_wikilinks": re.compile(r"`[^`\n]*\[\[[^\]\n]+\]\][^`\n]*`"),
    "long_fenced_code_openers": re.compile(r"(?m)^[ \t]*`{4,}"),
    "obsidian_properties": re.compile(r"(?m)^---[ \t]*\r?$"),
}


@pytest.mark.manual
def test_real_vault_reports_observation_edge_cases() -> None:
    """Scan real notes for parser-relevant formats without writing artifacts."""

    config = load_config()
    discovered_files = discover_markdown_files(
        config.vault_root,
        config.allowed_corpus_directories,
    )
    before = {
        item.absolute_path: _file_fingerprint(item.absolute_path)
        for item in discovered_files
    }

    file_counts = Counter()
    total_matches = Counter()
    for discovered_file in discovered_files:
        raw_text = discovered_file.absolute_path.read_text(encoding="utf-8")
        for name, pattern in EDGE_CASE_PATTERNS.items():
            matches = pattern.findall(raw_text)
            if matches:
                file_counts[name] += 1
                total_matches[name] += len(matches)

        if "\r\n" in raw_text:
            file_counts["CRLF_line_endings"] += 1
        if any(ord(character) > 127 for character in raw_text):
            file_counts["Unicode_content"] += 1

    after = {
        path: _file_fingerprint(path)
        for path in before
    }

    print(f"Scanned files: {len(discovered_files)}")
    for name in EDGE_CASE_PATTERNS:
        print(
            f"{name}: files={file_counts[name]}, "
            f"matches={total_matches[name]}"
        )
    print(f"CRLF_line_endings: files={file_counts['CRLF_line_endings']}")
    print(f"Unicode_content: files={file_counts['Unicode_content']}")
    print(f"Vault modified: {'no' if before == after else 'yes'}")

    assert before == after


def _file_fingerprint(path: Path) -> tuple[int, int]:
    """Return file metadata used to detect accidental writes."""

    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns
