"""CLI operations for creating and verifying Qdrant storage."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.config import (
    DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
)
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.embeddings.cli.batch import main as embedding_main
from rag_based_on_obsidian.embeddings.mlflow_tracking import (
    log_qdrant_consistency_run,
)
from rag_based_on_obsidian.embeddings.qdrant_sink import (
    QdrantVectorSink,
    versioned_collection_name,
)
from rag_based_on_obsidian.embeddings.settings import (
    load_batch_embedding_config,
)
from rag_based_on_obsidian.vector_store.consistency import (
    QdrantConsistencyVerifier,
)
from rag_based_on_obsidian.vector_store.settings import load_qdrant_config


def build_parser() -> argparse.ArgumentParser:
    """Build create, embed and verify vector-store commands."""
    parser = argparse.ArgumentParser(
        prog="rag-cli vector-store",
        description="Create, populate and verify Qdrant vector storage.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    create = subparsers.add_parser("create")
    create.add_argument(
        "--qdrant-config",
        type=Path,
        default=DEFAULT_QDRANT_CONFIG_PATH,
    )
    create.add_argument(
        "--batch-config",
        type=Path,
        default=DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    )
    create.add_argument("--vector-size", type=int, required=True)

    embed = subparsers.add_parser("embed")
    embed.add_argument("embedding_args", nargs=argparse.REMAINDER)

    verify = subparsers.add_parser("verify")
    _add_config_arguments(verify)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one vector-store operation."""
    args = build_parser().parse_args(argv)
    if args.operation == "embed":
        return embedding_main(args.embedding_args)
    if args.operation == "create":
        return _create_collection(args)
    if args.operation == "verify":
        return _verify_collection(args)
    build_parser().error(f"unknown vector-store operation: {args.operation}")
    return 2


def _create_collection(args: argparse.Namespace) -> int:
    qdrant_config = load_qdrant_config(args.qdrant_config)
    batch_config = load_batch_embedding_config(args.batch_config)
    collection_name = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
    )
    sink = QdrantVectorSink.from_url(
        qdrant_config.url,
        collection_name=collection_name,
        vector_size=args.vector_size,
        max_retries=qdrant_config.max_retries,
        retry_backoff_seconds=qdrant_config.retry_backoff_seconds,
    )
    print(
        f"Qdrant collection ready: {collection_name} "
        f"(dimension={sink.vector_size})"
    )
    return 0


def _verify_collection(args: argparse.Namespace) -> int:
    qdrant_config = load_qdrant_config(args.qdrant_config)
    batch_config = load_batch_embedding_config(args.batch_config)
    collection_name = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
    )
    client = QdrantClient(url=qdrant_config.url)
    engine = create_engine(load_database_url())
    try:
        with engine.connect() as connection:
            repository = ChunkRepository(connection)
            report = QdrantConsistencyVerifier(
                client,
                collection_name=collection_name,
                page_size=qdrant_config.scroll_page_size,
            ).verify(
                repository,
                chunking_version=batch_config.chunking_version,
                batch_size=batch_config.batch_size,
            )
    finally:
        engine.dispose()
        client.close()

    print(
        json.dumps(
            {
                "collection": collection_name,
                "postgres_points": report.postgres_points,
                "qdrant_points": report.qdrant_points,
                "missing_point_keys": report.missing_point_keys,
                "extra_point_keys": report.extra_point_keys,
                "metadata_mismatches": [
                    {
                        "point_key": mismatch.point_key,
                        "fields": mismatch.fields,
                    }
                    for mismatch in report.metadata_mismatches
                ],
                "consistency_mismatches": report.mismatch_count,
                "is_consistent": report.is_consistent,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    run_id = log_qdrant_consistency_run(
        config=batch_config,
        collection_name=collection_name,
        report=report,
    )
    print(f"MLflow consistency run: {run_id}")
    return 0 if report.is_consistent else 1


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--qdrant-config",
        type=Path,
        default=DEFAULT_QDRANT_CONFIG_PATH,
    )
    parser.add_argument(
        "--batch-config",
        type=Path,
        default=DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    )
