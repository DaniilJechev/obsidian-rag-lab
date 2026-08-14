"""Adapters from SectionTree nodes to LangChain Documents."""

from langchain_core.documents import Document

from rag_based_on_obsidian.chunking.section_tree import SectionNode


def section_to_document(node: SectionNode) -> Document:
    """Create one LangChain Document for one SectionTree section."""
    metadata = dict(node.metadata)
    metadata.update(
        {
            "section_id": node.section_id,
            "section_type": node.section_type,
            "section_title": node.title,
            "display_title": node.display_title,
            "section_path": list(node.section_path),
            "section_level": node.level,
            "start_offset": node.start_offset,
            "end_offset": node.end_offset,
            "is_empty_heading": node.is_empty_heading,
        }
    )
    content = node.direct_body
    if node.section_type == "heading":
        heading = f"{'#' * (node.level or 1)} {node.display_title}"
        content = f"{heading}\n\n{node.direct_body}"
    return Document(page_content=content.strip(), metadata=metadata)
