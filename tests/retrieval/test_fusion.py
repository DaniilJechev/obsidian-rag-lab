from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.fusion import reciprocal_rank_fusion


def _result(
    *,
    chunk_id: int,
    point_key: str,
    method: RetrievalMethod,
    score: float,
    rank: int,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=f"chunk {chunk_id}",
        score=score,
        retrieval_method=method,
        metadata={"source_path": f"note-{chunk_id}.md"},
        chunking_version="v1",
        rank=rank,
        point_key=point_key,
    )


def test_rrf_deduplicates_and_preserves_backend_scores() -> None:
    dense = [
        _result(
            chunk_id=1,
            point_key="same",
            method=RetrievalMethod.DENSE,
            score=0.9,
            rank=1,
        ),
        _result(
            chunk_id=2,
            point_key="dense-only",
            method=RetrievalMethod.DENSE,
            score=0.8,
            rank=2,
        ),
    ]
    lexical = [
        _result(
            chunk_id=1,
            point_key="same",
            method=RetrievalMethod.BM25,
            score=4.0,
            rank=1,
        ),
    ]

    results = reciprocal_rank_fusion(
        (dense, lexical),
        top_k=2,
        rrf_k=60,
    )

    assert [result.point_key for result in results] == ["same", "dense-only"]
    assert results[0].retrieval_method is RetrievalMethod.HYBRID
    assert results[0].dense_score == 0.9
    assert results[0].bm25_score == 4.0
    assert results[0].rrf_score == results[0].score
