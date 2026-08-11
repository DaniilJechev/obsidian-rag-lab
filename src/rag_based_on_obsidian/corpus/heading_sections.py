"""Extract direct and full-span Markdown heading sections."""

from dataclasses import dataclass

from rag_based_on_obsidian.corpus.markdown_entities import Heading, ParsedDocument


@dataclass(frozen=True)
class HeadingSection:
    """Text span associated with one heading or pre-heading content."""

    level: int | None
    title: str
    start_line: int
    end_line: int
    direct_body: str
    full_span: str


def extract_heading_sections(document: ParsedDocument) -> tuple[HeadingSection, ...]:
    """Return pre-heading and heading sections using parser heading positions."""

    lines = document.raw_text.splitlines()
    headings = document.headings
    sections: list[HeadingSection] = []

    first_heading_line = headings[0].line_number if headings else len(lines) + 1
    if first_heading_line > 1:
        sections.append(
            HeadingSection(
                level=None,
                title="__pre_heading__",
                start_line=1,
                end_line=first_heading_line - 1,
                direct_body="\n".join(lines[: first_heading_line - 1]).strip(),
                full_span="\n".join(lines[: first_heading_line - 1]).strip(),
            )
        )

    for index, heading in enumerate(headings):
        next_heading_line = _next_heading_line(
            headings,
            index,
            maximum_level=6,
            default=len(lines) + 1,
        )
        full_span_end_line = _next_heading_line(
            headings,
            index,
            maximum_level=heading.level,
            default=len(lines) + 1,
        )
        direct_end_index = _direct_body_end_index(
            next_heading_line,
        )
        start_index = heading.line_number - 1
        direct_body = "\n".join(
            lines[heading.line_number:direct_end_index]
        ).strip()
        full_span = "\n".join(
            lines[start_index : full_span_end_line - 1]
        ).strip()
        sections.append(
            HeadingSection(
                level=heading.level,
                title=heading.text,
                start_line=heading.line_number,
                end_line=full_span_end_line - 1,
                direct_body=direct_body,
                full_span=full_span,
            )
        )

    return tuple(sections)


def _direct_body_end_index(
    next_heading_line: int,
) -> int:
    """Stop direct body before the next heading of any level."""

    return next_heading_line - 1


def _next_heading_line(
    headings: tuple[Heading, ...],
    index: int,
    maximum_level: int,
    default: int,
) -> int:
    """Find the next heading at or above the requested hierarchy boundary."""

    for following_heading in headings[index + 1 :]:
        if following_heading.level <= maximum_level:
            return following_heading.line_number
    return default
