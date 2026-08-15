"""Structural Markdown chunking contracts and adapters."""

from rag_based_on_obsidian.chunking.blocks import (
    BlockType,
    MarkdownBlock,
)
from rag_based_on_obsidian.chunking.documents import section_to_document
from rag_based_on_obsidian.chunking.experiments import (
    ExperimentConfig,
    ExperimentProtocol,
    ExperimentResult,
    build_corpus_inputs,
    build_tree_sources,
    collect_metrics,
    load_experiment_config,
    load_experiment_protocol,
    load_protocol,
    log_experiment_to_mlflow,
    run_experiment,
    run_policy_experiment,
    run_policy_matrix,
    write_experiment_artifacts,
)
from rag_based_on_obsidian.chunking.persistence import ChunkRepository
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.records import (
    ChunkRecord,
    estimated_token_count,
    word_count,
)
from rag_based_on_obsidian.chunking.recursive import (
    chunk_section,
    chunk_section_tree,
)
from rag_based_on_obsidian.chunking.section_tree import (
    SectionNode,
    SectionTree,
    build_section_tree,
)

__all__ = [
    "BlockType",
    "ChunkRecord",
    "ChunkRepository",
    "ChunkingPolicy",
    "ExperimentConfig",
    "ExperimentProtocol",
    "ExperimentResult",
    "MarkdownBlock",
    "SectionNode",
    "SectionTree",
    "build_corpus_inputs",
    "build_section_tree",
    "build_tree_sources",
    "chunk_section",
    "chunk_section_tree",
    "collect_metrics",
    "estimated_token_count",
    "load_experiment_config",
    "load_experiment_protocol",
    "load_protocol",
    "log_experiment_to_mlflow",
    "run_experiment",
    "run_policy_experiment",
    "run_policy_matrix",
    "section_to_document",
    "word_count",
    "write_experiment_artifacts",
]
