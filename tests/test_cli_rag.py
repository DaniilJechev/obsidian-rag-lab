"""Tests for the unified RAG CLI dispatcher."""

import pytest

from rag_based_on_obsidian import cli_rag


def test_rag_cli_dispatches_upsert_dense_sparse_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[str] = []

    def fake_embedding_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 7

    monkeypatch.setattr(cli_rag, "embedding_main", fake_embedding_main)

    assert cli_rag.main(["upsert-dense-sparse", "--batch-config", "batch.yaml"]) == 7
    assert received == ["--batch-config", "batch.yaml"]


def test_rag_cli_dispatches_chunk_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    received: list[str] = []

    def fake_chunking_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 3

    monkeypatch.setattr(cli_rag, "chunking_main", fake_chunking_main)

    assert cli_rag.main(["chunk", "--policy", "policy.yaml"]) == 3
    assert received == ["--policy", "policy.yaml"]


def test_rag_cli_dispatches_vector_store_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []

    def fake_vector_store_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 5

    monkeypatch.setattr(cli_rag, "vector_store_main", fake_vector_store_main)

    assert cli_rag.main(["vector-store", "verify"]) == 5
    assert received == ["verify"]


def test_rag_cli_dispatches_search_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []

    def fake_retrieval_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 6

    monkeypatch.setattr(cli_rag, "retrieval_main", fake_retrieval_main)

    assert cli_rag.main(["search", "hybrid", "--query", "RAG"]) == 6
    assert received == ["hybrid", "--query", "RAG"]


def test_rag_cli_dispatches_eval_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[str] = []

    def fake_eval_main(arguments: list[str]) -> int:
        received.extend(arguments)
        return 4

    monkeypatch.setattr(cli_rag, "eval_main", fake_eval_main)

    assert cli_rag.main(["eval", "score", "--rankings", "ranks.json"]) == 4
    assert received == ["score", "--rankings", "ranks.json"]


def test_rag_cli_rejects_unknown_command() -> None:
    with pytest.raises(SystemExit):
        cli_rag.main(["unknown"])
