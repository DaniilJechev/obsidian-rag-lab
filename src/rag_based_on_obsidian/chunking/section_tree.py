"""Build an immutable Markdown section tree from the existing parser contract."""

from dataclasses import dataclass, field
from typing import Any

from rag_based_on_obsidian.chunking.blocks import (
    BlockType,
    MarkdownBlock,
)
from rag_based_on_obsidian.corpus.markdown_entities import ParsedDocument


@dataclass(frozen=True)
class SectionNode:
    """One heading or pre-heading section in the source document."""

    section_id: str
    section_type: str
    title: str | None
    display_title: str
    is_empty_heading: bool
    level: int | None
    section_path: tuple[str, ...]
    direct_body: str
    blocks: tuple[MarkdownBlock, ...]
    start_offset: int
    end_offset: int
    parent_section_id: str | None = None
    previous_sibling_id: str | None = None
    next_sibling_id: str | None = None
    children: tuple["SectionNode", ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SectionTree:
    """Immutable document tree with a synthetic root node."""

    relative_path: str
    source_content_hash: str | None
    parser_version: str | None
    root: SectionNode

    @property
    def sections(self) -> tuple[SectionNode, ...]:
        """Return all real sections in document order."""
        return tuple(_walk(self.root))[1:]


def build_section_tree(
    document: ParsedDocument,
    *,
    note_id: int | None = None,
    source_content_hash: str | None = None,
    parser_version: str | None = None,
) -> SectionTree:
    """Build sections, blocks, parent links and sibling links deterministically."""
    raw_text = document.raw_text
    lines = raw_text.splitlines(keepends=True)
    line_starts = _line_starts(lines)
    headings = document.headings
    nodes: list[SectionNode] = []

    if headings and headings[0].line_number > 1:
        start_line = _frontmatter_end_line(raw_text)
        if start_line < headings[0].line_number - 1:
            nodes.append(
                _make_section(
                    document,
                    section_id="section-0",
                    section_type="pre_heading",
                    title=None,
                    level=None,
                    start_line=start_line + 1,
                    end_line=headings[0].line_number - 1,
                    line_starts=line_starts,
                    path=(),
                    parent_id=None,
                    note_id=note_id,
                    source_content_hash=source_content_hash,
                    parser_version=parser_version,
                )
            )
    elif not headings and raw_text.strip():
        start_line = _frontmatter_end_line(raw_text)
        nodes.append(
            _make_section(
                document,
                section_id="section-0",
                section_type="pre_heading",
                title=None,
                level=None,
                start_line=start_line + 1,
                end_line=len(lines),
                line_starts=line_starts,
                path=(),
                parent_id=None,
                note_id=note_id,
                source_content_hash=source_content_hash,
                parser_version=parser_version,
            )
        )

    section_index = len(nodes)
    for index, heading in enumerate(headings):
        next_heading = headings[index + 1].line_number - 1 if index + 1 < len(headings) else len(lines)
        parent = _find_parent(nodes, heading.level)
        parent_id = parent.section_id if parent else None
        path = (*parent.section_path, heading.text or "__empty_heading__") if parent else (
            heading.text or "__empty_heading__",
        )
        nodes.append(
            _make_section(
                document,
                section_id=f"section-{section_index}",
                section_type="heading",
                title=heading.text or None,
                level=heading.level,
                start_line=heading.line_number,
                end_line=next_heading,
                line_starts=line_starts,
                path=path,
                parent_id=parent_id,
                note_id=note_id,
                source_content_hash=source_content_hash,
                parser_version=parser_version,
            )
        )
        section_index += 1

    root = _assemble_tree(
        nodes=nodes,
        relative_path=document.source.relative_path.as_posix(),
        note_id=note_id,
    )
    return SectionTree(
        relative_path=document.source.relative_path.as_posix(),
        source_content_hash=source_content_hash,
        parser_version=parser_version,
        root=root,
    )


def _make_section(
    document: ParsedDocument,
    *,
    section_id: str,
    section_type: str,
    title: str | None,
    level: int | None,
    start_line: int,
    end_line: int,
    line_starts: list[int],
    path: tuple[str, ...],
    parent_id: str | None,
    note_id: int | None,
    source_content_hash: str | None,
    parser_version: str | None,
) -> SectionNode:
    raw_text = document.raw_text
    start_offset = line_starts[start_line - 1] if start_line <= len(line_starts) else len(raw_text)
    end_offset = line_starts[end_line] if end_line < len(line_starts) else len(raw_text)
    text = raw_text[start_offset:end_offset]
    body_offset = start_offset
    if section_type == "heading" and start_line <= len(line_starts):
        body_offset = min(
            line_starts[start_line - 1] + len(raw_text[line_starts[start_line - 1] :].splitlines(keepends=True)[0]),
            end_offset,
        )
    blocks = _extract_blocks(
        text,
        start_offset,
        section_id,
        include_heading=section_type == "heading",
        heading_level=level,
    )
    return SectionNode(
        section_id=section_id,
        section_type=section_type,
        title=title,
        display_title=title or ("(empty heading)" if section_type == "heading" else "(pre-heading)"),
        is_empty_heading=section_type == "heading" and title is None,
        level=level,
        section_path=path,
        direct_body=raw_text[body_offset:end_offset].strip(),
        blocks=blocks,
        start_offset=start_offset,
        end_offset=end_offset,
        parent_section_id=parent_id,
        metadata={
            "note_id": note_id,
            "relative_path": document.source.relative_path.as_posix(),
            "source_content_hash": source_content_hash,
            "parser_version": parser_version,
            "frontmatter": document.frontmatter,
            "wikilinks": tuple(document.wikilinks),
        },
    )


def _extract_blocks(
    text: str,
    offset: int,
    section_id: str,
    *,
    include_heading: bool = False,
    heading_level: int | None = None,
) -> tuple[MarkdownBlock, ...]:
    """Extract conservative paragraph/code/list/table blocks in source order."""
    lines = text.splitlines(keepends=True)
    blocks: list[MarkdownBlock] = []
    cursor = 0
    paragraph: list[tuple[int, str]] = []
    in_code = False
    code_start = 0
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            start = paragraph[0][0]
            end = paragraph[-1][0] + len(paragraph[-1][1])
            blocks.append(
                MarkdownBlock(
                    block_id=f"{section_id}-block-{len(blocks)}",
                    block_type=BlockType.PARAGRAPH,
                    text=text[start:end].strip(),
                    start_offset=offset + start,
                    end_offset=offset + end,
                )
            )
            paragraph.clear()

    if include_heading and lines:
        heading_line = lines[0]
        heading_end = len(heading_line)
        blocks.append(
            MarkdownBlock(
                block_id=f"{section_id}-block-{len(blocks)}",
                block_type=BlockType.HEADING,
                text=heading_line.rstrip("\r\n"),
                start_offset=offset,
                end_offset=offset + heading_end,
                metadata={"level": heading_level},
            )
        )
        cursor = heading_end
        lines = lines[1:]

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            if in_code:
                code_lines.append(line)
                end = cursor + len(line)
                blocks.append(
                    MarkdownBlock(
                        block_id=f"{section_id}-block-{len(blocks)}",
                        block_type=BlockType.CODE,
                        text=text[code_start:end].strip(),
                        start_offset=offset + code_start,
                        end_offset=offset + end,
                    )
                )
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
                code_start = cursor
                code_lines.append(line)
        elif in_code:
            code_lines.append(line)
        elif not stripped:
            flush_paragraph()
        elif stripped.startswith(("- ", "* ", "+ ")) or (
            stripped[:2].isdigit() and stripped[2:3] == "."
        ):
            flush_paragraph()
            end = cursor + len(line)
            blocks.append(
                MarkdownBlock(
                    block_id=f"{section_id}-block-{len(blocks)}",
                    block_type=BlockType.LIST,
                    text=stripped,
                    start_offset=offset + cursor,
                    end_offset=offset + end,
                )
            )
        elif stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            end = cursor + len(line)
            blocks.append(
                MarkdownBlock(
                    block_id=f"{section_id}-block-{len(blocks)}",
                    block_type=BlockType.TABLE,
                    text=stripped,
                    start_offset=offset + cursor,
                    end_offset=offset + end,
                )
            )
        else:
            paragraph.append((cursor, line))
        cursor += len(line)
    flush_paragraph()
    return tuple(blocks)


def _assemble_tree(nodes: list[SectionNode], *, relative_path: str, note_id: int | None) -> SectionNode:
    children_by_parent: dict[str | None, list[SectionNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_section_id, []).append(node)

    def build_children(parent_id: str | None) -> tuple[SectionNode, ...]:
        siblings = children_by_parent.get(parent_id, [])
        result: list[SectionNode] = []
        for index, node in enumerate(siblings):
            children = build_children(node.section_id)
            result.append(
                SectionNode(
                    **{
                        **node.__dict__,
                        "previous_sibling_id": siblings[index - 1].section_id if index else None,
                        "next_sibling_id": siblings[index + 1].section_id if index + 1 < len(siblings) else None,
                        "children": children,
                    }
                )
            )
        return tuple(result)

    children = build_children(None)
    return SectionNode(
        section_id="root",
        section_type="root",
        title=None,
        display_title=relative_path,
        is_empty_heading=False,
        level=None,
        section_path=(),
        direct_body="",
        blocks=(),
        start_offset=0,
        end_offset=0,
        children=children,
        metadata={"note_id": note_id, "relative_path": relative_path},
    )


def _find_parent(nodes: list[SectionNode], level: int) -> SectionNode | None:
    for node in reversed(nodes):
        if node.level is not None and node.level < level:
            return node
    return None


def _line_starts(lines: list[str]) -> list[int]:
    starts: list[int] = []
    cursor = 0
    for line in lines:
        starts.append(cursor)
        cursor += len(line)
    return starts


def _frontmatter_end_line(raw_text: str) -> int:
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return 0
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() in {"---", "..."}:
            return index + 1
    return 0


def _walk(node: SectionNode):
    yield node
    for child in node.children:
        yield from _walk(child)
