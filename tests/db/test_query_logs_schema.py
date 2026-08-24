"""query_logs is part of the SQLAlchemy Core metadata."""

from rag_based_on_obsidian.db.schema import metadata, query_logs


def test_query_logs_table_is_registered() -> None:
    assert "query_logs" in metadata.tables
    column_names = {column.name for column in query_logs.columns}
    assert column_names == {
        "query_log_id",
        "created_at",
        "query",
        "method",
        "top_k",
        "latency_ms",
        "result_count",
        "error",
    }


def test_query_logs_created_at_default_is_sql_now() -> None:
    default = query_logs.c.created_at.server_default
    assert default is not None
    assert str(default.arg).lower() == "now()"
