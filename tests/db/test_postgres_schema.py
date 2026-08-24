"""Integration tests for the PostgreSQL schema."""

import os
from pathlib import Path, PurePosixPath

import pytest
from sqlalchemy import create_engine, delete, func, insert, select
from sqlalchemy.exc import IntegrityError

from rag_based_on_obsidian.config import ENV_FILE
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.db.schema import (
    chunks,
    index_versions,
    ingestion_runs,
    ingestion_states_by_note,
    note_links,
    notes,
)
from rag_based_on_obsidian.ingestion.orchestrator import run_ingestion

pytestmark = pytest.mark.manual


@pytest.fixture
def database_connection():
    """Yield a PostgreSQL connection and roll back test data afterward."""
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    if not os.environ.get("POSTGRES_PASSWORD"):
        pytest.skip("POSTGRES_PASSWORD is required for PostgreSQL tests")

    engine = create_engine(load_database_url())

    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()

    engine.dispose()


def make_note(path: str) -> dict[str, object]:
    """Build the smallest valid notes row for integration tests."""
    return {
        "relative_path": path,
        "source_directory": "DLS2",
        "title": "Integration test note",
        "content_hash": f"hash:{path}",
        "file_size_bytes": 10,
        "character_count": 10,
        "word_count": 2,
        "parse_status": "parsed",
        "parser_version": "test",
    }


def test_notes_reject_invalid_values(database_connection) -> None:
    """CHECK constraints reject negative sizes and unknown parse statuses."""
    invalid_size = make_note("tests/invalid-size.md")
    invalid_size["file_size_bytes"] = -1
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(insert(notes).values(**invalid_size))

    invalid_status = make_note("tests/invalid-status.md")
    invalid_status["parse_status"] = "unknown"
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(insert(notes).values(**invalid_status))


def test_notes_relative_path_is_unique(database_connection) -> None:
    """The same relative path cannot be inserted twice."""
    row = make_note("tests/duplicate.md")
    database_connection.execute(insert(notes).values(**row))

    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(insert(notes).values(**row))


def test_note_links_cascade_and_set_null(database_connection) -> None:
    """Source deletion cascades; target deletion preserves an unresolved link."""
    source_id = database_connection.execute(
        insert(notes).values(**make_note("tests/source.md")).returning(notes.c.note_id)
    ).scalar_one()
    target_id = database_connection.execute(
        insert(notes).values(**make_note("tests/target.md")).returning(notes.c.note_id)
    ).scalar_one()

    database_connection.execute(
        insert(note_links).values(
            source_note_id=source_id,
            target_note_id=target_id,
            target_reference="tests/target",
            display_text="Target",
            link_type="wikilink",
        )
    )
    database_connection.execute(
        insert(note_links).values(
            source_note_id=source_id,
            target_note_id=target_id,
            target_reference="tests/target-2",
            display_text=None,
            link_type="wikilink",
        )
    )

    database_connection.execute(delete(notes).where(notes.c.note_id == target_id))
    unresolved = database_connection.execute(
        select(note_links.c.target_note_id).where(
            note_links.c.source_note_id == source_id
        )
    ).all()
    assert unresolved == [(None,), (None,)]

    database_connection.execute(delete(notes).where(notes.c.note_id == source_id))
    remaining_links = database_connection.execute(
        select(note_links.c.link_id).where(
            note_links.c.source_note_id == source_id
        )
    ).all()
    assert remaining_links == []


def test_note_links_reject_unknown_source(database_connection) -> None:
    """A link must reference an existing source note."""
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            insert(note_links).values(
                source_note_id=999_999_999,
                target_note_id=None,
                target_reference="missing",
                display_text=None,
                link_type="wikilink",
            )
        )


