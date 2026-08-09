"""Read-only discovery of Markdown files inside the configured corpus."""

from collections.abc import Iterator, Sequence
from pathlib import Path, PurePosixPath
import warnings

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile


def discover_markdown_files(
    vault_root: Path,
    allowed_directories: Sequence[str] = ("DLS1", "DLS2"),
) -> list[DiscoveredFile]:
    """Return deterministic metadata for allowed Markdown files.

    Missing allowed directories produce warnings and are skipped. Permission
    errors are propagated because silently returning a partial corpus is unsafe.
    Symbolic links are skipped with warnings and are never followed.
    """

    resolved_vault_root = _validate_vault_root(vault_root)
    discovered_files: list[DiscoveredFile] = []

    for directory_name in allowed_directories:
        _validate_allowed_directory_name(directory_name)
        allowed_directory = resolved_vault_root / directory_name

        if not allowed_directory.exists():
            warnings.warn(
                f"Allowed corpus directory is missing: {directory_name}",
                UserWarning,
                stacklevel=2,
            )
            continue

        if allowed_directory.is_symlink():
            warnings.warn(
                f"Skipping symbolic link allowed directory: {allowed_directory}",
                UserWarning,
                stacklevel=2,
            )
            continue

        if not allowed_directory.is_dir():
            raise NotADirectoryError(
                f"Allowed corpus path is not a directory: {allowed_directory}"
            )

        for file_path in _iter_regular_markdown_files(allowed_directory):
            relative_path = PurePosixPath(
                file_path.relative_to(resolved_vault_root).as_posix()
            )
            discovered_files.append(
                DiscoveredFile(
                    absolute_path=file_path,
                    relative_path=relative_path,
                )
            )

    return sorted(discovered_files, key=lambda item: item.relative_path.as_posix())


def _validate_vault_root(vault_root: Path) -> Path:
    """Resolve and validate the vault root before reading it."""

    resolved_vault_root = vault_root.expanduser().resolve(strict=True)
    if not resolved_vault_root.is_dir():
        raise NotADirectoryError(
            f"Obsidian vault root is not a directory: {resolved_vault_root}"
        )
    return resolved_vault_root


def _validate_allowed_directory_name(directory_name: str) -> None:
    """Reject allowlist entries that could escape the vault root."""

    directory_path = Path(directory_name)
    if (
        not directory_name
        or directory_path.is_absolute()
        or len(directory_path.parts) != 1
        or directory_path in {Path("."), Path("..")}
    ):
        raise ValueError(
            "Allowed directory must be one direct child directory name: "
            f"{directory_name!r}"
        )


def _iter_regular_markdown_files(directory: Path) -> Iterator[Path]:
    """Recursively yield regular ``.md`` files without following symlinks."""

    try:
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except PermissionError:
        raise

    for entry in entries:
        if entry.is_symlink():
            warnings.warn(
                f"Skipping symbolic link during corpus discovery: {entry}",
                UserWarning,
                stacklevel=3,
            )
            continue

        if entry.is_dir():
            yield from _iter_regular_markdown_files(entry)
        elif entry.is_file() and entry.suffix == ".md":
            yield entry.resolve(strict=True)
