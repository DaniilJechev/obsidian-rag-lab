"""Entities used at the corpus discovery boundary."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class DiscoveredFile:
    """A Markdown file accepted by the corpus discovery boundary."""

    absolute_path: Path
    relative_path: PurePosixPath
