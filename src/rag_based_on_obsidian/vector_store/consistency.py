"""Consistency verification between PostgreSQL chunks and Qdrant points."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from qdrant_client import QdrantClient

from rag_based_on_obsidian.storage_identity import stable_point_key

type ChunkRow = Mapping[str, object]


class VersionedChunkReader(Protocol):
    """Minimal PostgreSQL reader contract needed for consistency checks."""

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> Iterable[list[dict[str, object]]]:
        """Yield all chunks belonging to one explicit version."""


@dataclass(frozen=True)
class MetadataMismatch:
    """One Qdrant payload that differs from its PostgreSQL source row."""

    point_key: str
    fields: tuple[str, ...]


@dataclass(frozen=True)
class ConsistencyReport:
    """Deterministic comparison result for one chunking version."""

    postgres_points: int
    qdrant_points: int
    missing_point_keys: tuple[str, ...]
    extra_point_keys: tuple[str, ...]
    metadata_mismatches: tuple[MetadataMismatch, ...]

    @property
    def mismatch_count(self) -> int:
        """Return one count covering missing, extra and mismatched records."""
        return (
            len(self.missing_point_keys)
            + len(self.extra_point_keys)
            + len(self.metadata_mismatches)
        )

    @property
    def is_consistent(self) -> bool:
        """Return whether both stores describe the same point set and payload."""
        return self.mismatch_count == 0


class QdrantConsistencyVerifier:
    """Compare versioned PostgreSQL chunk rows with Qdrant payloads."""

    def __init__(
        self,
        client: QdrantClient,
        *,
        collection_name: str,
        page_size: int = 256,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.client = client
        self.collection_name = collection_name
        self.page_size = page_size

    def verify(
        self,
        repository: VersionedChunkReader,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> ConsistencyReport:
        """Compare IDs and retrieval payload fields across both stores."""
        expected = {
            stable_point_key_from_row(chunk): chunk
            for batch in repository.iter_by_version(
                chunking_version=chunking_version,
                batch_size=batch_size,
            )
            for chunk in batch
        }
        actual = self._read_points()
        missing = tuple(sorted(set(expected) - set(actual)))
        extra = tuple(sorted(set(actual) - set(expected)))
        mismatches = tuple(
            MetadataMismatch(
                point_key=point_key,
                fields=_mismatched_fields(
                    expected[point_key],
                    actual[point_key],
                ),
            )
            for point_key in sorted(set(expected) & set(actual))
            if _mismatched_fields(expected[point_key], actual[point_key])
        )
        return ConsistencyReport(
            postgres_points=len(expected),
            qdrant_points=len(actual),
            missing_point_keys=missing,
            extra_point_keys=extra,
            metadata_mismatches=mismatches,
        )

    def _read_points(self) -> dict[str, Mapping[str, object]]:
        points: dict[str, Mapping[str, object]] = {}
        offset: Any = None
        while True:
            page, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=self.page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in page:
                payload = point.payload or {}
                if not isinstance(payload, Mapping):
                    raise TypeError("Qdrant point payload must be a mapping")
                point_key = payload.get("point_key")
                if not isinstance(point_key, str) or not point_key:
                    raise ValueError(
                        f"Qdrant point {point.id} has no valid point_key"
                    )
                points[point_key] = payload
            if offset is None:
                return points


_PAYLOAD_FIELDS = (
    "chunk_id",
    "note_id",
    "chunk_index",
    "chunking_version",
    "text",
    "section_title",
    "section_level",
    "section_path",
    "source_path",
    "start_offset",
    "end_offset",
)


def stable_point_key_from_row(chunk: ChunkRow) -> str:
    """Build the same stable key used by Qdrant payload generation."""
    chunk_id = chunk.get("chunk_id")
    note_id = chunk.get("note_id")
    chunk_index = chunk.get("chunk_index")
    chunking_version = chunk.get("chunking_version")
    if not all(
        isinstance(value, int)
        for value in (chunk_id, note_id, chunk_index)
    ):
        raise TypeError("chunk identity fields must be integers")
    if not isinstance(chunking_version, str):
        raise TypeError("chunking_version must be a string")
    source_path = chunk.get("source_path")
    source_hash = chunk.get("source_content_hash")
    if not isinstance(source_path, str):
        raise TypeError("source_path must be a string")
    if not isinstance(source_hash, str):
        raise TypeError("source_content_hash must be a string")
    return stable_point_key(
        source_path=source_path,
        source_content_hash=source_hash,
        chunking_version=chunking_version,
        chunk_index=chunk_index,
    )


def _mismatched_fields(
    expected: ChunkRow,
    actual: Mapping[str, object],
) -> tuple[str, ...]:
    return tuple(
        field
        for field in _PAYLOAD_FIELDS
        if _normalize(expected.get(field)) != _normalize(actual.get(field))
    )


def _normalize(value: object) -> object:
    if isinstance(value, list | tuple):
        return tuple(_normalize(item) for item in value)
    return value
