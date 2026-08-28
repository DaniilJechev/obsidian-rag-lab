"""Unit tests for cosine similarity helper."""

import pytest

from rag_based_on_obsidian.cache.similarity import cosine_similarity


def test_cosine_identical_vectors() -> None:
    left = (1.0, 0.0, 0.0)
    assert cosine_similarity(left, left) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors() -> None:
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)


def test_cosine_dimension_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        cosine_similarity((1.0, 0.0), (1.0,))


def test_cosine_empty_vectors() -> None:
    assert cosine_similarity((), ()) == 0.0
