"""Deterministic Unicode-aware word tokenization for corpus EDA."""

import re

WORD_TOKENIZER_NAME = "unicode_word_tokenizer"
WORD_TOKENIZER_VERSION = "1.0"

_WORD_PATTERN = re.compile(
    r"https?://\S+|[^\W_]+(?:[-_][^\W_]+)*",
    flags=re.UNICODE,
)


def tokenize_words(text: str) -> tuple[str, ...]:
    """Return natural words while excluding URLs and technical identifiers."""

    tokens = (match.group(0) for match in _WORD_PATTERN.finditer(text))
    return tuple(
        token
        for token in tokens
        if not token.startswith(("http://", "https://"))
        and "_" not in token
        and not any(character.isdigit() for character in token)
    )
