"""CLI adapter for dense, BM25 and hybrid retrieval."""

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from qdrant_client import QdrantClient
from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.config import (
    DEFAULT_BATCH_EMBEDDING_CONFIG_PATH,
    DEFAULT_EMBEDDING_MODEL_CONFIG_PATH,
    DEFAULT_QDRANT_CONFIG_PATH,
    DEFAULT_RETRIEVAL_CONFIG_PATH,
)
from rag_based_on_obsidian.db.connection import load_database_url
from rag_based_on_obsidian.embeddings.qdrant_sink import versioned_collection_name
from rag_based_on_obsidian.embeddings.settings import (
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever
from rag_based_on_obsidian.retrieval.lexical import InMemoryBM25Index
from rag_based_on_obsidian.retrieval.mlflow_tracking import log_search_run
from rag_based_on_obsidian.retrieval.pipeline import HybridRetriever
from rag_based_on_obsidian.retrieval.progress import (
    SearchProgress,
    configure_search_logging,
    logger,
)
from rag_based_on_obsidian.retrieval.settings import (
    RetrievalConfig,
    load_retrieval_config,
)
from rag_based_on_obsidian.vector_store.settings import (
    QdrantConfig,
    load_qdrant_config,
)


def build_parser() -> argparse.ArgumentParser:
    """Build dense, BM25 and hybrid retrieval commands."""
    parser = argparse.ArgumentParser(
        prog="rag-cli search",
        description="Run dense, BM25 or hybrid retrieval.",
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("dense", "bm25", "hybrid"):
        operation_parser = subparsers.add_parser(operation)
        _add_arguments(operation_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one explicitly selected retrieval operation."""
    configure_search_logging()
    args = build_parser().parse_args(argv)
    if args.operation not in {"dense", "bm25", "hybrid"}:
        print(
            "error: search requires an explicit operation: dense, bm25 or hybrid",
            file=sys.stderr,
        )
        return 2

    progress = SearchProgress()
    progress.mark("parse_args", operation=args.operation)
    config = _load_runtime_config(args)
    progress.mark(
        "load_config",
        top_k=config.top_k,
        chunking_version=config.chunking_version,
    )
    logger.info("stage=search_start operation=%s query=%r", args.operation, args.query)

    collection_name: str | None = None
    model_name: str | None = None
    model_revision: str | None = None
    device: str | None = None
    dimension: int | None = None
    results: list[RetrievedChunk] = []
    duration = 0.0
    try:
        if args.operation == "dense":
            results, duration, collection_name, model_meta = _run_dense(
                args,
                config,
                progress,
            )
            model_name, model_revision, device, dimension = model_meta
        elif args.operation == "bm25":
            results, duration = _run_bm25(args, config, progress)
        elif args.operation == "hybrid":
            results, duration, collection_name, model_meta = _run_hybrid(
                args,
                config,
                progress,
            )
            model_name, model_revision, device, dimension = model_meta
        else:
            print(
                "error: search requires an explicit operation: dense, bm25 or hybrid",
                file=sys.stderr,
            )
            return 2
    except Exception as exc:  # noqa: BLE001
        error_text = f"{type(exc).__name__}: {exc}"
        logger.exception("stage=search_failed operation=%s", args.operation)
        _record_search_run(
            args=args,
            config=config,
            progress=progress,
            results=results,
            duration_seconds=progress.total_seconds,
            collection_name=collection_name,
            model_name=model_name,
            model_revision=model_revision,
            device=device,
            dimension=dimension,
            error=error_text,
        )
        print(f"error: {error_text}", file=sys.stderr)
        return 1

    progress.mark("search_done", result_count=len(results))
    _record_search_run(
        args=args,
        config=config,
        progress=progress,
        results=results,
        duration_seconds=duration,
        collection_name=collection_name,
        model_name=model_name,
        model_revision=model_revision,
        device=device,
        dimension=dimension,
        error=None,
    )
    _print_results(
        results,
        operation=args.operation,
        duration_seconds=duration,
    )
    return 0


def _add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", required=True)
    parser.add_argument("--retrieval-config", type=Path, default=DEFAULT_RETRIEVAL_CONFIG_PATH)
    parser.add_argument("--qdrant-config", type=Path, default=DEFAULT_QDRANT_CONFIG_PATH)
    parser.add_argument("--batch-config", type=Path, default=DEFAULT_BATCH_EMBEDDING_CONFIG_PATH)
    parser.add_argument("--model-config", type=Path, default=DEFAULT_EMBEDDING_MODEL_CONFIG_PATH)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--candidate-k", type=int, default=None)
    parser.add_argument("--rrf-k", type=int, default=None)
    parser.add_argument("--source-path", default=None)
    parser.add_argument("--note-id", type=int, default=None)


def _load_runtime_config(args: argparse.Namespace) -> RetrievalConfig:
    config = load_retrieval_config(args.retrieval_config)
    overrides: dict[str, object] = {}
    for name in ("top_k", "candidate_k", "rrf_k"):
        value = getattr(args, name)
        if value is not None:
            overrides[name] = value
    return replace(config, **overrides)


def _run_dense(
    args: argparse.Namespace,
    config: RetrievalConfig,
    progress: SearchProgress,
) -> tuple[list[RetrievedChunk], float, str, tuple[str, str, str, int]]:
    provider, collection_name, qdrant_config = _load_dense_dependencies(
        args,
    )
    progress.mark(
        "load_embedding_model",
        model=provider.metadata.model_name,
        collection=collection_name,
    )
    client = QdrantClient(url=qdrant_config.url)
    progress.mark("connect_qdrant", url=qdrant_config.url)
    started_at = perf_counter()
    try:
        results = QdrantDenseRetriever(
            client,
            collection_name=collection_name,
            provider=provider,
        ).search(
            args.query,
            top_k=config.top_k,
            filters=_filters(args, config),
        )
    finally:
        client.close()
    return (
        results,
        perf_counter() - started_at,
        collection_name,
        (
            provider.metadata.model_name,
            provider.metadata.model_revision,
            provider.metadata.device,
            provider.metadata.dimension,
        ),
    )


def _run_bm25(
    args: argparse.Namespace,
    config: RetrievalConfig,
    progress: SearchProgress,
) -> tuple[list[RetrievedChunk], float]:
    batch_config = load_batch_embedding_config(args.batch_config)
    progress.mark("load_batch_config", chunking_version=batch_config.chunking_version)
    engine = create_engine(load_database_url())
    progress.mark("connect_postgres")
    started_at = perf_counter()
    try:
        with engine.connect() as connection:
            repository = ChunkRepository(connection)
            progress.mark("load_postgres_chunks")
            index = InMemoryBM25Index.from_rows(
                (
                    row
                    for batch in repository.iter_by_version(
                        chunking_version=batch_config.chunking_version,
                        batch_size=config.postgres_batch_size,
                    )
                    for row in batch
                ),
                chunking_version=batch_config.chunking_version,
            )
            progress.mark("build_bm25_index")
            results = index.search(
                args.query,
                top_k=config.top_k,
                filters=_filters(args, config),
            )
            progress.mark("bm25_search", hits=len(results))
    finally:
        engine.dispose()
    return results, perf_counter() - started_at


def _run_hybrid(
    args: argparse.Namespace,
    config: RetrievalConfig,
    progress: SearchProgress,
) -> tuple[list[RetrievedChunk], float, str, tuple[str, str, str, int]]:
    provider, collection_name, qdrant_config = _load_dense_dependencies(
        args,
    )
    progress.mark(
        "load_embedding_model",
        model=provider.metadata.model_name,
        collection=collection_name,
    )
    batch_config = load_batch_embedding_config(args.batch_config)
    client = QdrantClient(url=qdrant_config.url)
    progress.mark("connect_qdrant", url=qdrant_config.url)
    engine = create_engine(load_database_url())
    progress.mark("connect_postgres")
    started_at = perf_counter()
    try:
        with engine.connect() as connection:
            retriever = HybridRetriever.from_repository(
                dense=QdrantDenseRetriever(
                    client,
                    collection_name=collection_name,
                    provider=provider,
                ),
                provider=provider,
                repository=ChunkRepository(connection),
                chunking_version=batch_config.chunking_version,
                batch_size=config.postgres_batch_size,
            )
            progress.mark("build_bm25_index")
            results = asyncio.run(
                retriever.search(
                    args.query,
                    top_k=config.top_k,
                    candidate_k=config.candidate_k,
                    rrf_k=config.rrf_k,
                    filters=_filters(args, config),
                )
            )
            progress.mark("hybrid_search", hits=len(results))
    finally:
        engine.dispose()
        client.close()
    return (
        results,
        perf_counter() - started_at,
        collection_name,
        (
            provider.metadata.model_name,
            provider.metadata.model_revision,
            provider.metadata.device,
            provider.metadata.dimension,
        ),
    )


def _load_dense_dependencies(
    args: argparse.Namespace,
) -> tuple[
    TransformersEmbeddingProvider,
    str,
    QdrantConfig,
]:
    model_config = load_embedding_model_config(args.model_config)
    provider = TransformersEmbeddingProvider(model_config)
    batch_config = load_batch_embedding_config(args.batch_config)
    qdrant_config = load_qdrant_config(args.qdrant_config)
    collection_name = versioned_collection_name(
        qdrant_config.collection,
        batch_config.chunking_version,
        model_name=provider.metadata.model_name,
        model_revision=provider.metadata.model_revision,
        vector_size=provider.metadata.dimension,
    )
    return provider, collection_name, qdrant_config


def _record_search_run(
    *,
    args: argparse.Namespace,
    config: RetrievalConfig,
    progress: SearchProgress,
    results: Sequence[RetrievedChunk],
    duration_seconds: float,
    collection_name: str | None,
    model_name: str | None,
    model_revision: str | None,
    device: str | None,
    dimension: int | None,
    error: str | None,
) -> None:
    logger.info("stage=mlflow_log experiment=searching")
    try:
        run_id = log_search_run(
            operation=args.operation,
            query=args.query,
            top_k=config.top_k,
            candidate_k=config.candidate_k,
            rrf_k=config.rrf_k,
            chunking_version=config.chunking_version,
            result_count=len(results),
            duration_seconds=duration_seconds,
            stage_seconds=progress.stage_seconds,
            collection_name=collection_name,
            model_name=model_name,
            model_revision=model_revision,
            device=device,
            dimension=dimension,
            error=error,
        )
        logger.info("stage=mlflow_log_done run_id=%s", run_id)
    except Exception:  # noqa: BLE001
        logger.exception("stage=mlflow_log_failed")


def _filters(
    args: argparse.Namespace,
    config: RetrievalConfig,
) -> Mapping[str, object]:
    filters = dict(config.filters)
    if args.source_path is not None:
        filters["source_path"] = args.source_path
    if args.note_id is not None:
        filters["note_id"] = args.note_id
    return filters


def _print_results(
    results: Sequence[RetrievedChunk],
    *,
    operation: str,
    duration_seconds: float,
) -> None:
    print(
        json.dumps(
            {
                "operation": operation,
                "result_count": len(results),
                "duration_seconds": duration_seconds,
                "results": [_serialize_result(result) for result in results],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _serialize_result(result: RetrievedChunk) -> dict[str, object]:
    return {
        "rank": result.rank,
        "chunk_id": result.chunk_id,
        "point_key": result.point_key,
        "score": result.score,
        "dense_score": result.dense_score,
        "bm25_score": result.bm25_score,
        "rrf_score": result.rrf_score,
        "retrieval_method": result.retrieval_method.value,
        "chunking_version": result.chunking_version,
        "metadata": dict(result.metadata),
        "text": result.text,
    }
