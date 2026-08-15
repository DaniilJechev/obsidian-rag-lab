"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
CHUNKING_CONFIG_DIR = PROJECT_ROOT / "configs" / "chunking"
DEFAULT_MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
DEFAULT_MLFLOW_BACKEND_STORE_URI = "sqlite:///mlflow.db"
DEFAULT_MLFLOW_ARTIFACT_ROOT = Path("artifacts") / "mlflow"
DEFAULT_EXPERIMENT_ARTIFACT_DIR = Path("artifacts") / "chunking"
DEFAULT_EXPERIMENT_NAME = "sprint-9-chunking-experiments"
DEFAULT_EXPERIMENT_PROTOCOL_PATH = (
    PROJECT_ROOT / "configs" / "experiments" / "sprint9_chunking.yaml"
)
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy


@dataclass(frozen=True)
class AppConfig:
    """Validated configuration required by the application."""

    vault_root: Path
    allowed_corpus_directories: tuple[str, ...]
    postgres_host: str
    postgres_port: int
    postgres_database: str
    postgres_user: str
    postgres_password: str = ""
    mlflow_tracking_uri: str = DEFAULT_MLFLOW_TRACKING_URI
    mlflow_backend_store_uri: str = DEFAULT_MLFLOW_BACKEND_STORE_URI
    mlflow_artifact_root: Path = DEFAULT_MLFLOW_ARTIFACT_ROOT
    experiment_artifact_dir: Path = DEFAULT_EXPERIMENT_ARTIFACT_DIR
    experiment_name: str = DEFAULT_EXPERIMENT_NAME
    experiment_protocol_path: Path = DEFAULT_EXPERIMENT_PROTOCOL_PATH


def load_config(*, vault_root_override: Path | None = None) -> AppConfig:
    """Load application configuration from the project ``.env`` file."""

    load_dotenv(ENV_FILE)
    vault_root_value = (
        str(vault_root_override)
        if vault_root_override is not None
        else os.environ.get("OBSIDIAN_VAULT_ROOT")
    )
    if not vault_root_value:
        raise ValueError("OBSIDIAN_VAULT_ROOT is required")

    directories_value = os.environ.get(
        "ALLOWED_CORPUS_DIRECTORIES",
        "DLS1,DLS2",
    )
    allowed_directories = tuple(
        directory.strip()
        for directory in directories_value.split(",")
        if directory.strip()
    )
    if not allowed_directories:
        raise ValueError("ALLOWED_CORPUS_DIRECTORIES must not be empty")

    return AppConfig(
        vault_root=Path(vault_root_value).expanduser(),
        allowed_corpus_directories=allowed_directories,
        postgres_host=os.environ.get("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.environ.get("POSTGRES_PORT", "5432")),
        postgres_database=os.environ.get("POSTGRES_DB", "rag"),
        postgres_user=os.environ.get("POSTGRES_USER", "rag"),
        postgres_password=os.environ.get("POSTGRES_PASSWORD", ""),
        mlflow_tracking_uri=os.environ.get(
            "MLFLOW_TRACKING_URI",
            DEFAULT_MLFLOW_TRACKING_URI,
        ),
        mlflow_backend_store_uri=os.environ.get(
            "MLFLOW_BACKEND_STORE_URI",
            DEFAULT_MLFLOW_BACKEND_STORE_URI,
        ),
        mlflow_artifact_root=Path(
            os.environ.get(
                "MLFLOW_ARTIFACT_ROOT",
                str(DEFAULT_MLFLOW_ARTIFACT_ROOT),
            )
        ).expanduser(),
        experiment_artifact_dir=Path(
            os.environ.get(
                "EXPERIMENT_ARTIFACT_DIR",
                str(DEFAULT_EXPERIMENT_ARTIFACT_DIR),
            )
        ).expanduser(),
        experiment_name=os.environ.get(
            "EXPERIMENT_NAME",
            DEFAULT_EXPERIMENT_NAME,
        ),
        experiment_protocol_path=Path(
            os.environ.get(
                "EXPERIMENT_PROTOCOL_PATH",
                str(DEFAULT_EXPERIMENT_PROTOCOL_PATH),
            )
        ).expanduser(),
    )


def load_chunking_policy(path: Path) -> ChunkingPolicy:
    """Load and validate one YAML chunking policy."""
    if path.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError("chunking policy path must have a .yaml or .yml suffix")

    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)

    if not isinstance(raw_config, dict):
        raise TypeError("chunking policy YAML must contain a mapping")
    return ChunkingPolicy.model_validate(raw_config)


def load_chunking_policy_by_name(name: str) -> ChunkingPolicy:
    """Load a named policy from the project's ``configs/chunking`` directory."""
    if not name or Path(name).name != name:
        raise ValueError("chunking policy name must be a plain filename stem")

    policy_path = CHUNKING_CONFIG_DIR / f"{name}.yaml"
    if not policy_path.is_file():
        raise FileNotFoundError(f"chunking policy not found: {policy_path}")
    return load_chunking_policy(policy_path)
