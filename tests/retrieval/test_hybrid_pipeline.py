import asyncio

from rag_based_on_obsidian.embeddings.contracts import EmbeddingMetadata
from rag_based_on_obsidian.retrieval.contracts import (
    RetrievalMethod,
    RetrievedChunk,
)
from rag_based_on_obsidian.retrieval.pipeline import HybridRetriever


class FakeProvider:
    metadata = EmbeddingMetadata(
        model_name="fake",
        model_revision="v1",
        device="cpu",
        dimension=2,
        normalized=True,
    )

    def embed_query(self, text: str) -> tuple[float, ...]:
        return (1.0, 0.0)


class FakeDense:
    def search_vector(self, vector, *, top_k, filters):
        assert vector == (1.0, 0.0)
        return [
            RetrievedChunk(
                chunk_id=1,
                text="dense result",
                score=0.9,
                retrieval_method=RetrievalMethod.DENSE,
                metadata={},
                chunking_version="v1",
                rank=1,
                point_key="key-1",
            )
        ]


class FakeLexical:
    def search(self, query, *, top_k, filters):
        return [
            RetrievedChunk(
                chunk_id=1,
                text="lexical result",
                score=2.0,
                retrieval_method=RetrievalMethod.BM25,
                metadata={},
                chunking_version="v1",
                rank=1,
                point_key="key-1",
            )
        ]


def test_hybrid_search_embeds_once_and_fuses_in_async_pipeline() -> None:
    retriever = HybridRetriever(
        dense=FakeDense(),
        lexical=FakeLexical(),
        provider=FakeProvider(),
    )

    results = asyncio.run(
        retriever.search(
            "query",
            top_k=1,
            candidate_k=2,
            rrf_k=60,
        )
    )

    assert len(results) == 1
    assert results[0].retrieval_method is RetrievalMethod.HYBRID
    assert results[0].dense_score == 0.9
    assert results[0].bm25_score == 2.0
