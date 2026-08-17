"""Tests for the direct batch embedding CLI adapter."""

from pathlib import Path

from rag_based_on_obsidian.embeddings.cli.batch import (
    _override_batch_config,
    build_parser,
)
from rag_based_on_obsidian.embeddings.settings import BatchEmbeddingConfig


def test_batch_cli_parser_accepts_config_overrides() -> None:
    args = build_parser().parse_args(
        [
            "--model-config",
            "model.yaml",
            "--batch-config",
            "batch.yaml",
            "--qdrant-config",
            "qdrant.yaml",
            "--tracking-uri",
            "http://localhost:5000",
            "--experiment-name",
            "experiment",
            "--run-name",
            "run",
        ]
    )

    assert args.model_config == Path("model.yaml")
    assert args.batch_config == Path("batch.yaml")
    assert args.qdrant_config == Path("qdrant.yaml")
    assert args.tracking_uri == "http://localhost:5000"
    assert args.experiment_name == "experiment"
    assert args.run_name == "run"


def test_batch_cli_overrides_are_applied_immutably(tmp_path: Path) -> None:
    config = BatchEmbeddingConfig(
        name="batch",
        chunking_version="chunk-v1",
        artifact_dir=tmp_path,
        batch_size=2,
    )

    updated = _override_batch_config(
        config,
        tracking_uri="http://localhost:5000",
        experiment_name="new-experiment",
        run_name="new-run",
    )

    assert config.tracking_uri == "http://127.0.0.1:5000"
    assert updated.tracking_uri == "http://localhost:5000"
    assert updated.experiment_name == "new-experiment"
    assert updated.run_name == "new-run"
