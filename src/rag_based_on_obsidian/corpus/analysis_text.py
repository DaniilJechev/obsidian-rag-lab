"""Build normalized text views for inventory analysis without mutating source."""

import re

from rag_based_on_obsidian.corpus.markdown_entities import ParsedDocument

_MARKDOWN_DELIMITER_PATTERN = re.compile(r"(!?)(\[\[|\]\]|`{1,3}|\*\*|__|[*_#])")


def build_analysis_text(document: ParsedDocument) -> str:
    """Return analysis text with syntax delimiters removed and content preserved."""

    return _MARKDOWN_DELIMITER_PATTERN.sub("", document.raw_text)
