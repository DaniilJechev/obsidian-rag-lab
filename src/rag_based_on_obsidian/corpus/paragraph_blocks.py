"""Extract paragraph-like Markdown blocks for chunking analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_based_on_obsidian.corpus.heading_sections import (
    HeadingSection,
    extract_heading_sections,
)
from rag_based_on_obsidian.corpus.markdown_entities import ParsedDocument

_HEADING_LINE = re.compile(r"^\s{0,3}#{1,6}(?:\s+.*)?$")
_IMAGE_EMBED = re.compile(r"!\[\[[^\]]+\]\]")
_WIKILINK = re.compile(r"(?<!\!)\[\[[^\]]+\]\]")
_FENCED_CODE = re.compile(r"^\s*(```|~~~)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_BLOCKQUOTE = re.compile(r"^\s*>")


@dataclass(frozen=True)
class ParagraphBlock:
    """One non-empty blank-line-delimited block and its heading level."""

    level: int | None
    word_count: int
    token_count: int
    character_count: int
    byte_count: int
    russian_word_count: int
    english_word_count: int
    mixed_or_other_word_count: int
    unknown_word_count: int
    wikilink_count: int
    image_embed_count: int
    code_block_count: int
    list_item_count: int
    blockquote_line_count: int


def extract_paragraph_blocks(
    document: ParsedDocument,
) -> tuple[ParagraphBlock, ...]:
    """Extract blocks from each heading section, excluding heading lines."""

    blocks: list[ParagraphBlock] = []
    for section in extract_heading_sections(document):
        blocks.extend(_blocks_from_section(section, document))
    return tuple(blocks)


def _blocks_from_section(
    section: HeadingSection,
    document: ParsedDocument,
) -> list[ParagraphBlock]:
    text = section.direct_body
    raw_blocks = re.split(r"\n\s*\n", text)
    meaningful_blocks = [
        block
        for block in raw_blocks
        if block.strip() and not _HEADING_LINE.fullmatch(block.strip())
    ]
    if meaningful_blocks:
        return [_build_block(section.level, block) for block in meaningful_blocks]
    if section.level is not None:
        return [_build_block(section.level, "")]
    return []


def _build_block(level: int | None, text: str) -> ParagraphBlock:
    from rag_based_on_obsidian.corpus.language_classifier import (
        WordLanguage,
        classify_word,
    )
    from rag_based_on_obsidian.corpus.word_tokenizer import tokenize_words

    words = tokenize_words(text)
    language_counts = {language: 0 for language in WordLanguage}
    for word in words:
        language_counts[classify_word(word)] += 1
    lines = text.splitlines()
    code_block_count = sum(
        1 for line in lines if _FENCED_CODE.match(line)
    ) // 2
    return ParagraphBlock(
        level=level,
        word_count=len(words),
        token_count=len(words),
        character_count=len(text),
        byte_count=len(text.encode("utf-8")),
        russian_word_count=language_counts[WordLanguage.RUSSIAN],
        english_word_count=language_counts[WordLanguage.ENGLISH],
        mixed_or_other_word_count=language_counts[WordLanguage.MIXED_OR_OTHER],
        unknown_word_count=language_counts[WordLanguage.UNKNOWN],
        wikilink_count=len(_WIKILINK.findall(text)),
        image_embed_count=len(_IMAGE_EMBED.findall(text)),
        code_block_count=code_block_count,
        list_item_count=sum(1 for line in lines if _LIST_ITEM.match(line)),
        blockquote_line_count=sum(1 for line in lines if _BLOCKQUOTE.match(line)),
    )
