"""Domain contract for versioned retrieval chunks."""

import re
from dataclasses import dataclass

_WORD_PATTERN = re.compile(r"\b\w+\b", re.UNICODE)
_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def word_count(text: str) -> int:
    """Count words with a deterministic Unicode-aware proxy."""
    return len(_WORD_PATTERN.findall(text))


def estimated_token_count(text: str) -> int:
    """Estimate tokens without coupling chunking to an LLM tokenizer."""
    return len(_TOKEN_PATTERN.findall(text))


@dataclass(frozen=True)
class ChunkRecord:
    """One versioned retrieval unit derived from one SectionTree section."""

    note_id: int
    chunk_index: int
    text: str
    section_id: str
    section_title: str | None
    section_level: int | None
    section_path: tuple[str, ...]
    section_type: str
    start_offset: int
    end_offset: int
    word_count: int
    token_count: int
    parser_version: str
    source_content_hash: str
    chunking_version: str

    def __post_init__(self) -> None:
        """Validate identity and source-span invariants."""
        if self.note_id < 0:
            raise ValueError("note_id must be non-negative")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")
        if not self.text.strip():
            raise ValueError("text must not be empty")
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError("chunk offsets must be an ordered non-negative span")
        if self.word_count != word_count(self.text):
            raise ValueError("word_count does not match text")
        if self.token_count != estimated_token_count(self.text):
            raise ValueError("token_count does not match text")
        if not self.parser_version:
            raise ValueError("parser_version must not be empty")
        if not self.source_content_hash:
            raise ValueError("source_content_hash must not be empty")
        if not self.chunking_version:
            raise ValueError("chunking_version must not be empty")
