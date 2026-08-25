from rag_based_on_obsidian.embeddings.contracts import EmbeddingMetadata
from rag_based_on_obsidian.eval.e5_langchain_embeddings import E5LangchainEmbeddings


class _FakeProvider:
    @property
    def metadata(self) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            model_name="fake-e5",
            model_revision="main",
            device="cpu",
            dimension=2,
            normalized=True,
        )

    def embed_documents(self, texts: list[str]) -> list[tuple[float, ...]]:
        return [(1.0, 0.0) for _ in texts]

    def embed_query(self, text: str) -> tuple[float, ...]:
        assert text
        return (0.0, 1.0)


def test_e5_langchain_embeddings_returns_lists() -> None:
    wrapper = E5LangchainEmbeddings(_FakeProvider())
    assert wrapper.embed_documents(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]
    assert wrapper.embed_query("q") == [0.0, 1.0]
