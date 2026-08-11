from collections import Counter
from pathlib import Path

import pytest

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.corpus.inventory import build_corpus_inventory
from rag_based_on_obsidian.corpus.serialization import write_inventory_json


@pytest.mark.manual
def test_real_vault_inventory_is_read_only() -> None:
    """Build the real-vault inventory and verify source fingerprints."""

    config = load_config()
    discovered_files = discover_markdown_files(
        config.vault_root,
        config.allowed_corpus_directories,
    )
    before = {
        item.absolute_path: _file_fingerprint(item.absolute_path)
        for item in discovered_files
    }

    inventory = build_corpus_inventory(
        discovered_files,
        allowed_directories=config.allowed_corpus_directories,
        show_progress=True,
    )
    output_path = Path("artifacts/corpus_inventory.json")
    write_inventory_json(inventory, output_path)

    after = {
        path: _file_fingerprint(path)
        for path in before
    }
    anomaly_counts = Counter(
        anomaly
        for document in inventory.documents
        for anomaly in document.anomalies
    )

    print(f"Discovered files: {inventory.summary.documents_total}")
    print(f"Parsed files: {inventory.summary.documents_parsed}")
    print(f"Failed files: {inventory.summary.documents_failed}")
    print(f"Duplicate groups: {inventory.summary.duplicate_groups}")
    print(f"Duplicate documents: {inventory.summary.duplicate_documents}")
    print(f"Anomalies: {dict(anomaly_counts)}")
    print(f"Inventory artifact: {output_path}")
    print("Vault modified: no" if before == after else "Vault modified: yes")

    assert inventory.summary.documents_total == len(discovered_files)
    assert before == after


def _file_fingerprint(path: Path) -> tuple[int, int]:
    """Return metadata used to detect accidental writes to the vault."""

    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns
