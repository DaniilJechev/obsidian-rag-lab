import pytest

import rag_based_on_obsidian.config as config_module


def test_load_config_reads_vault_root_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OBSIDIAN_VAULT_ROOT", "~/obsidianNotes")
    monkeypatch.setenv("ALLOWED_CORPUS_DIRECTORIES", "DLS1, DLS2")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://localhost:5050")
    monkeypatch.setenv("EXPERIMENT_NAME", "test-experiments")

    config = config_module.load_config()

    assert config.vault_root.name == "obsidianNotes"
    assert config.allowed_corpus_directories == ("DLS1", "DLS2")
    assert config.mlflow_tracking_uri == "http://localhost:5050"
    assert config.experiment_name == "test-experiments"


def test_load_config_reads_pgvector_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OBSIDIAN_VAULT_ROOT", "~/obsidianNotes")
    monkeypatch.setenv("PGVECTOR_PORT", "5544")

    config = config_module.load_config()

    assert config.pgvector_port == 5544
    assert config.pgvector_config_path.name == "pgvector.yaml"


def test_load_config_requires_vault_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OBSIDIAN_VAULT_ROOT", raising=False)
    monkeypatch.setattr(config_module, "ENV_FILE", config_module.Path("missing.env"))

    with pytest.raises(ValueError, match="OBSIDIAN_VAULT_ROOT is required"):
        config_module.load_config()


def test_load_chunking_policy_from_yaml() -> None:
    policy = config_module.load_chunking_policy_by_name("policy_chunking_512")

    assert policy.name == "policy-chunking-512"
    assert policy.chunk_size == 512
    assert policy.chunk_overlap == 30
    assert policy.chunking_version == "sprint9-policy-512-v2"
    assert policy.include_heading_context is True


def test_load_chunking_policy_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="plain filename stem"):
        config_module.load_chunking_policy_by_name("../secret")
