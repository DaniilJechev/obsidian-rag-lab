"""CLI adapter for the version-aware batch embedding pipeline."""

import argparse
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    BatchEmbeddingResult,
)
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the direct batch embedding command contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Embed PostgreSQL chunks for one explicit chunking version and "
            "write temporary JSON artifacts."
        )
    )
    parser.add_argument("--model-config", type=Path, default=None)
    parser.add_argument("--batch-config", type=Path, default=None)
    parser.add_argument("--tracking-uri", default=None)
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--run-name", default=None)
    return parser


def run_batch_embedding(
    *,
    model_config_path: Path,
    batch_config_path: Path,
    tracking_uri: str | None = None,
    experiment_name: str | None = None,
    run_name: str | None = None,
) -> BatchEmbeddingResult:
    """Load configs, connect PostgreSQL and execute the batch pipeline."""
    model_config = load_embedding_model_config(model_config_path)
    batch_config = load_batch_embedding_config(batch_config_path)
    batch_config = _override_batch_config(
        batch_config,
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_name=run_name,
    )
    provider = TransformersEmbeddingProvider(model_config)
    engine = create_engine(load_database_url())
    try:
        with engine.connect() as connection:
            repository = ChunkRepository(connection)
            pipeline = BatchEmbeddingPipeline(provider, batch_config)
            return pipeline.execute(repository)
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
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        run_name=args.run_name,
    )
    print(
        f"Embedded {len(result.embeddings)}/{result.chunks_total} chunks; "
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
