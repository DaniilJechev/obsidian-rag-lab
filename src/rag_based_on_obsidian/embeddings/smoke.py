"""CLI entry point for a real local embedding and MLflow smoke run."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rag_based_on_obsidian.config import load_config
from rag_based_on_obsidian.embeddings.mlflow_tracking import (
    log_embedding_smoke_run,
)
from rag_based_on_obsidian.embeddings.settings import (
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)

DEFAULT_SMOKE_TEXTS = (
    "RAG объединяет поиск релевантного контекста и генерацию ответа.",
    "Embeddings превращают текст в векторы для similarity search.",
)


def run_embedding_smoke(
    *,
    tracking_uri: str,
    experiment_name: str,
    model_config_path: Path,
    texts: Sequence[str] = DEFAULT_SMOKE_TEXTS,
) -> str:
    """Run real CPU inference and log its operational metrics to MLflow."""
    model_config = load_embedding_model_config(model_config_path)
    provider = TransformersEmbeddingProvider(model_config)
    return log_embedding_smoke_run(
        provider,
        texts,
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_name=model_config.name,
        config=model_config,
    )


def main() -> None:
    """Load project configuration and execute one embedding smoke run."""
    parser = argparse.ArgumentParser(
        description="Run a local embedding model smoke test and log MLflow metrics.",
    )
    parser.add_argument("--tracking-uri", default=None)
    parser.add_argument("--experiment-name", default=None)
    args = parser.parse_args()

    app_config = load_config()
    run_id = run_embedding_smoke(
        tracking_uri=args.tracking_uri or app_config.mlflow_tracking_uri,
        experiment_name=(
            args.experiment_name or app_config.embedding_experiment_name
        ),
        model_config_path=app_config.embedding_model_config_path,
    )
    print(f"MLflow embedding smoke run: {run_id}")
