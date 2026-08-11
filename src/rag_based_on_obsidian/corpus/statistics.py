"""Calculate inventory statistics for parsed Markdown documents."""

import hashlib
from statistics import mean, median

from rag_based_on_obsidian.corpus.analysis_text import build_analysis_text
from rag_based_on_obsidian.corpus.heading_sections import extract_heading_sections
from rag_based_on_obsidian.corpus.inventory_entities import (
    DocumentStatistics,
    HeadingStatistics,
    LanguageStatistics,
    TokenCount,
)
from rag_based_on_obsidian.corpus.language_classifier import (
    WordLanguage,
    classify_word,
)
from rag_based_on_obsidian.corpus.markdown_entities import ParsedDocument
from rag_based_on_obsidian.corpus.paragraph_blocks import extract_paragraph_blocks
from rag_based_on_obsidian.corpus.word_tokenizer import (
    WORD_TOKENIZER_NAME,
    tokenize_words,
)


def calculate_document_statistics(
    document: ParsedDocument,
) -> DocumentStatistics:
    """Calculate deterministic statistics for one parsed document."""

    analysis_text = build_analysis_text(document)
    words = tokenize_words(analysis_text)
    language_statistics = _language_statistics(words)
    heading_statistics = _heading_statistics(document)
    paragraph_blocks = extract_paragraph_blocks(document)
    anomalies = _document_anomalies(document, analysis_text)

    return DocumentStatistics(
        source=document.source,
        analysis_text=analysis_text,
        file_size_bytes=len(document.raw_text.encode("utf-8")),
        character_count=len(document.raw_text),
        word_count=len(words),
        token_counts=(TokenCount(WORD_TOKENIZER_NAME, len(words)),),
        heading_statistics=heading_statistics,
        paragraph_blocks=paragraph_blocks,
        language_statistics=language_statistics,
        anomalies=anomalies,
        content_hash=hashlib.sha256(
            document.raw_text.encode("utf-8")
        ).hexdigest(),
    )


def _language_statistics(words: tuple[str, ...]) -> LanguageStatistics:
    counts = {language: 0 for language in WordLanguage}
    for word in words:
        counts[classify_word(word)] += 1
    return LanguageStatistics(
        russian_word_count=counts[WordLanguage.RUSSIAN],
        english_word_count=counts[WordLanguage.ENGLISH],
        mixed_or_other_word_count=counts[WordLanguage.MIXED_OR_OTHER],
        unknown_word_count=counts[WordLanguage.UNKNOWN],
    )


def _heading_statistics(
    document: ParsedDocument,
) -> tuple[HeadingStatistics, ...]:
    sections = extract_heading_sections(document)
    result: list[HeadingStatistics] = []
    for view in ("direct_body", "full_span"):
        for level in (None, 1, 2, 3, 4, 5, 6):
            word_counts = [
                len(tokenize_words(getattr(section, view)))
                for section in sections
                if section.level == level
            ]
            if not word_counts:
                continue
            result.append(
                HeadingStatistics(
                    level=level,
                    view=view,
                    section_count=len(word_counts),
                    mean_word_count=mean(word_counts),
                    median_word_count=median(word_counts),
                    mean_token_counts=(
                        TokenCount(WORD_TOKENIZER_NAME, mean(word_counts)),
                    ),
                    median_token_counts=(
                        TokenCount(WORD_TOKENIZER_NAME, median(word_counts)),
                    ),
                )
            )
    return tuple(result)


def _document_anomalies(
    document: ParsedDocument,
    analysis_text: str,
) -> tuple[str, ...]:
    anomalies: list[str] = []
    if not document.raw_text.strip():
        anomalies.append("empty_document")
    elif not analysis_text.strip():
        anomalies.append("no_text_after_structure")
    return tuple(anomalies)
