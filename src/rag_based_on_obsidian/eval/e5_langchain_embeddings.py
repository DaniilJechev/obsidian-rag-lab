"""LangChain Embeddings duck-type over the local e5 provider."""

from __future__ import annotations

from rag_based_on_obsidian.embeddings.contracts import EmbeddingProvider


class E5LangchainEmbeddings:
    """Expose ``embed_documents`` / ``embed_query`` for ragas wrappers."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(vector) for vector in self._provider.embed_documents(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(self._provider.embed_query(text))
