"""Read-only corpus orchestration and candidate-policy matrix execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from rag_based_on_obsidian.chunking.experiments.core import (
    SHORT_CHUNK_FRACTION,
    ExperimentConfig,
    ExperimentProtocol,
    ExperimentResult,
    TreeSource,
    load_experiment_config,
    load_experiment_protocol,
    run_experiment,
    write_experiment_artifacts,
)
from rag_based_on_obsidian.chunking.experiments.mlflow_tracking import (
    log_experiment_to_mlflow,
)
from rag_based_on_obsidian.chunking.section_tree import SectionTree, build_section_tree
from rag_based_on_obsidian.corpus.discovery import discover_markdown_files
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file
from rag_based_on_obsidian.pipeline_versions import PARSER_VERSION


@dataclass(frozen=True)
class CorpusInput:
    """One parsed, provenance-aware input note used by experiments."""

    note_id: int
    relative_path: str
    source_text: str
    tree: SectionTree


@dataclass(frozen=True)
class MatrixRunResult:
    """One candidate policy result and its MLflow identity."""

    config: ExperimentConfig
    result: ExperimentResult
    artifact_dir: Path
    run_id: str


def load_protocol(path: Path) -> ExperimentProtocol:
    """Expose protocol loading at the orchestration boundary."""
    return load_experiment_protocol(path)


def build_corpus_inputs(
    vault_root: Path,
    allowed_directories: Sequence[str] = ("DLS1", "DLS2"),
) -> tuple[CorpusInput, ...]:
    """Discover and parse the allowlisted vault without modifying it."""
    discovered_files = discover_markdown_files(vault_root, allowed_directories)
    inputs: list[CorpusInput] = []
    for note_id, discovered_file in enumerate(
        tqdm(
            discovered_files,
            desc="Parsing Markdown notes",
            unit="note",
        )
    ):
        parsed = parse_markdown_file(discovered_file)
        source_hash = hashlib.sha256(
            parsed.raw_text.encode("utf-8")
        ).hexdigest()
        tree = build_section_tree(
            parsed,
            note_id=note_id,
            source_content_hash=source_hash,
            parser_version=PARSER_VERSION,
        )
        inputs.append(
            CorpusInput(
                note_id=note_id,
                relative_path=discovered_file.relative_path.as_posix(),
                source_text=parsed.raw_text,
                tree=tree,
            )
        )
    return tuple(inputs)


def corpus_inputs_to_tree_sources(
    corpus_inputs: tuple[CorpusInput, ...],
) -> tuple[TreeSource, ...]:
    """Adapt rich corpus inputs to the pure chunking runner contract."""
    return tuple((item.tree, item.source_text) for item in corpus_inputs)


def build_tree_sources(
    vault_root: Path,
    allowed_directories: Sequence[str] = ("DLS1", "DLS2"),
) -> tuple[TreeSource, ...]:
    """Build deterministic SectionTree/source pairs for one experiment matrix."""
    return corpus_inputs_to_tree_sources(
        build_corpus_inputs(vault_root, allowed_directories)
    )


def run_policy_experiment(
    policy_path: Path,
    tree_sources: tuple[TreeSource, ...],
    *,
    artifact_root: Path,
    tracking_uri: str,
    experiment_name: str,
    short_chunk_fraction: float = SHORT_CHUNK_FRACTION,
) -> MatrixRunResult:
    """Run, persist and track one candidate policy."""
    tqdm.write(f"[{policy_path.name}] loading policy")
    config = load_experiment_config(policy_path)
    tqdm.write(f"[{config.policy.name}] chunking corpus")
    result = run_experiment(
        config,
        tree_sources,
        short_chunk_fraction=short_chunk_fraction,
    )
    tqdm.write(f"[{config.policy.name}] writing local artifacts")
    artifact_dir = write_experiment_artifacts(result, artifact_root)
    tqdm.write(f"[{config.policy.name}] logging to MLflow")
    run_id = log_experiment_to_mlflow(
        result,
        artifact_dir,
        experiment_name=experiment_name,
        tracking_uri=tracking_uri,
    )
    return MatrixRunResult(
        config=config,
        result=result,
        artifact_dir=artifact_dir,
        run_id=run_id,
    )


def run_policy_matrix(
    policy_paths: Sequence[Path],
    tree_sources: tuple[TreeSource, ...],
    *,
    artifact_root: Path,
    tracking_uri: str,
    experiment_name: str,
    short_chunk_fraction: float = SHORT_CHUNK_FRACTION,
) -> tuple[MatrixRunResult, ...]:
    """Execute candidate policies in deterministic path order."""
    ordered_policy_paths = sorted(
        policy_paths,
        key=lambda path: path.as_posix(),
    )
    results: list[MatrixRunResult] = []
    for policy_path in tqdm(
        ordered_policy_paths,
        desc="Running chunking policies",
        unit="policy",
    ):
        results.append(
            run_policy_experiment(
                policy_path,
                tree_sources,
                artifact_root=artifact_root,
                tracking_uri=tracking_uri,
                experiment_name=experiment_name,
                short_chunk_fraction=short_chunk_fraction,
            )
        )
    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "matrix_manifest.json").write_text(
        json.dumps(
            [
                {
                    "policy_name": item.config.policy.name,
                    "chunking_version": item.config.chunking_version,
                    "run_id": item.run_id,
                    "artifact_dir": item.artifact_dir.as_posix(),
                    "metrics": item.result.metrics,
                }
                for item in results
            ],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return tuple(results)
