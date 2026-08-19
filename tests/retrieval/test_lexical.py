from types import SimpleNamespace

from qdrant_client.models import Document

from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.lexical import QdrantSparseRetriever


class FakeQdrant:
    def __init__(self) -> None:
        self.arguments: dict[str, object] = {}

    def query_points(self, **kwargs: object) -> object:
        self.arguments = kwargs
        query_filter = kwargs.get("query_filter")
        must = getattr(query_filter, "must", ()) or ()
        source_path = None
        for condition in must:
            if getattr(condition, "key", None) == "source_path":
                source_path = getattr(getattr(condition, "match", None), "value", None)
        payload = {
            "chunk_id": 2 if source_path == "DLS2/b.md" else 1,
            "point_key": "key-filtered" if source_path == "DLS2/b.md" else "key-1",
            "text": "lexical keywords in the chunk",
            "chunking_version": "v1",
            "source_path": source_path or "DLS1/note.md",
        }
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    score=4.2,
                    payload=payload,
                )
            ]
        )


def test_sparse_search_maps_qdrant_payload() -> None:
    client = FakeQdrant()
    retriever = QdrantSparseRetriever(
        client,
        collection_name="collection-v1",
        chunking_version="v1",
        bm25_avg_len=191.0,
    )

    results = retriever.search("lexical keywords", top_k=1)

    assert len(results) == 1
    assert results[0].retrieval_method is RetrievalMethod.BM25
    assert results[0].chunk_id == 1
    assert results[0].chunking_version == "v1"
    assert results[0].point_key == "key-1"
    assert client.arguments["using"] == "bm25"
    assert client.arguments["limit"] == 1
    query = client.arguments["query"]
    assert isinstance(query, Document)
    assert query.text == "lexical keywords"


def test_sparse_search_applies_metadata_filter() -> None:
    client = FakeQdrant()
    retriever = QdrantSparseRetriever(
        client,
        collection_name="collection-v1",
        chunking_version="v1",
        bm25_avg_len=191.0,
    )

    results = retriever.search(
        "same query",
        top_k=5,
        filters={"source_path": "DLS2/b.md"},
    )

    assert [result.chunk_id for result in results] == [2]
    query_filter = client.arguments["query_filter"]
    keys = {condition.key for condition in query_filter.must}
    assert keys == {"source_path", "chunking_version"}
