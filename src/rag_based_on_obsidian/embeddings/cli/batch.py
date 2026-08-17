"""CLI adapter for the version-aware batch embedding pipeline."""

import argparse
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    BatchEmbeddingResult,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import (
    QdrantVectorSink,
    versioned_collection_name,
)
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.vector_store.settings import load_qdrant_config


def build_parser() -> argparse.ArgumentParser:
    """Build the direct batch embedding command contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Embed PostgreSQL chunks for one explicit chunking version and "
            "upsert validated vectors into Qdrant."
        )
    )
    parser.add_argument("--model-config", type=Path, default=None)
    parser.add_argument("--batch-config", type=Path, default=None)
    parser.add_argument("--qdrant-config", type=Path, default=None)
    parser.add_argument("--tracking-uri", default=None)
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete the target Qdrant collection before embedding.",
    )
    return parser


def run_batch_embedding(
    *,
    model_config_path: Path,
    batch_config_path: Path,
    qdrant_config_path: Path,
    recreate: bool = False,
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
    run_name: str | None = None,
) -> BatchEmbeddingResult:
    """Load configs, connect PostgreSQL and execute the batch pipeline."""
    print("[1/5] Loading embedding configuration")
    model_config = load_embedding_model_config(model_config_path)
    batch_config = load_batch_embedding_config(batch_config_path)
    qdrant_config = load_qdrant_config(qdrant_config_path)
    batch_config = _override_batch_config(
        batch_config,
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_name=run_name,
    )
    print("[2/5] Loading embedding model")
    provider = TransformersEmbeddingProvider(
        replace(model_config, show_progress=False)
    )
    print("[3/5] Connecting to PostgreSQL")
    engine = create_engine(load_database_url())
    try:
        with engine.connect() as connection:
            repository = ChunkRepository(connection)
            collection_name = versioned_collection_name(
                qdrant_config.collection,
                batch_config.chunking_version,
                model_name=provider.metadata.model_name,
                model_revision=provider.metadata.model_revision,
                vector_size=provider.metadata.dimension,
            )
            if recreate:
                _recreate_collection(
                    qdrant_config.url,
                    collection_name=collection_name,
                )
                print(f"Recreated Qdrant collection {collection_name}")
            print(f"[4/5] Connecting to Qdrant collection {collection_name}")
            sink = QdrantVectorSink.from_url(
                qdrant_config.url,
                collection_name=collection_name,
                vector_size=provider.metadata.dimension,
                max_retries=qdrant_config.max_retries,
                retry_backoff_seconds=qdrant_config.retry_backoff_seconds,
            )
            print("[5/5] Starting direct batch embedding to Qdrant")
            pipeline = BatchEmbeddingPipeline(
                provider,
                batch_config,
                stage_logger=print,
            )
            return pipeline.execute(repository, sink=sink)
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Run batch embeddings using project defaults and CLI overrides."""
    args = build_parser().parse_args(argv)
    app_config = load_config()
    result = run_batch_embedding(
        model_config_path=args.model_config or app_config.embedding_model_config_path,
        batch_config_path=(
            args.batch_config or app_config.batch_embedding_config_path
        ),
        qdrant_config_path=(
            args.qdrant_config or app_config.qdrant_config_path
        ),
        recreate=args.recreate,
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
    )
    print(
        f"Embedded {result.embeddings_succeeded}/{result.chunks_total} chunks; "
        f"failed={len(result.failures)}; "
        f"duration={result.duration_seconds:.3f}s; "
        f"mlflow_run_id={result.mlflow_run_id or 'unknown'}"
    )
    return 0


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


def _recreate_collection(url: str, *, collection_name: str) -> None:
    """Explicitly delete one target collection before a full rebuild."""
    client = QdrantClient(url=url)
    try:
        if client.collection_exists(collection_name=collection_name):
            client.delete_collection(collection_name=collection_name)
    finally:
        client.close()