def test_ingestion_persists_and_resolves_wikilinks(
    database_connection,
    tmp_path: Path,
) -> None:
    """Ingestion stores aliases, resolves targets and remains idempotent."""
    source_path = tmp_path / "source.md"
    target_path = tmp_path / "target.md"
    source_path.write_text(
        "# Source\n[[DLS2/target#Section|Target note]] [[target]] [[Missing note]]",
        encoding="utf-8",
    )
    target_path.write_text("# Target\nContent.", encoding="utf-8")
    discovered = [
        DiscoveredFile(source_path, PurePosixPath("DLS2/source.md")),
        DiscoveredFile(target_path, PurePosixPath("DLS2/target.md")),
    ]

    first = run_ingestion(
        database_connection,
        discovered,
        corpus_scope="DLS2",
    )
    second = run_ingestion(
        database_connection,
        discovered,
        corpus_scope="DLS2",
    )

    assert first.new == 2
    assert second.unchanged == 2
    target_id = database_connection.scalar(
        select(notes.c.note_id).where(notes.c.relative_path == "DLS2/target.md")
    )
    rows = database_connection.execute(
        select(
            note_links.c.target_reference,
            note_links.c.target_note_id,
            note_links.c.display_text,
        )
        .join(notes, note_links.c.source_note_id == notes.c.note_id)
        .where(notes.c.relative_path == "DLS2/source.md")
        .order_by(note_links.c.target_reference)
    ).all()
    assert rows == [
        ("DLS2/target#Section", target_id, "Target note"),
        ("Missing note", None, None),
        ("target", target_id, None),
    ]
    assert database_connection.scalar(
        select(func.count())
        .select_from(note_links)
        .join(notes, note_links.c.source_note_id == notes.c.note_id)
        .where(notes.c.relative_path == "DLS2/source.md")
    ) == 3


def test_ingestion_states_by_note_require_valid_status_and_relationships(
    database_connection,
) -> None:
    """State rows enforce status values and parent foreign keys."""
    note_id = database_connection.execute(
        insert(notes)
        .values(**make_note("tests/state.md"))
        .returning(notes.c.note_id)
    ).scalar_one()
    run_id = database_connection.execute(
        insert(ingestion_runs).values(
            corpus_scope="DLS2",
            status="running",
        ).returning(ingestion_runs.c.run_id)
    ).scalar_one()
    index_version_id = database_connection.execute(
        insert(index_versions).values(
            parser_version="test",
            chunking_version="test",
        ).returning(index_versions.c.index_version_id)
    ).scalar_one()

    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            insert(ingestion_states_by_note).values(
                note_id=note_id,
                run_id=run_id,
                index_version_id=index_version_id,
                content_hash="hash",
                parser_version="test",
                status="unknown",
            )
        )

    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            insert(ingestion_states_by_note).values(
                note_id=note_id,
                run_id=run_id,
                index_version_id=999_999_999,
                content_hash="hash",
                parser_version="test",
                status="discovered",
            )
        )


def test_ingestion_runs_reject_negative_counters(database_connection) -> None:
    """Run counters cannot contain negative values."""
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(
            insert(ingestion_runs).values(
                corpus_scope="DLS2",
                status="running",
                documents_total=-1,
            )
        )


def test_ingestion_is_idempotent_and_reprocesses_parser_changes(
    database_connection,
    tmp_path: Path,
) -> None:
    """Repeated input creates no note duplicates and parser changes reprocess."""
    source_path = tmp_path / "Sprint6Idempotency" / "idempotent.md"
    source_path.parent.mkdir()
    source_path.write_text("# Idempotent\nText.", encoding="utf-8")
    discovered = DiscoveredFile(
        absolute_path=source_path,
        relative_path=PurePosixPath("Sprint6Idempotency/idempotent.md"),
    )

    first = run_ingestion(
        database_connection,
        [discovered],
        corpus_scope="Sprint6Idempotency",
        parser_version="parser-v1",
    )
    second = run_ingestion(
        database_connection,
        [discovered],
        corpus_scope="Sprint6Idempotency",
        parser_version="parser-v1",
    )
    parser_changed = run_ingestion(
        database_connection,
        [discovered],
        corpus_scope="Sprint6Idempotency",
        parser_version="parser-v2",
    )

    assert first.new == 1
    assert second.unchanged == 1
    assert parser_changed.changed == 1
    assert database_connection.scalar(
        select(func.count()).select_from(notes).where(
            notes.c.relative_path == "Sprint6Idempotency/idempotent.md"
        )
    ) == 1
    assert database_connection.scalar(
        select(func.count())
        .select_from(ingestion_states_by_note)
        .join(notes, ingestion_states_by_note.c.note_id == notes.c.note_id)
        .where(notes.c.relative_path == "Sprint6Idempotency/idempotent.md")
    ) == 3


