"""SQLAlchemy Core metadata for the Phase 2 PostgreSQL schema."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()


notes = Table(
    "notes",
    metadata,
    Column("note_id", BigInteger, Identity(), primary_key=True),
    Column("relative_path", Text, nullable=False, unique=True),
    Column("source_directory", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column(
        "file_size_bytes",
        BigInteger,
        nullable=False,
    ),
    Column(
        "character_count",
        Integer,
        nullable=False,
    ),
    Column(
        "word_count",
        Integer,
        nullable=False,
    ),
    Column(
        "language_statistics",
        JSONB,
        nullable=False,
        server_default="{}",
    ),
    Column(
        "parse_status",
        Text,
        nullable=False,
    ),
    Column(
        "anomalies",
        JSONB,
        nullable=False,
        server_default="[]",
    ),
    Column("source_mtime", DateTime(timezone=True), nullable=True),
    Column("parser_version", Text, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    CheckConstraint(
        "file_size_bytes >= 0",
        name="notes_file_size_bytes_check",
    ),
    CheckConstraint(
        "character_count >= 0",
        name="notes_character_count_check",
    ),
    CheckConstraint(
        "word_count >= 0",
        name="notes_word_count_check",
    ),
    CheckConstraint(
        "parse_status IN ('parsed', 'failed')",
        name="notes_parse_status_check",
    ),
)


note_links = Table(
    "note_links",
    metadata,
    Column("link_id", BigInteger, Identity(), primary_key=True),
    Column(
        "source_note_id",
        BigInteger,
        ForeignKey("notes.note_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "target_note_id",
        BigInteger,
        ForeignKey("notes.note_id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("target_reference", Text, nullable=False),
    Column("display_text", Text, nullable=True),
    Column("link_type", Text, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    UniqueConstraint(
        "source_note_id",
        "target_reference",
        "link_type",
        name="uq_note_links_source_reference_type",
    ),
)


ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    Column("run_id", BigInteger, Identity(), primary_key=True),
    Column(
        "started_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column(
        "status",
        Text,
        nullable=False,
    ),
    Column("corpus_scope", Text, nullable=False),
    Column(
        "documents_total",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "documents_succeeded",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "documents_failed",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "documents_skipped",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    CheckConstraint(
        "documents_total >= 0",
        name="ingestion_runs_documents_total_check",
    ),
    CheckConstraint(
        "documents_succeeded >= 0",
        name="ingestion_runs_documents_succeeded_check",
    ),
    CheckConstraint(
        "documents_failed >= 0",
        name="ingestion_runs_documents_failed_check",
    ),
    CheckConstraint(
        "documents_skipped >= 0",
        name="ingestion_runs_documents_skipped_check",
    ),
    CheckConstraint(
        "status IN ('running', 'completed', 'failed', 'partial')",
        name="ingestion_runs_status_check",
    ),
)


index_versions = Table(
    "index_versions",
    metadata,
    Column("index_version_id", BigInteger, Identity(), primary_key=True),
    Column("parser_version", Text, nullable=False),
    Column("chunking_version", Text, nullable=False),
    Column("embedding_model", Text, nullable=True),
    Column("embedding_version", Text, nullable=True),
    Column(
        "embedding_parameters",
        JSONB,
        nullable=False,
        server_default="{}",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    UniqueConstraint(
        "parser_version",
        "chunking_version",
        "embedding_model",
        "embedding_version",
        "embedding_parameters",
        name="uq_index_versions_identity",
    ),
)


ingestion_states_by_note = Table(
    "ingestion_states_by_note",
    metadata,
    Column("state_id", BigInteger, Identity(), primary_key=True),
    Column(
        "note_id",
        BigInteger,
        ForeignKey("notes.note_id"),
        nullable=False,
    ),
    Column(
        "run_id",
        BigInteger,
        ForeignKey("ingestion_runs.run_id"),
        nullable=False,
    ),
    Column(
        "index_version_id",
        BigInteger,
        ForeignKey("index_versions.index_version_id"),
        nullable=False,
    ),
    Column("content_hash", Text, nullable=False),
    Column("parser_version", Text, nullable=False),
    Column(
        "status",
        Text,
        nullable=False,
    ),
    Column("error_type", Text, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("processed_at", DateTime(timezone=True), nullable=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    UniqueConstraint(
        "note_id",
        "run_id",
        name="uq_ingestion_states_by_note_note_run",
    ),
    CheckConstraint(
        "status IN ('discovered', 'parsed', 'new', 'changed', "
        "'unchanged', 'failed', 'stale')",
        name="ingestion_states_by_note_status_check",
    ),
)


chunks = Table(
    "chunks",
    metadata,
    Column("chunk_id", BigInteger, Identity(), primary_key=True),
    Column(
        "note_id",
        BigInteger,
        ForeignKey("notes.note_id"),
        nullable=False,
    ),
    Column(
        "chunk_index",
        Integer,
        nullable=False,
    ),
    Column("text", Text, nullable=False),
    Column("section_title", Text, nullable=True),
    Column(
        "section_level",
        SmallInteger,
        nullable=True,
    ),
    Column("section_path", JSONB, nullable=False, server_default="[]"),
    Column("section_type", Text, nullable=False),
    Column(
        "start_offset",
        Integer,
        nullable=True,
    ),
    Column(
        "end_offset",
        Integer,
        nullable=True,
    ),
    Column(
        "word_count",
        Integer,
        nullable=False,
    ),
    Column(
        "token_count",
        Integer,
        nullable=False,
    ),
    Column("parser_version", Text, nullable=True),
    Column("source_content_hash", Text, nullable=True),
    Column("chunking_version", Text, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    UniqueConstraint(
        "note_id",
        "chunking_version",
        "chunk_index",
        name="uq_chunks_note_version_index",
    ),
    CheckConstraint(
        "chunk_index >= 0",
        name="chunks_chunk_index_check",
    ),
    CheckConstraint(
        "section_level BETWEEN 1 AND 6",
        name="chunks_section_level_check",
    ),
    CheckConstraint(
        "start_offset >= 0",
        name="chunks_start_offset_check",
    ),
    CheckConstraint(
        "end_offset >= 0",
        name="chunks_end_offset_check",
    ),
    CheckConstraint(
        "word_count >= 0",
        name="chunks_word_count_check",
    ),
    CheckConstraint(
        "token_count >= 0",
        name="chunks_token_count_check",
    ),
)


eval_items = Table(
    "eval_items",
    metadata,
    Column("eval_item_id", BigInteger, Identity(), primary_key=True),
    Column("question", Text, nullable=False),
    Column("corpus_scope", Text, nullable=False),
    Column(
        "relevant_note_ids",
        JSONB,
        nullable=False,
        server_default="[]",
    ),
    Column(
        "relevant_chunk_ids",
        JSONB,
        nullable=False,
        server_default="[]",
    ),
    Column("dataset_version", Text, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    ),
    UniqueConstraint(
        "dataset_version",
        "question",
        name="uq_eval_items_dataset_question",
    ),
    CheckConstraint(
        "char_length(question) > 0",
        name="eval_items_question_not_empty_check",
    ),
    CheckConstraint(
        "char_length(dataset_version) > 0",
        name="eval_items_dataset_version_not_empty_check",
    ),
    CheckConstraint(
        "char_length(corpus_scope) > 0",
        name="eval_items_corpus_scope_not_empty_check",
    ),
)


query_logs = Table(
    "query_logs",
    metadata,
    Column("query_log_id", BigInteger, Identity(), primary_key=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        # Plain "now()" is baked in as a constant at CREATE TABLE.
        server_default=text("now()"),
    ),
    Column("query", Text, nullable=False),
    Column("method", Text, nullable=False),
    Column("top_k", Integer, nullable=False),
    Column("latency_ms", Integer, nullable=False),
    Column(
        "result_count",
        Integer,
        nullable=False,
        server_default="0",
    ),
    Column("error", Text, nullable=True),
    CheckConstraint(
        "char_length(query) > 0",
        name="query_logs_query_not_empty_check",
    ),
    CheckConstraint(
        "method IN ('dense', 'bm25', 'hybrid')",
        name="query_logs_method_check",
    ),
    CheckConstraint(
        "top_k > 0",
        name="query_logs_top_k_positive_check",
    ),
    CheckConstraint(
        "latency_ms >= 0",
        name="query_logs_latency_ms_check",
    ),
    CheckConstraint(
        "result_count >= 0",
        name="query_logs_result_count_check",
    ),
)


__all__ = [
    "chunks",
    "eval_items",
    "index_versions",
    "ingestion_runs",
    "ingestion_states_by_note",
    "metadata",
    "note_links",
    "notes",
    "query_logs",
]
