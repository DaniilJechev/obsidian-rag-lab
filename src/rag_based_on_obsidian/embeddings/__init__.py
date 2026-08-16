"""Embedding provider contracts and implementations."""

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingMetadata,
    EmbeddingProvider,
    EmbeddingVector,
    validate_vectors,
)
from rag_based_on_obsidian.embeddings.settings import (
    EmbeddingModelConfig,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)

__all__ = [
    "EmbeddingMetadata",
    "EmbeddingModelConfig",
    "EmbeddingProvider",
    "EmbeddingVector",
    "TransformersEmbeddingProvider",
    "load_embedding_model_config",
    "validate_vectors",
]
