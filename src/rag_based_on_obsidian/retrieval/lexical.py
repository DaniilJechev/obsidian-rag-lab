"""Version-aware in-memory BM25 retrieval over PostgreSQL chunk rows."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.storage_identity import stable_point_key


@dataclass(frozen=True)
class _LexicalEntry:
    """A chunk row retained alongside the BM25 corpus position."""

    chunk_id: int
    text: str
    chunking_version: str
    point_key: str
    metadata: Mapping[str, object]


class InMemoryBM25Index:
    """Build one explicit chunk-version BM25 index in process memory."""

    def __init__(
        self,
        entries: Sequence[_LexicalEntry],
        *,
        tokenizer: Any = None,
    ) -> None:
        if not entries:
            raise ValueError("BM25 index requires at least one chunk")
        self._entries = tuple(entries)
        self._tokenizer = tokenizer or _tokenize
        corpus = [
            self._tokenizer(entry.text)
            for entry in self._entries
        ]
        self._index = BM25Okapi(corpus)
        self.chunking_version = self._entries[0].chunking_version

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, object]],
        *,
        chunking_version: str,
    ) -> "InMemoryBM25Index":
        """Create an index from one explicit PostgreSQL chunking version."""
        if not chunking_version.strip():
            raise ValueError("chunking_version must not be empty")
        entries = tuple(
            _entry_from_row(row, chunking_version=chunking_version)
            for row in rows
        )
        return cls(entries)

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: Mapping[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """Return deterministic lexical matches for one query."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_tokens = self._tokenizer(query)
        scores = self._index.get_scores(query_tokens)
        candidates = [
            (index, float(scores[index]))
            for index in range(len(self._entries))
            if _matches_filters(self._entries[index].metadata, filters)
        ]
        candidates.sort(
            key=lambda item: (-item[1], self._entries[item[0]].point_key)
        )
        results: list[RetrievedChunk] = []
        for rank, (index, score) in enumerate(candidates[:top_k], start=1):
            entry = self._entries[index]
            results.append(
                RetrievedChunk(
                    chunk_id=entry.chunk_id,
                    text=entry.text,
                    score=score,
                    retrieval_method=RetrievalMethod.BM25,
                    metadata=entry.metadata,
                    chunking_version=entry.chunking_version,
                    rank=rank,
                    point_key=entry.point_key,
                    bm25_score=score,
                )
            )
        return results


def _entry_from_row(
    row: Mapping[str, object],
    *,
    chunking_version: str,
) -> _LexicalEntry:
    chunk_id = _required_int(row, "chunk_id")
    note_id = _required_int(row, "note_id")
    chunk_index = _required_int(row, "chunk_index")
    row_version = row.get("chunking_version")
    if row_version != chunking_version:
        raise ValueError("row chunking_version does not match index version")
    text = _required_text(row, "text")
    source_path = _required_text(row, "source_path")
    source_hash = _required_text(row, "source_content_hash")
    point_key = stable_point_key(
        source_path=source_path,
        source_content_hash=source_hash,
        chunking_version=chunking_version,
        chunk_index=chunk_index,
    )
    metadata = {
        key: value
        for key, value in row.items()
        if key != "text"
    }
    metadata["note_id"] = note_id
    metadata["chunk_id"] = chunk_id
    return _LexicalEntry(
        chunk_id=chunk_id,
        text=text,
        chunking_version=chunking_version,
        point_key=point_key,
        metadata=metadata,
    )


def _matches_filters(
    metadata: Mapping[str, object],
    filters: Mapping[str, object] | None,
) -> bool:
    if not filters:
        return True
    return all(metadata.get(key) == value for key, value in filters.items())


def _required_int(row: Mapping[str, object], key: str) -> int:
    value = row.get(key)
    if not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    return value


def _required_text(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{key} must be a non-empty string")
    return value


def _tokenize(text: str) -> list[str]:
    return text.lower().split()
