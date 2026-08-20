"""Database connection configuration for PostgreSQL."""

from urllib.parse import quote_plus

from rag_based_on_obsidian.config import load_config


def load_database_url() -> str:
    """Build a SQLAlchemy URL from the project's environment variables."""
    config = load_config()
    return _postgres_url(
        host=config.postgres_host,
        port=config.postgres_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
    )


def load_pgvector_database_url() -> str:
    """Build a URL for the experimental pgvector Postgres, not the source DB."""
    config = load_config()
    return _postgres_url(
        host=config.pgvector_host,
        port=config.pgvector_port,
        database=config.postgres_database,
        user=config.postgres_user,
        password=config.postgres_password,
    )


def _postgres_url(
    *,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
) -> str:
    if not password:
        raise ValueError("POSTGRES_PASSWORD is required")
    escaped_user = quote_plus(user)
    escaped_password = quote_plus(password)
    escaped_host = quote_plus(host)
    escaped_database = quote_plus(database)
    return (
        f"postgresql+psycopg://{escaped_user}:{escaped_password}"
        f"@{escaped_host}:{port}/{escaped_database}"
    )
