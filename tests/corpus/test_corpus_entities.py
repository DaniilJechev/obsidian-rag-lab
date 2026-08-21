from pathlib import Path, PurePosixPath

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile


def test_discovered_file_preserves_absolute_and_normalized_relative_paths() -> None:
    discovered_file = DiscoveredFile(
        absolute_path=Path("C:/vault/DLS1/Encoder.md"),
        relative_path=PurePosixPath("DLS1/Encoder.md"),
    )

    assert discovered_file.absolute_path == Path("C:/vault/DLS1/Encoder.md")
    assert discovered_file.relative_path == PurePosixPath("DLS1/Encoder.md")
