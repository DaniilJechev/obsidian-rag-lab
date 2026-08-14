"""Immutable logical Markdown block contracts."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BlockType(StrEnum):
    """Supported logical Markdown block categories."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE = "code"
    LIST = "list"
    TABLE = "table"
    PRE_HEADING = "pre_heading"


@dataclass(frozen=True)
class MarkdownBlock:
    """One ordered source span with a semantic Markdown type."""

    block_id: str
    block_type: BlockType
    text: str
    start_offset: int
    end_offset: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate source-span invariants at the domain boundary."""
        if self.start_offset < 0:
            raise ValueError("start_offset must be non-negative")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be >= start_offset")

