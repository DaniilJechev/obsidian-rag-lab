"""Unit tests for idempotent ingestion contracts and decision logic."""

from rag_based_on_obsidian.ingestion.contracts import (
    IncomingNote,
    IngestionDecision,
    PreviousNoteState,
    RunCounters,
)
from rag_based_on_obsidian.ingestion.decision import decide_note_action


def incoming(
    *,
    content_hash: str = "hash-1",
    parser_version: str = "parser-v1",
    parse_status: str = "parsed",
) -> IncomingNote:
    """Build the smallest valid incoming note contract."""
    return IncomingNote(
        relative_path="DLS2/note.md",
        source_directory="DLS2",
        title="note",
        content_hash=content_hash,
        file_size_bytes=10,
        character_count=10,
        word_count=2,
        parse_status=parse_status,
        language_statistics={},
        anomalies=[],
        parser_version=parser_version,
    )


def previous(
    *,
    content_hash: str = "hash-1",
    parser_version: str = "parser-v1",
) -> PreviousNoteState:
    """Build the smallest persisted note identity."""
    return PreviousNoteState(
        note_id=1,
        relative_path="DLS2/note.md",
        content_hash=content_hash,
        parser_version=parser_version,
    )


def test_missing_previous_state_is_new() -> None:
    result = decide_note_action(incoming(), None)

    assert result.decision is IngestionDecision.NEW
    assert result.should_process is True


def test_matching_content_and_parser_is_unchanged() -> None:
    result = decide_note_action(incoming(), previous())

    assert result.decision is IngestionDecision.UNCHANGED
    assert result.should_process is False


def test_content_change_is_changed() -> None:
    result = decide_note_action(
        incoming(content_hash="hash-2"),
        previous(),
    )

    assert result.decision is IngestionDecision.CHANGED
    assert result.should_process is True


def test_parser_version_change_is_changed() -> None:
    result = decide_note_action(
        incoming(parser_version="parser-v2"),
        previous(),
    )

    assert result.decision is IngestionDecision.CHANGED
    assert result.should_process is True


def test_parse_failure_is_failed() -> None:
    result = decide_note_action(
        incoming(parse_status="failed"),
        previous(),
    )

    assert result.decision is IngestionDecision.FAILED
    assert result.should_process is False


def test_counters_track_decisions() -> None:
    counters = RunCounters(total=5)

    for decision in (
        IngestionDecision.NEW,
        IngestionDecision.CHANGED,
        IngestionDecision.UNCHANGED,
        IngestionDecision.STALE,
        IngestionDecision.FAILED,
    ):
        counters.increment(decision)

    assert counters.as_dict() == {
        "total": 5,
        "new": 1,
        "changed": 1,
        "unchanged": 1,
        "stale": 1,
        "failed": 1,
    }
