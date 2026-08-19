"""CLI adapter for dense, BM25 and hybrid retrieval."""

import argparse
import asyncio
import json
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
from rag_based_on_obsidian.retrieval.pipeline import HybridRetriever
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
    """Execute one retrieval operation."""
    args = build_parser().parse_args(argv)
    config = _load_runtime_config(args)
    if args.operation == "dense":
        results, duration = _run_dense(args, config)
    elif args.operation == "bm25":
        results, duration = _run_bm25(args, config)
    else:
        results, duration = _run_hybrid(args, config)
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
) -> tuple[list[RetrievedChunk], float]:
    provider, collection_name, qdrant_config = _load_dense_dependencies(
        args,
    )
    client = QdrantClient(url=qdrant_config.url)
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
    return results, perf_counter() - started_at


def _run_bm25(
    args: argparse.Namespace,
    config: RetrievalConfig,
) -> tuple[list[RetrievedChunk], float]:
    batch_config = load_batch_embedding_config(args.batch_config)
    engine = create_engine(load_database_url())
    started_at = perf_counter()
    try:
        with engine.connect() as connection:
            repository = ChunkRepository(connection)
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
            results = index.search(
                args.query,
                top_k=config.top_k,
                filters=_filters(args, config),
            )
    finally:
        engine.dispose()
    return results, perf_counter() - started_at


def _run_hybrid(
    args: argparse.Namespace,
    config: RetrievalConfig,
) -> tuple[list[RetrievedChunk], float]:
    provider, collection_name, qdrant_config = _load_dense_dependencies(
        args,
    )
    batch_config = load_batch_embedding_config(args.batch_config)
    client = QdrantClient(url=qdrant_config.url)
    engine = create_engine(load_database_url())
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
            results = asyncio.run(
                retriever.search(
                    args.query,
                    top_k=config.top_k,
                    candidate_k=config.candidate_k,
                    rrf_k=config.rrf_k,
                    filters=_filters(args, config),
                )
            )
    finally:
        engine.dispose()
        client.close()
    return results, perf_counter() - started_at


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
