import pytest

from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.lexical import InMemoryBM25Index


def _row(
    chunk_id: int,
    text: str,
    *,
    source_path: str = "DLS1/note.md",
) -> dict[str, object]:
    return {
        "chunk_id": chunk_id,
        "note_id": 1,
        "chunk_index": chunk_id - 1,
        "chunking_version": "v1",
        "text": text,
        "source_path": source_path,
        "source_content_hash": f"hash-{chunk_id}",
    }


def test_bm25_search_returns_versioned_provenance() -> None:
    index = InMemoryBM25Index.from_rows(
        (
            _row(1, "BM25 finds lexical keywords"),
            _row(2, "Dense retrieval finds semantic meaning"),
        ),
        chunking_version="v1",
    )

    results = index.search("lexical keywords", top_k=1)

    assert len(results) == 1
    assert results[0].retrieval_method is RetrievalMethod.BM25
    assert results[0].chunk_id == 1
    assert results[0].chunking_version == "v1"
    assert results[0].point_key


def test_bm25_applies_metadata_filter() -> None:
    index = InMemoryBM25Index.from_rows(
        (
            _row(1, "same query", source_path="DLS1/a.md"),
            _row(2, "same query", source_path="DLS2/b.md"),
        ),
        chunking_version="v1",
    )

    results = index.search(
        "same query",
        top_k=5,
        filters={"source_path": "DLS2/b.md"},
    )

    assert [result.chunk_id for result in results] == [2]


def test_bm25_rejects_mixed_versions() -> None:
    with pytest.raises(ValueError, match="does not match"):
        InMemoryBM25Index.from_rows(
            [_row(1, "text") | {"chunking_version": "v2"}],
            chunking_version="v1",
        )
