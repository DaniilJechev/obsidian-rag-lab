"""Structural Markdown chunking contracts and adapters."""

from rag_based_on_obsidian.chunking.blocks import (
    BlockType,
    MarkdownBlock,
)
from rag_based_on_obsidian.chunking.documents import section_to_document
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
    "MarkdownBlock",
    "SectionNode",
    "SectionTree",
    "build_section_tree",
    "chunk_section",
    "chunk_section_tree",
    "estimated_token_count",
    "section_to_document",
    "word_count",
]
