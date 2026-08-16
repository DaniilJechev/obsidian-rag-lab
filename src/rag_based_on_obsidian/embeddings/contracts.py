"""Stable contracts shared by embedding providers and pipeline code."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

type EmbeddingVector = tuple[float, ...]


@dataclass(frozen=True)
class EmbeddingMetadata:
    """Operational identity and shape of vectors produced by one provider."""

    model_name: str
    model_revision: str
    device: str
    dimension: int
    normalized: bool

    def __post_init__(self) -> None:
        """Reject metadata that could make vectors impossible to interpret."""
        if not self.model_name.strip():
            raise ValueError("model_name must not be empty")
        if not self.model_revision.strip():
            raise ValueError("model_revision must not be empty")
        if not self.device.strip():
            raise ValueError("device must not be empty")
        if self.dimension <= 0:
            raise ValueError("dimension must be positive")


class EmbeddingProvider(Protocol):
    """Provider boundary independent of a concrete ML framework or model."""

    @property
    def metadata(self) -> EmbeddingMetadata:
        """Return the immutable model and vector contract."""

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[EmbeddingVector]:
        """Embed documents in input order, returning one vector per text."""

    def embed_query(self, text: str) -> EmbeddingVector:
        """Embed one query using the same vector space as documents."""


def validate_vectors(
    vectors: Sequence[EmbeddingVector],
    *,
    expected_count: int,
    metadata: EmbeddingMetadata,
) -> None:
    """Validate provider output before it crosses into persistence or retrieval."""
    if expected_count < 0:
        raise ValueError("expected_count must be non-negative")
    if len(vectors) != expected_count:
        raise ValueError("provider returned an unexpected number of vectors")

    for vector in vectors:
        if len(vector) != metadata.dimension:
            raise ValueError("provider returned an unexpected vector dimension")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("provider returned a vector containing NaN or Inf")
