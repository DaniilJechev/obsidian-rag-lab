"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


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


def load_config() -> AppConfig:
    """Load application configuration from the project ``.env`` file."""

    load_dotenv(ENV_FILE)
    vault_root_value = os.environ.get("OBSIDIAN_VAULT_ROOT")
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
    )
