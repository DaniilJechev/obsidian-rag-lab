"""Unified command-line orchestrator for the RAG pipeline."""

import argparse
import sys
from collections.abc import Sequence

from rag_based_on_obsidian.chunking.chunking_cli import main as chunking_main
from rag_based_on_obsidian.embeddings.cli.batch import main as embedding_main
from rag_based_on_obsidian.eval.cli import main as eval_main
from rag_based_on_obsidian.eval.ragas.ragas_cli import main as ragas_main
from rag_based_on_obsidian.retrieval.cli import main as retrieval_main
from rag_based_on_obsidian.vector_store.cli import main as vector_store_main


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level command routing contract."""
    parser = argparse.ArgumentParser(
        prog="rag-cli",
        description="Orchestrate corpus, chunking and embedding workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "chunk",
        help="Run the existing chunking and PostgreSQL materialization CLI.",
    )
    subparsers.add_parser(
        "upsert-dense-sparse",
        help=(
            "Fill a Qdrant collection with dense embeddings and BM25 sparse "
            "vectors for one chunking version."
        ),
    )
    subparsers.add_parser(
        "vector-store",
        help="Create, upsert dense+BM25 points and verify Qdrant storage.",
    )
    subparsers.add_parser(
        "search",
        help="Run dense, BM25 or hybrid retrieval.",
    )
    subparsers.add_parser(
        "eval",
        help="Load gold items, score rankings, or run live retrieval eval.",
    )
    subparsers.add_parser(
        "ragas",
        help="Score POST /generate answers with RAGAS-style metrics.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch one subcommand while delegating its arguments unchanged."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help"}:
        build_parser().print_help()
        return 0

    command, command_arguments = arguments[0], arguments[1:]
    if command == "chunk":
        return chunking_main(command_arguments)
    if command == "upsert-dense-sparse":
        return embedding_main(command_arguments)
    if command == "vector-store":
        return vector_store_main(command_arguments)
    if command == "search":
        return retrieval_main(command_arguments)
    if command == "eval":
        return eval_main(command_arguments)
    if command == "ragas":
        return ragas_main(command_arguments)

    build_parser().error(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
