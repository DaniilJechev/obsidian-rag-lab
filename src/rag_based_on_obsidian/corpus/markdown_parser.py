"""Read and structurally parse Markdown selected by corpus discovery."""

import re

import yaml

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_entities import (
    Heading,
    ImageLink,
    ParsedDocument,
    Wikilink,
)

_FRONTMATTER_MARKER = re.compile(r"^(---|\.\.\.)[ \t]*$")
_HEADING_PATTERN = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?)|[ \t]*)$")
_IMAGE_LINK_PATTERN = re.compile(r"!\[\[([^\]]+)\]\]")
_WIKILINK_PATTERN = re.compile(r"(?<!\!)\[\[([^\]]+)\]\]")


def parse_markdown_file(discovered_file: DiscoveredFile) -> ParsedDocument:
    """Read one discovered Markdown file into the parser contract.

    Discovery owns path safety and allowlist enforcement. This function therefore
    reads only the supplied file and does not search directories or modify the
    source file.
    """

    raw_text = discovered_file.absolute_path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(raw_text)
    headings = _parse_headings(raw_text)
    image_links = _parse_image_links(raw_text)
    wikilinks = _parse_wikilinks(raw_text)

    return ParsedDocument(
        source=discovered_file,
        raw_text=raw_text,
        frontmatter=frontmatter,
        headings=headings,
        wikilinks=wikilinks,
        image_links=image_links,
    )


def _parse_frontmatter(raw_text: str) -> dict[str, object]:
    """Parse an optional YAML frontmatter block at the start of a document."""

    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if _FRONTMATTER_MARKER.fullmatch(line)
        ),
        None,
    )
    if closing_index is None:
        raise ValueError("Unclosed YAML frontmatter block")

    parsed = yaml.safe_load("\n".join(lines[1:closing_index]))
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise TypeError("YAML frontmatter must contain a mapping")
    return dict(parsed)


def _parse_headings(raw_text: str) -> tuple[Heading, ...]:
    """Extract ATX headings outside fenced code blocks."""

    headings: list[Heading] = []
    in_fenced_code = False

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue

        match = _HEADING_PATTERN.fullmatch(line)
        if match:
            headings.append(
                Heading(
                    level=len(match.group(1)),
                    text=(match.group(2) or "").strip(),
                    line_number=line_number,
                )
            )

    return tuple(headings)


def _parse_image_links(raw_text: str) -> tuple[ImageLink, ...]:
    """Extract Obsidian image embeds outside fenced code blocks."""

    return tuple(
        ImageLink(target=_link_target(match.group(1)), raw=match.group(0))
        for match in _iter_matches_outside_fences(_IMAGE_LINK_PATTERN, raw_text)
    )


def _parse_wikilinks(raw_text: str) -> tuple[Wikilink, ...]:
    """Extract Obsidian note links without treating image embeds as wikilinks."""

    links: list[Wikilink] = []
    for match in _iter_matches_outside_fences(_WIKILINK_PATTERN, raw_text):
        target_and_alias = match.group(1).split("|", maxsplit=1)
        target = target_and_alias[0].strip()
        alias = (
            target_and_alias[1].strip()
            if len(target_and_alias) == 2
            else None
        )
        links.append(
            Wikilink(
                target=target,
                raw=match.group(0),
                alias=alias,
            )
        )
    return tuple(links)


def _link_target(value: str) -> str:
    """Return the target part of an Obsidian link, excluding an optional alias."""

    return value.split("|", maxsplit=1)[0].strip()


def _iter_matches_outside_fences(
    pattern: re.Pattern[str],
    raw_text: str,
) -> list[re.Match[str]]:
    """Find regex matches on lines that are not inside fenced code blocks."""

    matches: list[re.Match[str]] = []
    in_fenced_code = False

    for line in raw_text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fenced_code = not in_fenced_code
        elif not in_fenced_code:
            matches.extend(pattern.finditer(line, pos=0))

    return matches
