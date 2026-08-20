"""CLI adapter that embeds PostgreSQL chunks into experimental pgvector."""

from dataclasses import replace
from pathlib import Path

from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.db.connection import (
    load_database_url,
    load_pgvector_database_url,
)
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    BatchEmbeddingResult,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import versioned_collection_name
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.vector_store.pgvector_settings import load_pgvector_config
from rag_based_on_obsidian.vector_store.pgvector_sink import PgvectorVectorSink
from rag_based_on_obsidian.vector_store.settings import load_qdrant_config


def run_pgvector_upsert(
    *,
    model_config_path: Path,
    batch_config_path: Path,
    qdrant_config_path: Path,
    pgvector_config_path: Path,
    recreate: bool = False,
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
    run_name: str | None = None,
) -> BatchEmbeddingResult:
    """Read chunks from source Postgres and upsert dense vectors to pgvector."""
    print("[1/5] Loading embedding configuration")
    model_config = load_embedding_model_config(model_config_path)
    batch_config = load_batch_embedding_config(batch_config_path)
    qdrant_config = load_qdrant_config(qdrant_config_path)
    pgvector_config = load_pgvector_config(pgvector_config_path)
    batch_config = _override_batch_config(
        batch_config,
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_name=run_name,
    )
    print("[2/5] Loading embedding model")
    provider = TransformersEmbeddingProvider(
        replace(model_config, show_progress=True)
    )
    index_generation = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
        model_name=provider.metadata.model_name,
        model_revision=provider.metadata.model_revision,
        vector_size=provider.metadata.dimension,
    )
    print("[3/5] Connecting to source PostgreSQL")
    source_engine = create_engine(load_database_url())
    print(f"[4/5] Connecting to pgvector table {pgvector_config.table}")
    sink = PgvectorVectorSink.from_url(
        load_pgvector_database_url(),
        index_generation=index_generation,
        vector_size=provider.metadata.dimension,
        table_name=pgvector_config.table,
        max_retries=pgvector_config.max_retries,
        retry_backoff_seconds=pgvector_config.retry_backoff_seconds,
    )
    if recreate:
        sink.delete_generation()
        print(f"Cleared pgvector index generation {index_generation}")
    try:
        with source_engine.connect() as connection:
            repository = ChunkRepository(connection)
            print("[5/5] Starting dense batch upsert to pgvector")
            pipeline = BatchEmbeddingPipeline(
                provider,
                batch_config,
                stage_logger=print,
            )
            return pipeline.execute(repository, sink=sink)
    finally:
        source_engine.dispose()
        sink.engine.dispose()


def _override_batch_config(
    config: BatchEmbeddingConfig,
    *,
    tracking_uri: str | None,
    experiment_name: str | None,
    run_name: str | None,
) -> BatchEmbeddingConfig:
    """Apply explicit CLI overrides without mutating the loaded config."""
    overrides = {
        key: value
        for key, value in {
            "tracking_uri": tracking_uri,
            "experiment_name": experiment_name,
            "run_name": run_name,
        }.items()
        if value is not None
    }
    return replace(config, **overrides)
