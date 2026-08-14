"""LangChain-backed recursive structural chunk generation."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_based_on_obsidian.chunking.blocks import BlockType
from rag_based_on_obsidian.chunking.documents import section_to_document
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.records import (
    ChunkRecord,
    estimated_token_count,
    word_count,
)
from rag_based_on_obsidian.chunking.section_tree import SectionNode, SectionTree


def chunk_section(
    section: SectionNode,
    *,
    source_text: str,
    policy: ChunkingPolicy,
    chunking_version: str,
    note_id: int | None = None,
    parser_version: str | None = None,
    source_content_hash: str | None = None,
    chunk_index_start: int = 0,
) -> tuple[ChunkRecord, ...]:
    """Split one SectionNode into deterministic, provenance-aware chunks."""
    resolved_note_id = note_id if note_id is not None else section.metadata.get("note_id")
    resolved_parser_version = (
        parser_version
        if parser_version is not None
        else section.metadata.get("parser_version")
    )
    resolved_hash = (
        source_content_hash
        if source_content_hash is not None
        else section.metadata.get("source_content_hash")
    )
    if not isinstance(resolved_note_id, int):
        raise TypeError("note_id is required to create ChunkRecord")
    if not isinstance(resolved_parser_version, str) or not resolved_parser_version:
        raise ValueError("parser_version is required to create ChunkRecord")
    if not isinstance(resolved_hash, str) or not resolved_hash:
        raise ValueError("source_content_hash is required to create ChunkRecord")

    document = section_to_document(section)
    page_content, protected_blocks = _protect_structural_blocks(
        section,
        document.page_content,
        policy,
    )
    oversized = estimated_token_count(page_content) > policy.chunk_size
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=policy.chunk_size,
        chunk_overlap=policy.chunk_overlap if oversized else 0,
        length_function=estimated_token_count,
        separators=policy.separators,
        keep_separator=True,
    )
    texts = splitter.split_text(page_content)
    source_span = source_text[section.start_offset : section.end_offset]
    heading_prefix = (
        page_content.split("\n\n", maxsplit=1)[0]
        if section.section_type == "heading"
        else ""
    )
    records: list[ChunkRecord] = []
    previous_relative_start = 0

    for local_index, text in enumerate(texts):
        text = _restore_structural_blocks(text, protected_blocks)
        output_text = text
        if heading_prefix and not text.startswith(heading_prefix):
            output_text = f"{heading_prefix}\n\n{text}"
        relative_start = source_span.find(text, previous_relative_start)
        if relative_start < 0:
            relative_start = _fallback_relative_start(
                source_span,
                text,
                previous_relative_start,
                page_content,
            )
        relative_end = min(len(source_span), relative_start + len(text))
        records.append(
            ChunkRecord(
                note_id=resolved_note_id,
                chunk_index=chunk_index_start + local_index,
                section_id=section.section_id,
                section_title=section.title,
                section_level=section.level,
                section_path=section.section_path,
                section_type=section.section_type,
                start_offset=section.start_offset + relative_start,
                end_offset=section.start_offset + relative_end,
                word_count=word_count(output_text),
                token_count=estimated_token_count(output_text),
                parser_version=resolved_parser_version,
                source_content_hash=resolved_hash,
                chunking_version=chunking_version,
                text=output_text,
            )
        )
        previous_relative_start = max(relative_start, previous_relative_start)

    return tuple(records)


def _protect_structural_blocks(
    section: SectionNode,
    page_content: str,
    policy: ChunkingPolicy,
) -> tuple[str, dict[str, str]]:
    """Protect small structural blocks from separator-based splitting."""
    flags = {
        BlockType.CODE: policy.preserve_code_blocks,
        BlockType.LIST: policy.preserve_list_blocks,
        BlockType.TABLE: policy.preserve_table_blocks,
    }
    protected: dict[str, str] = {}
    for index, block in enumerate(section.blocks):
        if not flags.get(block.block_type, False):
            continue
        if estimated_token_count(block.text) > policy.chunk_size:
            continue
        placeholder = f"__STRUCTURAL_BLOCK_{index}__"
        if block.text in page_content:
            page_content = page_content.replace(block.text, placeholder, 1)
            protected[placeholder] = block.text
    return page_content, protected


def _restore_structural_blocks(text: str, protected_blocks: dict[str, str]) -> str:
    for placeholder, block_text in protected_blocks.items():
        text = text.replace(placeholder, block_text)
    return text


def chunk_section_tree(
    tree: SectionTree,
    *,
    source_text: str,
    policy: ChunkingPolicy,
    chunking_version: str,
    note_id: int | None = None,
) -> tuple[ChunkRecord, ...]:
    """Generate chunks for all real sections in document order."""
    chunks: list[ChunkRecord] = []
    for section in tree.sections:
        section_chunks = chunk_section(
            section,
            source_text=source_text,
            policy=policy,
            chunking_version=chunking_version,
            note_id=note_id,
            chunk_index_start=len(chunks),
        )
        chunks.extend(section_chunks)
    return tuple(chunks)


def _fallback_relative_start(
    source_span: str,
    text: str,
    previous_relative_start: int,
    page_content: str,
) -> int:
    """Keep offsets deterministic when Document normalization changes whitespace."""
    normalized_source = " ".join(source_span.split())
    normalized_text = " ".join(text.split())
    normalized_index = normalized_source.find(normalized_text)
    if normalized_index >= 0:
        return min(len(source_span), previous_relative_start + normalized_index)
    approximate_ratio = (
        page_content.find(text) / len(page_content) if page_content else 0
    )
    return min(
        len(source_span),
        max(previous_relative_start, int(len(source_span) * approximate_ratio)),
    )
