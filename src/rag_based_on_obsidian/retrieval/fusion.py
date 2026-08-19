"""Rank-based fusion for dense and lexical retrieval results."""

from collections.abc import Sequence

from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
    retrieval_key,
)


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence[RetrievedChunk]],
    *,
    top_k: int,
    rrf_k: int = 60,
) -> list[RetrievedChunk]:
    """Fuse ranked lists without comparing incompatible raw score scales."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")

    aggregate: dict[str, dict[str, object]] = {}
    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            key = retrieval_key(result)
            state = aggregate.setdefault(
                key,
                {
                    "result": result,
                    "rrf_score": 0.0,
                    "dense_score": None,
                    "bm25_score": None,
                },
            )
            state["rrf_score"] = float(state["rrf_score"]) + (
                1.0 / (rrf_k + rank)
            )
            if result.retrieval_method is RetrievalMethod.DENSE:
                state["dense_score"] = result.score
            elif result.retrieval_method is RetrievalMethod.BM25:
                state["bm25_score"] = result.score

    ordered = sorted(
        aggregate.items(),
        key=lambda item: (-float(item[1]["rrf_score"]), item[0]),
    )
    fused: list[RetrievedChunk] = []
    for rank, (_, state) in enumerate(ordered[:top_k], start=1):
        result = state["result"]
        assert isinstance(result, RetrievedChunk)
        rrf_score = float(state["rrf_score"])
        fused.append(
            RetrievedChunk(
                chunk_id=result.chunk_id,
                text=result.text,
                score=rrf_score,
                retrieval_method=RetrievalMethod.HYBRID,
                metadata=result.metadata,
                chunking_version=result.chunking_version,
                rank=rank,
                point_key=result.point_key,
                dense_score=_optional_float(state["dense_score"]),
                bm25_score=_optional_float(state["bm25_score"]),
                rrf_score=rrf_score,
            )
        )
    return fused


def _optional_float(value: object) -> float | None:
    return float(value) if value is not None else None
