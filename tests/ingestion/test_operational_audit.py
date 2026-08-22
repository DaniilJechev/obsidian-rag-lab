"""Unit tests for Sprint 6 operational metric calculations."""

from datetime import UTC, datetime

from rag_based_on_obsidian.ingestion.contracts import RunCounters
from rag_based_on_obsidian.ingestion.operational_audit import (
    _duration_seconds,
)


def test_duration_seconds_is_calculated_from_observed_timestamps() -> None:
    started = datetime(2026, 8, 13, 10, 0, 0, tzinfo=UTC)
    finished = datetime(2026, 8, 13, 10, 0, 2, 500_000, tzinfo=UTC)

    assert _duration_seconds(started, finished) == 2.5


def test_unfinished_run_has_no_duration() -> None:
    started = datetime(2026, 8, 13, 10, 0, 0, tzinfo=UTC)

    assert _duration_seconds(started, None) is None


def test_empty_counters_have_zero_safe_success_rate() -> None:
    counters = RunCounters()
    processed = counters.new + counters.changed + counters.unchanged

    success_rate = processed / counters.total if counters.total else 0.0

    assert success_rate == 0.0
