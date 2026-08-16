"""Embedding provider contracts and implementations."""

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingMetadata,
    EmbeddingProvider,
    EmbeddingVector,
    validate_vectors,
)
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    BatchEmbeddingResult,
    EmbeddedChunk,
    EmbeddingFailure,
    JsonArtifactWriter,
    validate_embedding_batch,
)
from rag_based_on_obsidian.embeddings.settings import (
    BatchEmbeddingConfig,
    EmbeddingModelConfig,
    load_batch_embedding_config,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)

__all__ = [
    "BatchEmbeddingConfig",
    "BatchEmbeddingPipeline",
    "BatchEmbeddingResult",
    "EmbeddedChunk",
    "EmbeddingFailure",
    "EmbeddingMetadata",
    "EmbeddingModelConfig",
    "EmbeddingProvider",
    "EmbeddingVector",
    "JsonArtifactWriter",
    "TransformersEmbeddingProvider",
    "load_batch_embedding_config",
    "load_embedding_model_config",
    "validate_embedding_batch",
    "validate_vectors",
]
