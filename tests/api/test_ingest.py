"""Ingest vault preflight. No live e5, Qdrant, or PostgreSQL."""

from pathlib import Path

import pytest

from rag_based_on_obsidian.api.ingest import (
    PRODUCTION_CHUNKING_VERSION,
    PRODUCTION_POLICY_PATH,
    IngestService,
    IngestUnavailableError,
)
from rag_based_on_obsidian.embeddings.settings import BatchEmbeddingConfig
from rag_based_on_obsidian.vector_store.settings import QdrantConfig


def _service(tmp_path: Path) -> IngestService:
    (tmp_path / "DLS1").mkdir()
    (tmp_path / "DLS2").mkdir()
    return IngestService(
        engine=None,  # type: ignore[arg-type]
        provider=None,  # type: ignore[arg-type]
        qdrant_client=None,  # type: ignore[arg-type]
        batch_config=BatchEmbeddingConfig(
            name="test",
            chunking_version=PRODUCTION_CHUNKING_VERSION,
            artifact_dir=tmp_path,
            batch_size=8,
        ),
        qdrant_config=QdrantConfig(url="http://qdrant:6333", collection="notes"),
        vault_root=tmp_path,
        allowed_directories=("DLS1", "DLS2"),
        policy_path=PRODUCTION_POLICY_PATH,
    )


def test_assert_vault_ready_rejects_missing_corpus_dir(tmp_path: Path) -> None:
    service = _service(tmp_path)
    (tmp_path / "DLS2").rmdir()
    with pytest.raises(IngestUnavailableError, match="corpus directory missing"):
        service._assert_vault_ready()


def test_assert_vault_ready_accepts_dls_allowlist(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service._assert_vault_ready()
