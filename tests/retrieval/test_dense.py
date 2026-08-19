from types import SimpleNamespace

from rag_based_on_obsidian.embeddings.contracts import EmbeddingMetadata
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.dense import QdrantDenseRetriever


class FakeProvider:
    metadata = EmbeddingMetadata(
        model_name="fake",
        model_revision="v1",
        device="cpu",
        dimension=3,
        normalized=True,
    )

    def embed_query(self, text: str) -> tuple[float, ...]:
        return (1.0, 0.0, 0.0)


class FakeQdrant:
    def __init__(self) -> None:
        self.arguments: dict[str, object] = {}

    def query_points(self, **kwargs: object) -> object:
        self.arguments = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    score=0.91,
                    payload={
                        "chunk_id": 7,
                        "point_key": "key-7",
                        "text": "retrieved text",
                        "chunking_version": "v1",
                        "source_path": "DLS1/note.md",
                    },
                )
            ]
        )


def test_dense_search_maps_qdrant_payload_and_filter() -> None:
    client = FakeQdrant()
    retriever = QdrantDenseRetriever(
        client,
        collection_name="collection-v1",
        provider=FakeProvider(),
    )

    results = retriever.search(
        "query",
        top_k=3,
        filters={"source_path": "DLS1/note.md"},
    )

    assert results[0].retrieval_method is RetrievalMethod.DENSE
    assert results[0].chunk_id == 7
    assert client.arguments["limit"] == 3
    assert client.arguments["query"] == [1.0, 0.0, 0.0]
    assert client.arguments["query_filter"] is not None