def test_failed_note_isolated_and_stale_note_recorded(
    database_connection,
    tmp_path: Path,
) -> None:
    """A parse failure does not abort the batch; missing notes become stale."""
    valid_path = tmp_path / "Sprint6Failure" / "valid.md"
    failed_path = tmp_path / "Sprint6Failure" / "failed.md"
    valid_path.parent.mkdir()
    valid_path.write_text("# Valid\nText.", encoding="utf-8")
    failed_path.write_text("---\ntitle: [unclosed\n", encoding="utf-8")
    discovered = [
        DiscoveredFile(valid_path, PurePosixPath("Sprint6Failure/valid.md")),
        DiscoveredFile(failed_path, PurePosixPath("Sprint6Failure/failed.md")),
    ]

    first = run_ingestion(
        database_connection,
        discovered,
        corpus_scope="Sprint6Failure",
    )
    second = run_ingestion(
        database_connection,
        [discovered[0]],
        corpus_scope="Sprint6Failure",
    )

    assert first.new == 1
    assert first.failed == 1
    assert second.stale == 1
    assert database_connection.scalar(
        select(func.count())
        .select_from(ingestion_states_by_note)
        .where(ingestion_states_by_note.c.status == "failed")
    ) == 1
    assert database_connection.scalar(
        select(func.count())
        .select_from(ingestion_states_by_note)
        .where(ingestion_states_by_note.c.status == "stale")
    ) == 1


def test_failed_note_is_retried_after_source_is_fixed(
    database_connection,
    tmp_path: Path,
) -> None:
    """A failed attempt must not make a later successful retry look unchanged."""
    source_path = tmp_path / "Sprint6Retry" / "retry.md"
    source_path.parent.mkdir()
    source_path.write_text("---\ntitle: [unclosed\n", encoding="utf-8")
    discovered = DiscoveredFile(
        source_path,
        PurePosixPath("Sprint6Retry/retry.md"),
    )

    failed = run_ingestion(
        database_connection,
        [discovered],
        corpus_scope="Sprint6Retry",
    )
    source_path.write_text("# Fixed\nText.", encoding="utf-8")
    retried = run_ingestion(
        database_connection,
        [discovered],
        corpus_scope="Sprint6Retry",
    )

    assert failed.failed == 1
    assert retried.changed == 1
    assert database_connection.scalar(
        select(notes.c.parse_status).where(
            notes.c.relative_path == "Sprint6Retry/retry.md"
        )
    ) == "parsed"


def test_sprint6_version_mismatch_and_scope_aware_stale(
    database_connection,
    tmp_path: Path,
) -> None:
    """Parser changes reprocess notes and scoped stale excludes other corpora."""
    dls1_path = tmp_path / "Sprint6ScopeA" / "scope.md"
    dls2_path = tmp_path / "Sprint6ScopeB" / "other.md"
    dls1_path.parent.mkdir()
    dls2_path.parent.mkdir()
    dls1_path.write_text("# Scope\nText.", encoding="utf-8")
    dls2_path.write_text("# Other\nText.", encoding="utf-8")
    dls1_file = DiscoveredFile(
        dls1_path,
        PurePosixPath("Sprint6ScopeA/scope.md"),
    )
    dls2_file = DiscoveredFile(
        dls2_path,
        PurePosixPath("Sprint6ScopeB/other.md"),
    )

    first = run_ingestion(
        database_connection,
        [dls1_file, dls2_file],
        corpus_scope="Sprint6ScopeA,Sprint6ScopeB",
        parser_version="parser-v1",
    )
    version_changed = run_ingestion(
        database_connection,
        [dls1_file, dls2_file],
        corpus_scope="Sprint6ScopeA,Sprint6ScopeB",
        parser_version="parser-v2",
    )
    dls1_only = run_ingestion(
        database_connection,
        [dls1_file],
        corpus_scope="Sprint6ScopeA",
        parser_version="parser-v2",
    )

    assert first.new == 2
    assert version_changed.changed == 2
    assert dls1_only.unchanged == 1
    assert dls1_only.stale == 0
    assert database_connection.scalar(
        select(func.count())
        .select_from(notes)
        .where(
            notes.c.relative_path.in_(
                ("Sprint6ScopeA/scope.md", "Sprint6ScopeB/other.md")
            )
        )
    ) == 2


def test_chunks_require_valid_note_and_unique_position(database_connection) -> None:
    """Chunks require a note and have one position per chunking version."""
    note_id = database_connection.execute(
        insert(notes)
        .values(**make_note("tests/chunks.md"))
        .returning(notes.c.note_id)
    ).scalar_one()
    chunk = {
        "note_id": note_id,
        "chunk_index": 0,
        "text": "chunk",
        "section_type": "paragraph",
        "word_count": 1,
        "token_count": 1,
        "chunking_version": "test",
    }
    database_connection.execute(insert(chunks).values(**chunk))

    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(insert(chunks).values(**chunk))

    invalid_chunk = dict(chunk)
    invalid_chunk["note_id"] = 999_999_999
    invalid_chunk["chunk_index"] = 1
    with pytest.raises(IntegrityError), database_connection.begin_nested():
        database_connection.execute(insert(chunks).values(**invalid_chunk))
