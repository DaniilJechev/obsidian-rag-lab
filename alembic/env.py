"""Alembic environment for the SQLAlchemy Core schema."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.db.schema import metadata

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


config.set_main_option(
    "sqlalchemy.url",
    load_database_url().replace("%", "%%"),
)


target_metadata = metadata


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations through a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
