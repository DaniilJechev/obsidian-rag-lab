"""Immutable contracts shared by ingestion decision and orchestration layers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from rag_based_on_obsidian.corpus.inventory_entities import (
    DocumentStatistics,
)
from rag_based_on_obsidian.corpus.markdown_entities import Wikilink


class IngestionDecision(StrEnum):
    """Business-level outcome for one incoming document."""

    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    STALE = "stale"
    FAILED = "failed"


@dataclass(frozen=True)
class PreviousNoteState:
    """Latest persisted identity fields required for idempotency."""

    note_id: int
    relative_path: str
    content_hash: str
    parser_version: str
    last_status: str | None = None


@dataclass(frozen=True)
class IncomingNote:
    """Database-ready note metadata derived from parser/statistics output."""

    relative_path: str
    source_directory: str
    title: str
    content_hash: str
    file_size_bytes: int
    character_count: int
    word_count: int
    parse_status: str
    language_statistics: dict[str, Any]
    anomalies: list[str]
    parser_version: str
    source_mtime: datetime | None = None
    wikilinks: tuple[Wikilink, ...] = ()

    @classmethod
    def from_statistics(
        cls,
        statistics: DocumentStatistics,
        *,
        parser_version: str,
        wikilinks: tuple[Wikilink, ...] = (),
    ) -> "IncomingNote":
        """Convert the existing inventory contract into a DB write contract."""
        if statistics.content_hash is None:
            raise ValueError("Parsed document must have content_hash")

        relative_path = statistics.source.relative_path.as_posix()
        source_directory = PurePosixPath(relative_path).parts[0]
        return cls(
            relative_path=relative_path,
            source_directory=source_directory,
            title=statistics.source.absolute_path.stem,
            content_hash=statistics.content_hash,
            file_size_bytes=statistics.file_size_bytes,
            character_count=statistics.character_count,
            word_count=statistics.word_count,
            parse_status="parsed"
            if statistics.parse_status == "ok"
            else "failed",
            language_statistics={
                "russian_word_count": statistics.language_statistics.russian_word_count,
                "english_word_count": statistics.language_statistics.english_word_count,
                "mixed_or_other_word_count": (
                    statistics.language_statistics.mixed_or_other_word_count
                ),
                "unknown_word_count": statistics.language_statistics.unknown_word_count,
            },
            anomalies=list(statistics.anomalies),
            parser_version=parser_version,
            wikilinks=wikilinks,
        )


@dataclass(frozen=True)
class DecisionResult:
    """Decision plus an explanation suitable for state/error accounting."""

    decision: IngestionDecision
    reason: str
    should_process: bool


@dataclass
class RunCounters:
    """Mutable counters accumulated during one ingestion run."""

    total: int = 0
    new: int = 0
    changed: int = 0
    unchanged: int = 0
    stale: int = 0
    failed: int = 0

    def increment(self, decision: IngestionDecision) -> None:
        """Increment the counter matching one document decision."""
        setattr(self, decision.value, getattr(self, decision.value) + 1)

    def as_dict(self) -> dict[str, int]:
        """Return counters using the names persisted by ingestion orchestration."""
        return {
            "total": self.total,
            "new": self.new,
            "changed": self.changed,
            "unchanged": self.unchanged,
            "stale": self.stale,
            "failed": self.failed,
        }
