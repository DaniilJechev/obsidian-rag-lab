"""Manual PostgreSQL tests for versioned chunk persistence."""

import os

import pytest
from sqlalchemy import create_engine, insert

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.chunking.records import ChunkRecord
from rag_based_on_obsidian.config import ENV_FILE
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.db.schema import notes

pytestmark = pytest.mark.manual


@pytest.fixture
def database_connection():
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


def make_record(note_id: int, version: str, index: int = 0) -> ChunkRecord:
    text = f"# Retrieval\n\nchunk {index}"
    return ChunkRecord(
        note_id=note_id,
        chunk_index=index,
        text=text,
        section_id="section-1",
        section_title="Retrieval",
        section_level=1,
        section_path=("Retrieval",),
        section_type="heading",
        start_offset=index,
        end_offset=index + len(text),
        word_count=3,
        token_count=4,
        parser_version="parser-v1",
        source_content_hash="hash:note",
        chunking_version=version,
    )


def test_chunk_generation_is_idempotent_and_versioned(database_connection) -> None:
    note_id = database_connection.execute(
        insert(notes)
        .values(
            relative_path="tests/chunk-persistence.md",
            source_directory="DLS2",
            title="Chunk persistence",
            content_hash="hash:note",
            file_size_bytes=10,
            character_count=10,
            word_count=2,
            parse_status="parsed",
            parser_version="parser-v1",
        )
        .returning(notes.c.note_id)
    ).scalar_one()
    repository = ChunkRepository(database_connection)

    repository.replace_generation(
        [make_record(note_id, "chunk-v1", 0), make_record(note_id, "chunk-v1", 1)]
    )
    repository.replace_generation([make_record(note_id, "chunk-v1", 0)])
    repository.replace_generation([make_record(note_id, "chunk-v2")])

    first_version = repository.list_generation(
        note_id=note_id,
        chunking_version="chunk-v1",
    )
    second_version = repository.list_generation(
        note_id=note_id,
        chunking_version="chunk-v2",
    )

    assert len(first_version) == 1
    assert len(second_version) == 1
    assert first_version[0]["chunking_version"] == "chunk-v1"
    assert second_version[0]["chunking_version"] == "chunk-v2"
