from rag_based_on_obsidian.eval.contracts import collapse_chunks_to_notes
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk


def _chunk(chunk_id: int, note_id: int, rank: int, path: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text="body",
        score=1.0,
        retrieval_method=RetrievalMethod.HYBRID,
        metadata={"note_id": note_id, "source_path": path},
        chunking_version="v1",
        rank=rank,
        point_key=f"key-{chunk_id}",
    )


def test_collapse_keeps_first_note_occurrence() -> None:
    chunks = [
        _chunk(1, 10, 1, "DLS1/a.md"),
        _chunk(2, 10, 2, "DLS1/a.md"),
        _chunk(3, 20, 3, "DLS2/b.md"),
    ]

    notes = collapse_chunks_to_notes(chunks)

    assert [note.note_id for note in notes] == [10, 20]
    assert [note.rank for note in notes] == [1, 2]
    assert notes[0].source_path == "DLS1/a.md"
