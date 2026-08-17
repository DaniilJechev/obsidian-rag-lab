"""Tests for combined vector-store CLI operations."""

from pathlib import Path
from types import SimpleNamespace

from rag_based_on_obsidian.vector_store import cli


def test_run_and_verify_runs_verification_after_embedding(
    monkeypatch,
    capsys,
) -> None:
    embedding_arguments: list[str] = []
    verification_arguments: list[object] = []

    def fake_embedding_main(arguments: list[str]) -> int:
        embedding_arguments.extend(arguments)
        return 0

    def fake_verify_collection(arguments: object) -> int:
        verification_arguments.append(arguments)
        return 0

    monkeypatch.setattr(cli, "embedding_main", fake_embedding_main)
    monkeypatch.setattr(cli, "_verify_collection", fake_verify_collection)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: SimpleNamespace(
            qdrant_config_path=Path("default-qdrant.yaml"),
            batch_embedding_config_path=Path("default-batch.yaml"),
            embedding_model_config_path=Path("default-model.yaml"),
        ),
    )

    assert cli.main(
        [
            "run-and-verify",
            "--batch-config",
            "batch.yaml",
            "--qdrant-config",
            "qdrant.yaml",
        ]
    ) == 0

    assert embedding_arguments == [
        "--batch-config",
        "batch.yaml",
        "--qdrant-config",
        "qdrant.yaml",
    ]
    assert verification_arguments[0].batch_config == Path("batch.yaml")
    assert verification_arguments[0].qdrant_config == Path("qdrant.yaml")
    assert "Verify started" in capsys.readouterr().out
