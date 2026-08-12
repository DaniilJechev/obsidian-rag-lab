"""Database connection configuration for PostgreSQL."""

from urllib.parse import quote_plus

from rag_based_on_obsidian.config import load_config


def load_database_url() -> str:
    """Build a SQLAlchemy URL from the project's environment variables."""
    config = load_config()

    if not config.postgres_password:
        raise ValueError("POSTGRES_PASSWORD is required")

    escaped_user = quote_plus(config.postgres_user)
    escaped_password = quote_plus(config.postgres_password)
    escaped_host = quote_plus(config.postgres_host)
    escaped_database = quote_plus(config.postgres_database)

    return (
        f"postgresql+psycopg://{escaped_user}:{escaped_password}"
        f"@{escaped_host}:{config.postgres_port}/{escaped_database}"
    )
