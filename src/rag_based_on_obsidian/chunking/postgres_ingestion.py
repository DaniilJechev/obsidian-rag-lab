"""Materialize one chunking policy into PostgreSQL."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Connection
from tqdm import tqdm

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.chunking.recursive import chunk_section_tree
from rag_based_on_obsidian.chunking.section_tree import build_section_tree
from rag_based_on_obsidian.config import load_chunking_policy
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file
from rag_based_on_obsidian.corpus.statistics import calculate_document_statistics
from rag_based_on_obsidian.ingestion.contracts import IncomingNote
from rag_based_on_obsidian.ingestion.repositories import (
    NoteRepository,
    acquire_ingestion_lock,
)
from rag_based_on_obsidian.pipeline_versions import PARSER_VERSION


@dataclass(frozen=True)
class ChunkIngestionResult:
    """Counters returned after materializing one policy."""

    documents: int
    chunks: int
    cleared_chunks: int
    chunking_version: str


def materialize_policy(
    connection: Connection,
    *,
    vault_root: Path,
    allowed_directories: Sequence[str],
    policy_path: Path,
) -> ChunkIngestionResult:
    """Clear and fully rematerialize one policy generation for the allowlist."""
    policy = load_chunking_policy(policy_path)
    discovered_files = discover_markdown_files(vault_root, allowed_directories)
    note_repository = NoteRepository(connection)
    chunk_repository = ChunkRepository(connection)
    total_chunks = 0

    with connection.begin():
        acquire_ingestion_lock(connection)
        cleared_chunks = chunk_repository.clear_all()
        for discovered_file in tqdm(
            discovered_files,
            desc=f"Writing {policy.name} to PostgreSQL",
            unit="note",
        ):
            parsed = parse_markdown_file(discovered_file)
            statistics = calculate_document_statistics(parsed)
            incoming = IncomingNote.from_statistics(
                statistics,
                parser_version=PARSER_VERSION,
            )
            note_id = note_repository.upsert(incoming)
            source_hash = hashlib.sha256(
                parsed.raw_text.encode("utf-8")
            ).hexdigest()
            tree = build_section_tree(
                parsed,
                note_id=note_id,
                source_content_hash=source_hash,
                parser_version=PARSER_VERSION,
            )
            records = chunk_section_tree(
                tree,
                source_text=parsed.raw_text,
                policy=policy,
                chunking_version=policy.chunking_version,
                note_id=note_id,
            )
            total_chunks += chunk_repository.upsert_generation(records)

    return ChunkIngestionResult(
        documents=len(discovered_files),
        chunks=total_chunks,
        cleared_chunks=cleared_chunks,
        chunking_version=policy.chunking_version,
    )
