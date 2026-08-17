"""CLI operations for creating and verifying Qdrant storage."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.config import (
    DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
    load_config,
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
    load_embedding_model_config,
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
    create.add_argument(
        "--model-config",
        type=Path,
        default=DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    )
    create.add_argument("--vector-size", type=int, default=None)

    embed = subparsers.add_parser("embed")
    embed.add_argument("embedding_args", nargs=argparse.REMAINDER)

    run_and_verify = subparsers.add_parser(
        "run-and-verify",
        help="Embed chunks into Qdrant and verify storage consistency.",
    )
    _add_embedding_arguments(run_and_verify)

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
    if args.operation == "run-and-verify":
        return _run_and_verify(args)
    if args.operation == "verify":
        return _verify_collection(args)
    build_parser().error(f"unknown vector-store operation: {args.operation}")
    return 2


def _run_and_verify(args: argparse.Namespace) -> int:
    """Run the embedding command and verify its selected Qdrant collection."""
    embedding_args = _embedding_arguments(args)
    embedding_exit_code = embedding_main(embedding_args)
    if embedding_exit_code != 0:
        return embedding_exit_code

    print("------------- Verify started ------------")
    app_config = load_config()
    verify_args = argparse.Namespace(
        qdrant_config=args.qdrant_config or app_config.qdrant_config_path,
        batch_config=(
            args.batch_config or app_config.batch_embedding_config_path
        ),
        model_config=(
            args.model_config or app_config.embedding_model_config_path
        ),
    )
    return _verify_collection(verify_args)


def _create_collection(args: argparse.Namespace) -> int:
    qdrant_config = load_qdrant_config(args.qdrant_config)
    batch_config = load_batch_embedding_config(args.batch_config)
    model_config = load_embedding_model_config(args.model_config)
    vector_size = args.vector_size or model_config.dimension
    if vector_size is None:
        raise ValueError(
            "model config must define dimension or pass --vector-size"
        )
    collection_name = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
        model_name=model_config.model_name,
        model_revision=model_config.model_revision,
        vector_size=vector_size,
    )
    sink = QdrantVectorSink.from_url(
        qdrant_config.url,
        collection_name=collection_name,
        vector_size=vector_size,
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
    model_config = load_embedding_model_config(args.model_config)
    vector_size = model_config.dimension
    if vector_size is None:
        raise ValueError("model config must define dimension for verification")
    collection_name = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
        model_name=model_config.model_name,
        model_revision=model_config.model_revision,
        vector_size=vector_size,
    )
    client = QdrantClient(url=qdrant_config.url)
    engine = create_engine(load_database_url())
    verification_started_at = perf_counter()
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
    verification_duration_seconds = perf_counter() - verification_started_at
    verdict = "PASS" if report.is_consistent else "FAIL"

    print(
        json.dumps(
            {
                "collection": collection_name,
                "postgres_points": report.postgres_points,
                "qdrant_points": report.qdrant_points,
                "point_count_matches": report.point_count_matches,
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
                "verify_duration_seconds": verification_duration_seconds,
                "verdict": verdict,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if report.is_consistent:
        print(
            f"VERIFY VERDICT: PASS — PostgreSQL and Qdrant are consistent "
            f"({verification_duration_seconds:.3f}s)"
        )
    else:
        print(
            f"VERIFY VERDICT: FAIL — consistency mismatches detected "
            f"({verification_duration_seconds:.3f}s)"
        )
        print(
            "ACTION: if this was a full rebuild, rerun "
            "`uv run rag-cli vector-store run-and-verify --recreate` "
            "to replace the target collection."
        )
    run_id = log_qdrant_consistency_run(
        config=batch_config,
        collection_name=collection_name,
        report=report,
        duration_seconds=verification_duration_seconds,
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
    parser.add_argument(
        "--model-config",
        type=Path,
        default=DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    )


def _add_embedding_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the embedding overrides supported by the combined command."""
    parser.add_argument("--model-config", type=Path, default=None)
    parser.add_argument("--batch-config", type=Path, default=None)
    parser.add_argument("--qdrant-config", type=Path, default=None)
    parser.add_argument("--tracking-uri", default=None)
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete the target collection before embedding.",
    )


def _embedding_arguments(args: argparse.Namespace) -> list[str]:
    """Translate combined-command options into embedding CLI arguments."""
    arguments: list[str] = []
    for option, attribute in (
        ("--model-config", "model_config"),
        ("--batch-config", "batch_config"),
        ("--qdrant-config", "qdrant_config"),
        ("--tracking-uri", "tracking_uri"),
        ("--experiment-name", "experiment_name"),
        ("--run-name", "run_name"),
    ):
        value = getattr(args, attribute)
        if value is not None:
            arguments.extend((option, str(value)))
    if args.recreate:
        arguments.append("--recreate")
    return arguments
