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


def test_upsert_dense_sparse_forwards_remainder_arguments(monkeypatch) -> None:
    received: list[str] = []

    def fake_embedding_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 0

    monkeypatch.setattr(cli, "embedding_main", fake_embedding_main)

    assert cli.main(["upsert-dense-sparse", "--recreate"]) == 0
    assert received == ["--recreate"]


def test_upsert_pgvector_uses_experimental_runner(monkeypatch) -> None:
    received: dict[str, object] = {}

    def fake_run_pgvector_upsert(**kwargs: object) -> object:
        received.update(kwargs)

        class Result:
            embeddings_succeeded = 3
            chunks_total = 3
            failures = ()
            duration_seconds = 1.5
            mlflow_run_id = "run-1"

        return Result()

    monkeypatch.setattr(cli, "run_pgvector_upsert", fake_run_pgvector_upsert)
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda: SimpleNamespace(
            qdrant_config_path=Path("default-qdrant.yaml"),
            batch_embedding_config_path=Path("default-batch.yaml"),
            embedding_model_config_path=Path("default-model.yaml"),
            pgvector_config_path=Path("default-pgvector.yaml"),
        ),
    )

    assert cli.main(["upsert-pgvector", "--recreate"]) == 0
    assert received["recreate"] is True
    assert received["pgvector_config_path"] == Path("default-pgvector.yaml")

