"""Unit tests for Sprint 26 rerank helpers (no HF download)."""

from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod, RetrievedChunk
from rag_based_on_obsidian.retrieval.rerank import IdentityReranker, build_reranker
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig


def _chunk(chunk_id: int, text: str, score: float, rank: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=score,
        retrieval_method=RetrievalMethod.HYBRID,
        metadata={},
        chunking_version="test",
        rank=rank,
    )


def test_identity_reranker_trims_and_renumbers() -> None:
    chunks = [
        _chunk(1, "a", 0.9, 1),
        _chunk(2, "b", 0.8, 2),
        _chunk(3, "c", 0.7, 3),
    ]
    out = IdentityReranker().rerank("q", chunks, top_k=2)
    assert [c.chunk_id for c in out] == [1, 2]
    assert [c.rank for c in out] == [1, 2]


def test_build_reranker_disabled_is_identity() -> None:
    config = RerankConfig(name="t", enabled=False)
    reranker = build_reranker(config)
    assert isinstance(reranker, IdentityReranker)


class _ReverseReranker:
    def ensure_loaded(self) -> None:
        return None

    def rerank(self, query: str, chunks: list[RetrievedChunk], *, top_k: int):
        _ = query
        ordered = list(reversed(chunks))[:top_k]
        return [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                score=float(len(chunks) - index),
                retrieval_method=chunk.retrieval_method,
                metadata=dict(chunk.metadata),
                chunking_version=chunk.chunking_version,
                rank=index,
                rerank_score=float(len(chunks) - index),
            )
            for index, chunk in enumerate(ordered, start=1)
        ]


def test_reverse_reranker_changes_order() -> None:
    chunks = [
        _chunk(1, "first", 0.9, 1),
        _chunk(2, "second", 0.8, 2),
    ]
    out = _ReverseReranker().rerank("q", chunks, top_k=2)
    assert [c.chunk_id for c in out] == [2, 1]
