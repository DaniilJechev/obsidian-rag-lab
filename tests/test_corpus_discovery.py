from pathlib import Path

import pytest

from rag_based_on_obsidian.corpus.discovery import discover_markdown_files


def create_vault(tmp_path: Path) -> Path:
    """Create a small isolated vault fixture for discovery tests."""

    (tmp_path / "DLS1" / "nested").mkdir(parents=True)
    (tmp_path / "DLS2").mkdir()
    (tmp_path / "Private").mkdir()
    (tmp_path / "DLS1_backup").mkdir()

    (tmp_path / "DLS1" / "Encoder.md").write_text("encoder", encoding="utf-8")
    (tmp_path / "DLS1" / "nested" / "BERT.md").write_text(
        "bert",
        encoding="utf-8",
    )
    (tmp_path / "DLS1" / "ignore.txt").write_text("ignore", encoding="utf-8")
    (tmp_path / "DLS2" / "RAG.md").write_text("rag", encoding="utf-8")
    (tmp_path / "Private" / "secret.md").write_text("secret", encoding="utf-8")
    (tmp_path / "DLS1_backup" / "old.md").write_text("old", encoding="utf-8")
    return tmp_path


def test_discovery_returns_only_sorted_markdown_files_in_allowlist(
    tmp_path: Path,
) -> None:
    vault_root = create_vault(tmp_path)

    discovered_files = discover_markdown_files(
        vault_root,
        allowed_directories=("DLS1", "DLS2"),
    )

    assert [file.relative_path.as_posix() for file in discovered_files] == [
        "DLS1/Encoder.md",
        "DLS1/nested/BERT.md",
        "DLS2/RAG.md",
    ]
    assert all(file.absolute_path.is_absolute() for file in discovered_files)


def test_missing_allowed_directory_warns_and_continues(tmp_path: Path) -> None:
    (tmp_path / "DLS2").mkdir()
    (tmp_path / "DLS2" / "RAG.md").write_text("rag", encoding="utf-8")

    with pytest.warns(UserWarning, match="DLS1"):
        discovered_files = discover_markdown_files(
            tmp_path,
            allowed_directories=("DLS1", "DLS2"),
        )

    assert [file.relative_path.as_posix() for file in discovered_files] == [
        "DLS2/RAG.md"
    ]


def test_invalid_allowlist_path_is_rejected(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)

    with pytest.raises(ValueError, match="direct child directory name"):
        discover_markdown_files(tmp_path, allowed_directories=("../Private",))


def test_missing_vault_root_is_rejected(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        discover_markdown_files(missing_root)
