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
    ingestion_states,
    note_links,
    notes,
)
from rag_based_on_obsidian.ingestion.orchestrator import run_ingestion


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


def test_ingestion_states_require_valid_status_and_relationships(
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
            insert(ingestion_states).values(
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
            insert(ingestion_states).values(
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
    source_path = tmp_path / "DLS2" / "idempotent.md"
    source_path.parent.mkdir()
    source_path.write_text("# Idempotent\nText.", encoding="utf-8")
    discovered = DiscoveredFile(
        absolute_path=source_path,
        relative_path=PurePosixPath("DLS2/idempotent.md"),
    )

    first = run_ingestion(
        database_connection,
        [discovered],
        parser_version="parser-v1",
    )
    second = run_ingestion(
        database_connection,
        [discovered],
        parser_version="parser-v1",
    )
    parser_changed = run_ingestion(
        database_connection,
        [discovered],
        parser_version="parser-v2",
    )

    assert first.new == 1
    assert second.unchanged == 1
    assert parser_changed.changed == 1
    assert database_connection.scalar(
        select(func.count()).select_from(notes).where(
            notes.c.relative_path == "DLS2/idempotent.md"
        )
    ) == 1
    assert database_connection.scalar(
        select(func.count()).select_from(ingestion_states)
    ) == 3


def test_failed_note_isolated_and_stale_note_recorded(
    database_connection,
    tmp_path: Path,
) -> None:
    """A parse failure does not abort the batch; missing notes become stale."""
    valid_path = tmp_path / "DLS2" / "valid.md"
    failed_path = tmp_path / "DLS2" / "failed.md"
    valid_path.parent.mkdir()
    valid_path.write_text("# Valid\nText.", encoding="utf-8")
    failed_path.write_text("---\ntitle: [unclosed\n", encoding="utf-8")
    discovered = [
        DiscoveredFile(valid_path, PurePosixPath("DLS2/valid.md")),
        DiscoveredFile(failed_path, PurePosixPath("DLS2/failed.md")),
    ]

    first = run_ingestion(database_connection, discovered)
    second = run_ingestion(
        database_connection,
        [discovered[0]],
    )

    assert first.new == 1
    assert first.failed == 1
    assert second.stale == 1
    assert database_connection.scalar(
        select(func.count())
        .select_from(ingestion_states)
        .where(ingestion_states.c.status == "failed")
    ) == 1
    assert database_connection.scalar(
        select(func.count())
        .select_from(ingestion_states)
        .where(ingestion_states.c.status == "stale")
    ) == 1


def test_failed_note_is_retried_after_source_is_fixed(
    database_connection,
    tmp_path: Path,
) -> None:
    """A failed attempt must not make a later successful retry look unchanged."""
    source_path = tmp_path / "DLS2" / "retry.md"
    source_path.parent.mkdir()
    source_path.write_text("---\ntitle: [unclosed\n", encoding="utf-8")
    discovered = DiscoveredFile(
        source_path,
        PurePosixPath("DLS2/retry.md"),
    )

    failed = run_ingestion(database_connection, [discovered])
    source_path.write_text("# Fixed\nText.", encoding="utf-8")
    retried = run_ingestion(database_connection, [discovered])

    assert failed.failed == 1
    assert retried.changed == 1
    assert database_connection.scalar(
        select(notes.c.parse_status).where(
            notes.c.relative_path == "DLS2/retry.md"
        )
    ) == "parsed"


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
