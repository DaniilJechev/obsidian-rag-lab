"""ingestion_states_by_note is the per-note audit table in Core metadata."""

from rag_based_on_obsidian.db.schema import ingestion_states_by_note, metadata


def test_ingestion_states_by_note_table_is_registered() -> None:
    assert "ingestion_states_by_note" in metadata.tables
    assert "ingestion_states" not in metadata.tables
    column_names = {column.name for column in ingestion_states_by_note.columns}
    assert column_names == {
        "state_id",
        "note_id",
        "run_id",
        "index_version_id",
        "content_hash",
        "parser_version",
        "status",
        "error_type",
        "error_message",
        "processed_at",
        "created_at",
    }
