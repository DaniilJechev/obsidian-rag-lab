"""Pure idempotency decision logic."""

from rag_based_on_obsidian.ingestion.contracts import (
    DecisionResult,
    IncomingNote,
    IngestionDecision,
    PreviousNoteState,
)


def decide_note_action(
    incoming: IncomingNote,
    previous: PreviousNoteState | None,
) -> DecisionResult:
    """Classify one note without database access or side effects.

    A missing previous state is a new note. Existing content with a different
    parser version is changed because the derived representation is stale even
    when the source bytes are identical.
    """
    if incoming.parse_status != "parsed":
        return DecisionResult(
            decision=IngestionDecision.FAILED,
            reason="incoming_note_failed_to_parse",
            should_process=False,
        )
    if previous is None:
        return DecisionResult(
            decision=IngestionDecision.NEW,
            reason="no_persisted_note_at_relative_path",
            should_process=True,
        )
    if previous.last_status == IngestionDecision.FAILED.value:
        return DecisionResult(
            decision=IngestionDecision.CHANGED,
            reason="previous_attempt_failed_and_requires_retry",
            should_process=True,
        )
    if (
        previous.content_hash == incoming.content_hash
        and previous.parser_version == incoming.parser_version
    ):
        return DecisionResult(
            decision=IngestionDecision.UNCHANGED,
            reason="content_and_parser_version_match",
            should_process=False,
        )
    return DecisionResult(
        decision=IngestionDecision.CHANGED,
        reason="content_or_parser_version_changed",
        should_process=True,
    )