from types import SimpleNamespace

import pytest

from rag_based_on_obsidian.embeddings.contracts import EmbeddingMetadata
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.pgvector import PgvectorDenseRetriever


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


class FakeResult:
    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return [
            {
                "chunk_id": 7,
                "text": "retrieved text",
                "chunking_version": "v1",
                "point_key": "key-7",
                "note_id": 3,
                "chunk_index": 0,
                "section_title": "Note",
                "section_level": 1,
                "section_path": ["Note"],
                "source_path": "DLS1/note.md",
                "start_offset": 0,
                "end_offset": 14,
                "distance": 0.09,
            }
        ]


class FakeConnection:
    def __init__(self) -> None:
        self.executed = None

    def execute(self, statement: object) -> FakeResult:
        self.executed = statement
        return FakeResult()

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeEngine:
    dialect = SimpleNamespace(name="sqlite")

    def __init__(self) -> None:
        self.connection = FakeConnection()

    def connect(self) -> FakeConnection:
        return self.connection


def test_pgvector_search_converts_cosine_distance_to_similarity() -> None:
    engine = FakeEngine()
    retriever = PgvectorDenseRetriever(
        engine,
        index_generation="gen-v1",
        provider=FakeProvider(),
    )
    results = retriever.search(
        "query",
        top_k=3,
        filters={"source_path": "DLS1/note.md"},
    )
    assert results[0].retrieval_method is RetrievalMethod.PGVECTOR
    assert results[0].chunk_id == 7
    assert results[0].score == pytest.approx(0.91)
    assert results[0].dense_score == pytest.approx(0.91)
    assert engine.connection.executed is not None


def test_pgvector_search_rejects_unknown_filter() -> None:
    retriever = PgvectorDenseRetriever(
        FakeEngine(),
        index_generation="gen-v1",
        provider=FakeProvider(),
    )
    with pytest.raises(TypeError, match="unsupported pgvector filter"):
        retriever.search("query", top_k=3, filters={"unknown": "x"})
