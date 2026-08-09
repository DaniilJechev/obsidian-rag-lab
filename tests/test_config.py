import pytest

import rag_based_on_obsidian.config as config_module


def test_load_config_reads_vault_root_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OBSIDIAN_VAULT_ROOT", "~/obsidianNotes")

    config = config_module.load_config()

    assert config.vault_root.name == "obsidianNotes"


def test_load_config_requires_vault_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OBSIDIAN_VAULT_ROOT", raising=False)
    monkeypatch.setattr(config_module, "ENV_FILE", config_module.Path("missing.env"))

    with pytest.raises(ValueError, match="OBSIDIAN_VAULT_ROOT is required"):
        config_module.load_config()
