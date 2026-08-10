"""Immutable entities for parsed Obsidian Markdown documents."""

from dataclasses import dataclass

from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile


@dataclass(frozen=True)
class Heading:
    """A Markdown heading without the body text below it."""

    level: int
    text: str
    line_number: int


@dataclass(frozen=True)
class Wikilink:
    """An Obsidian note link such as ``[[RAG|Retrieval Augmented Generation]]``."""

    target: str
    raw: str
    alias: str | None = None


@dataclass(frozen=True)
class ImageLink:
    """An Obsidian image embed kept separate from ordinary note links."""

    target: str
    raw: str


@dataclass(frozen=True)
class ParsedDocument:
    """Structured content parsed from one discovered Markdown file."""

    source: DiscoveredFile
    raw_text: str
    frontmatter: dict[str, object]
    headings: tuple[Heading, ...] = ()
    wikilinks: tuple[Wikilink, ...] = ()
    image_links: tuple[ImageLink, ...] = ()

    @property
    def filename(self) -> str:
        """Return the source filename without duplicating provenance data."""

        return self.source.absolute_path.name

    @property
    def folder(self) -> str:
        """Return the source folder relative to the configured vault root."""

        return self.source.relative_path.parent.as_posix()
