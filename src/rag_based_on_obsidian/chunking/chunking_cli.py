"""Command-line entrypoint for reproducible chunking and database materialization."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml
from sqlalchemy import create_engine

from rag_based_on_obsidian.chunking.experiments.runner import (
    build_tree_sources,
    load_protocol,
    run_policy_matrix,
)
from rag_based_on_obsidian.chunking.postgres_ingestion import materialize_policy
from rag_based_on_obsidian.config import CHUNKING_CONFIG_DIR, load_config
from rag_based_on_obsidian.db.connection import load_database_url


def build_parser() -> argparse.ArgumentParser:
    """Build the stable CLI argument contract."""
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic chunking policies, log them to MLflow, or "
            "fully replace PostgreSQL chunks."
        )
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        help="Override OBSIDIAN_VAULT_ROOT from .env.",
    )
    parser.add_argument(
        "--allowed-directory",
        action="append",
        dest="allowed_directories",
        help="Allowed direct child directory; repeat for DLS1 and DLS2.",
    )
    policy_group = parser.add_mutually_exclusive_group(required=True)
    policy_group.add_argument("--policy", action="append", dest="policies")
    policy_group.add_argument("--all-policies", action="store_true")
    parser.add_argument(
        "--tracking-uri",
        default=None,
        help="MLflow Tracking Server URI.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
    )
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument(
        "--protocol",
        type=Path,
        help="Override EXPERIMENT_PROTOCOL_PATH from .env.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--to-pg",
        action="store_true",
        help=(
            "Clear all rows from PostgreSQL table 'chunks' and fully "
            "rebuild it with one explicit policy."
        ),
    )
    parser.add_argument(
        "--ingestion-config",
        type=Path,
        default=None,
        help="YAML defaults for PostgreSQL chunk materialization.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate arguments, build the corpus and run the requested pipeline."""
    args = build_parser().parse_args(argv)
    app_config = load_config(vault_root_override=args.vault_root)
    protocol = load_protocol(
        args.protocol or app_config.experiment_protocol_path
    )
    allowed_directories = tuple(
        args.allowed_directories or app_config.allowed_corpus_directories
    )
    vault_root = app_config.vault_root
    tracking_uri = args.tracking_uri or app_config.mlflow_tracking_uri
    artifact_dir = args.artifact_dir or app_config.experiment_artifact_dir
    experiment_name = args.experiment_name or app_config.experiment_name
    policy_paths = _resolve_policy_paths(
        args.policies,
        args.all_policies,
        protocol.policy_paths,
    )
    if args.to_pg and args.all_policies:
        raise ValueError("--to-pg requires one explicit --policy")
    if not args.allowed_directories:
        allowed_directories = protocol.allowed_corpus_directories
    if args.to_pg:
        if len(policy_paths) != 1:
            raise ValueError("--to-pg requires exactly one policy")
        ingestion_config = _load_ingestion_config(
            args.ingestion_config or app_config.chunk_ingestion_config_path
        )
        pg_directories = tuple(
            args.allowed_directories
            or ingestion_config["allowed_corpus_directories"]
            or allowed_directories
        )
        engine = create_engine(load_database_url())
        try:
            with engine.connect() as connection:
                result = materialize_policy(
                    connection,
                    vault_root=vault_root,
                    allowed_directories=pg_directories,
                    policy_path=policy_paths[0],
                )
        finally:
            engine.dispose()
        print(
            f"Cleared {result.cleared_chunks} old chunks; persisted "
            f"{result.chunks} chunks from {result.documents} notes "
            f"({result.chunking_version})"
        )
        return 0
    tree_sources = build_tree_sources(vault_root, allowed_directories)

    if args.dry_run:
        print(f"Discovered source trees: {len(tree_sources)}")
        for policy_path in policy_paths:
            print(f"Policy: {policy_path}")
        return 0

    results = run_policy_matrix(
        policy_paths,
        tree_sources,
        artifact_root=artifact_dir,
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        short_chunk_fraction=protocol.short_chunk_fraction,
    )
    for result in results:
        print(
            f"Logged {result.config.policy.name}: "
            f"run_id={result.run_id} chunks={result.result.metrics['chunks_total']}"
        )
    return 0


def _load_ingestion_config(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise TypeError("chunk ingestion YAML must contain a mapping")
    directories = raw_config.get("allowed_corpus_directories", [])
    if not isinstance(directories, list) or not all(
        isinstance(directory, str) and directory for directory in directories
    ):
        raise TypeError("allowed_corpus_directories must be a list of strings")
    return {
        "allowed_corpus_directories": directories,
    }


def _resolve_policy_paths(
    policy_values: list[str] | None,
    all_policies: bool,
    protocol_policy_paths: tuple[Path, ...],
) -> tuple[Path, ...]:
    if all_policies:
        return tuple(
            sorted(protocol_policy_paths, key=lambda path: path.as_posix())
        )
    if not policy_values:
        raise ValueError("at least one policy is required")
    paths: list[Path] = []
    for value in policy_values:
        candidate = Path(value)
        path = (
            candidate
            if candidate.suffix in {".yaml", ".yml"}
            else CHUNKING_CONFIG_DIR / f"{value}.yaml"
        )
        if not path.is_file():
            raise FileNotFoundError(f"chunking policy not found: {path}")
        paths.append(path)
    return tuple(paths)


if __name__ == "__main__":
    sys.exit(main())
