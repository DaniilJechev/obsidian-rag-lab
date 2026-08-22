import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "project.toml"


def load_project_config() -> dict:
    with CONFIG_PATH.open("rb") as config_file:
        return tomllib.load(config_file)


def test_project_config_exists() -> None:
    assert CONFIG_PATH.is_file()


def test_project_environment_is_development() -> None:
    config = load_project_config()

    assert config["project"]["environment"] == "development"


def test_corpus_allowlist_is_restricted_to_dls_directories() -> None:
    config = load_project_config()

    allowed_directories = config["corpus"]["allowed_directories"]

    assert set(allowed_directories) == {"DLS1", "DLS2"}


def test_required_project_paths_are_configured() -> None:
    config = load_project_config()

    paths = config["paths"]
    required_paths = {"artifacts", "docs", "evals", "notebooks"}

    assert required_paths.issubset(paths)