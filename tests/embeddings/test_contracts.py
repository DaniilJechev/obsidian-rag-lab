"""Tests for the framework-independent embedding provider contract."""

import pytest

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingMetadata,
    validate_vectors,
)


def test_embedding_metadata_rejects_invalid_dimension() -> None:
    with pytest.raises(ValueError, match="dimension"):
        EmbeddingMetadata(
            model_name="test-model",
            model_revision="v1",
            device="cpu",
            dimension=0,
            normalized=True,
        )


def test_validate_vectors_accepts_valid_batch() -> None:
    metadata = EmbeddingMetadata(
        model_name="test-model",
        model_revision="v1",
        device="cpu",
        dimension=2,
        normalized=True,
    )

    validate_vectors(
        [(0.1, 0.2), (0.3, 0.4)],
        expected_count=2,
        metadata=metadata,
    )


def test_validate_vectors_rejects_wrong_dimension() -> None:
    metadata = EmbeddingMetadata(
        model_name="test-model",
        model_revision="v1",
        device="cpu",
        dimension=2,
        normalized=True,
    )

    with pytest.raises(ValueError, match="dimension"):
        validate_vectors(
            [(0.1,)],
            expected_count=1,
            metadata=metadata,
        )


def test_validate_vectors_rejects_non_finite_value() -> None:
    metadata = EmbeddingMetadata(
        model_name="test-model",
        model_revision="v1",
        device="cpu",
        dimension=2,
        normalized=True,
    )

    with pytest.raises(ValueError, match="NaN or Inf"):
        validate_vectors(
            [(0.1, float("nan"))],
            expected_count=1,
            metadata=metadata,
        )
