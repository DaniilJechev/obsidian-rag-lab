"""Orchestrate read-only corpus processing and idempotent database writes."""

import hashlib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from sqlalchemy import Connection, create_engine

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file
from rag_based_on_obsidian.corpus.statistics import calculate_document_statistics
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.ingestion.contracts import (
    IncomingNote,
    IngestionDecision,
    RunCounters,
)
from rag_based_on_obsidian.ingestion.decision import decide_note_action
from rag_based_on_obsidian.ingestion.repositories import (
    IndexVersionRepository,
    IngestionRunRepository,
    IngestionStateRepository,
    NoteRepository,
    acquire_ingestion_lock,
)
from rag_based_on_obsidian.pipeline_versions import (
    CHUNKING_VERSION,
    EMBEDDING_MODEL,
    EMBEDDING_PARAMETERS,
    EMBEDDING_VERSION,
    PARSER_VERSION,
)


def run_ingestion(
    connection: Connection,
    discovered_files: Sequence[DiscoveredFile],
    *,
    corpus_scope: str = "DLS1,DLS2",
    parser_version: str = PARSER_VERSION,
) -> RunCounters:
    """Process discovered files in one transaction with per-note isolation."""
    counters = RunCounters()
    note_repository = NoteRepository(connection)
    run_repository = IngestionRunRepository(connection)
    state_repository = IngestionStateRepository(connection)
    index_repository = IndexVersionRepository(connection)

    transaction_context = (
        connection.begin()
        if not connection.in_transaction()
        else connection.begin_nested()
    )
    with transaction_context:
        acquire_ingestion_lock(connection)
        run_id = run_repository.create(corpus_scope)
        index_version_id = index_repository.get_or_create(
            parser_version=parser_version,
            chunking_version=CHUNKING_VERSION,
            embedding_model=EMBEDDING_MODEL,
            embedding_version=EMBEDDING_VERSION,
            embedding_parameters=EMBEDDING_PARAMETERS,
        )
        discovered_paths = set()

        for discovered_file in sorted(
            discovered_files,
            key=lambda item: item.relative_path.as_posix(),
        ):
            relative_path = discovered_file.relative_path.as_posix()
            discovered_paths.add(relative_path)
            counters.total += 1
            try:
                with connection.begin_nested():
                    incoming = _build_incoming_note(
                        discovered_file,
                        parser_version=parser_version,
                    )
                    previous = note_repository.get_by_path(relative_path)
                    result = decide_note_action(incoming, previous)
                    if previous is None or result.should_process:
                        note_id = note_repository.upsert(incoming)
                    else:
                        note_id = previous.note_id
                    state_repository.record(
                        note_id=note_id,
                        run_id=run_id,
                        index_version_id=index_version_id,
                        content_hash=incoming.content_hash,
                        parser_version=parser_version,
                        status=result.decision.value,
                    )
                counters.increment(result.decision)
            except Exception as error:  # noqa: BLE001
                counters.increment(IngestionDecision.FAILED)
                _record_failed_note(
                    connection=connection,
                    note_repository=note_repository,
                    state_repository=state_repository,
                    run_id=run_id,
                    index_version_id=index_version_id,
                    discovered_file=discovered_file,
                    parser_version=parser_version,
                    error=error,
                )

        scope_directories = tuple(
            directory.strip()
            for directory in corpus_scope.split(",")
            if directory.strip()
        )
        for previous in note_repository.list_paths(
            source_directories=scope_directories,
        ):
            if previous.relative_path in discovered_paths:
                continue
            counters.stale += 1
            state_repository.record(
                note_id=previous.note_id,
                run_id=run_id,
                index_version_id=index_version_id,
                content_hash=previous.content_hash,
                parser_version=parser_version,
                status=IngestionDecision.STALE.value,
            )

        run_status = (
            "failed"
            if counters.total > 0 and counters.failed == counters.total
            else "partial"
            if counters.failed
            else "completed"
        )
        run_repository.finish(run_id, counters, status=run_status)

    return counters


def run_configured_ingestion() -> RunCounters:
    """Discover the configured read-only vault and ingest it into PostgreSQL."""
    config = load_config()
    discovered_files = discover_markdown_files(
        config.vault_root,
        config.allowed_corpus_directories,
    )
    corpus_scope = ",".join(config.allowed_corpus_directories)
    engine = create_engine(load_database_url())
    try:
        with engine.connect() as connection:
            return run_ingestion(
                connection,
                discovered_files,
                corpus_scope=corpus_scope,
            )
    finally:
        engine.dispose()


def _build_incoming_note(
    discovered_file: DiscoveredFile,
    *,
    parser_version: str,
) -> IncomingNote:
    """Parse and calculate deterministic metadata for one file."""
    parsed_document = parse_markdown_file(discovered_file)
    statistics = calculate_document_statistics(parsed_document)
    return IncomingNote.from_statistics(
        statistics,
        parser_version=parser_version,
    )


def _record_failed_note(
    *,
    connection: Connection,
    note_repository: NoteRepository,
    state_repository: IngestionStateRepository,
    run_id: int,
    index_version_id: int,
    discovered_file: DiscoveredFile,
    parser_version: str,
    error: Exception,
) -> None:
    """Keep a failed document visible without aborting the batch."""
    raw_bytes = _safe_read_bytes(discovered_file.absolute_path)
    relative_path = discovered_file.relative_path.as_posix()
    fallback = IncomingNote(
        relative_path=relative_path,
        source_directory=PurePosixPath(relative_path).parts[0],
        title=Path(relative_path).stem,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        file_size_bytes=len(raw_bytes),
        character_count=0,
        word_count=0,
        parse_status="failed",
        language_statistics={},
        anomalies=["ingestion_error"],
        parser_version=parser_version,
    )
    with connection.begin_nested():
        previous = note_repository.get_by_path(relative_path)
        if previous is None:
            note_id = note_repository.upsert(fallback)
        else:
            note_id = previous.note_id
        state_repository.record(
            note_id=note_id,
            run_id=run_id,
            index_version_id=index_version_id,
            content_hash=fallback.content_hash,
            parser_version=parser_version,
            status=IngestionDecision.FAILED.value,
            error_type=type(error).__name__,
            error_message=str(error),
        )


def _safe_read_bytes(path: Path) -> bytes:
    """Read bytes for a stable failure identity without masking the error."""
    try:
        return path.read_bytes()
    except OSError:
        return b""
