"""Unit tests for PostgreSQL/Qdrant consistency verification."""

from types import SimpleNamespace

from rag_based_on_obsidian.vector_store.consistency import (
    QdrantConsistencyVerifier,
    stable_point_key_from_row,
)


class FakeQdrantClient:
    """Qdrant scroll double returning a deterministic point page."""

    def __init__(self, points: list[object]) -> None:
        self.points = points

    def scroll(self, **kwargs: object) -> tuple[list[object], None]:
        del kwargs
        return self.points, None


class FakeRepository:
    """PostgreSQL chunk reader double for consistency tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def iter_by_version(
        self,
        *,
        chunking_version: str,
        batch_size: int,
    ) -> list[list[dict[str, object]]]:
        del chunking_version, batch_size
        return [self.rows]


def _row(chunk_id: int, text: str) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "note_id": 1,
        "chunk_index": chunk_id - 1,
        "chunking_version": "chunk-v1",
        "text": text,
        "section_title": "Section",
        "section_level": 1,
        "section_path": ["Section"],
        "source_path": "DLS1/note.md",
        "source_content_hash": "hash-1",
        "start_offset": 0,
        "end_offset": len(text),
    }


def _point(row: dict[str, object]) -> object:
    return SimpleNamespace(
        id=row["chunk_id"],
        payload={
            key: value
            for key, value in row.items()
            if key != "chunk_id"
        }
        | {
            "chunk_id": row["chunk_id"],
            "point_key": stable_point_key_from_row(row),
        },
    )


def test_consistency_report_detects_missing_extra_and_metadata_mismatch() -> None:
    repository = FakeRepository([_row(1, "one"), _row(2, "two")])
    mismatched = _row(1, "changed")
    extra = _row(3, "extra")
    verifier = QdrantConsistencyVerifier(
        FakeQdrantClient([_point(mismatched), _point(extra)]),
        collection_name="rag_chunks__chunk-v1",
    )

    report = verifier.verify(
        repository,
        chunking_version="chunk-v1",
        batch_size=2,
    )

    assert report.postgres_points == 2
    assert report.qdrant_points == 2
    assert len(report.missing_point_keys) == 1
    assert len(report.extra_point_keys) == 1
    assert report.metadata_mismatches[0].point_key
    assert "text" in report.metadata_mismatches[0].fields
    assert report.mismatch_count == 3
    assert not report.is_consistent


def test_consistency_report_accepts_matching_points() -> None:
    rows = [_row(1, "one"), _row(2, "two")]
    verifier = QdrantConsistencyVerifier(
        FakeQdrantClient([_point(row) for row in rows]),
        collection_name="rag_chunks__chunk-v1",
    )

    report = verifier.verify(
        FakeRepository(rows),
        chunking_version="chunk-v1",
        batch_size=2,
    )

    assert report.mismatch_count == 0
    assert report.is_consistent
