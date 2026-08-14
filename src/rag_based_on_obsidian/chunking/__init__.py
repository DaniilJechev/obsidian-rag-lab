"""Structural Markdown chunking contracts and adapters."""

from rag_based_on_obsidian.chunking.blocks import (
    BlockType,
    MarkdownBlock,
)
from rag_based_on_obsidian.chunking.documents import section_to_document
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.section_tree import (
    SectionNode,
    SectionTree,
    build_section_tree,
)

__all__ = [
    "BlockType",
    "ChunkingPolicy",
    "MarkdownBlock",
    "SectionNode",
    "SectionTree",
    "build_section_tree",
    "section_to_document",
]
