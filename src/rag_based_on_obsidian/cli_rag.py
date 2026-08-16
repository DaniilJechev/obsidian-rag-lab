"""Unified command-line orchestrator for the RAG pipeline."""

import argparse
import sys
from collections.abc import Sequence

from rag_based_on_obsidian.chunking.chunking_cli import main as chunking_main
from rag_based_on_obsidian.embeddings.cli.batch import main as embedding_main


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
        "embed",
        help="Run the batch embedding pipeline over PostgreSQL chunks.",
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
    if command == "embed":
        return embedding_main(command_arguments)

    build_parser().error(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
