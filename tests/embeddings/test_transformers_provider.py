"""Tests for the Transformers embedding provider."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from rag_based_on_obsidian.embeddings.settings import (
    EmbeddingModelConfig,
    load_embedding_model_config,
)
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)


class FakeTokenizer:
    """Small deterministic tokenizer double for CPU unit tests."""

    def __call__(
        self,
        texts: list[str],
        *,
        padding: bool,
        truncation: bool,
        max_length: int,
        return_tensors: str,
    ) -> dict[str, torch.Tensor]:
        del padding, truncation, max_length, return_tensors
        lengths = [len(text.split()) for text in texts]
        max_tokens = max(lengths)
        input_ids = [
            [1] * length + [0] * (max_tokens - length)
            for length in lengths
        ]
        attention_mask = [
            [1] * length + [0] * (max_tokens - length)
            for length in lengths
        ]
        return {
            "input_ids": torch.tensor(input_ids),
            "attention_mask": torch.tensor(attention_mask),
        }


class FakeModel:
    """Small model double exposing the Transformer output contract."""

    config = SimpleNamespace(hidden_size=2)

    def to(self, device: torch.device) -> "FakeModel":
        del device
        return self

    def eval(self) -> "FakeModel":
        return self

    def __call__(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> SimpleNamespace:
        del attention_mask
        values = input_ids.to(dtype=torch.float32)
        hidden_states = torch.stack((values, values + 1), dim=-1)
        return SimpleNamespace(last_hidden_state=hidden_states)


def _config() -> EmbeddingModelConfig:
    return EmbeddingModelConfig(
        name="test-model",
        model_name="test-model",
        model_revision="v1",
        device="cpu",
        max_length=16,
        batch_size=2,
        normalized=True,
        document_prefix="passage: ",
        query_prefix="query: ",
    )


def test_provider_embeds_documents_and_query_with_normalization() -> None:
    provider = TransformersEmbeddingProvider(
        _config(),
        tokenizer=FakeTokenizer(),
        model=FakeModel(),
    )

    vectors = provider.embed_documents(["one two", "three"])
    query_vector = provider.embed_query("question")

    assert len(vectors) == 2
    assert len(vectors[0]) == 2
    assert len(query_vector) == 2
    assert sum(value * value for value in vectors[0]) == pytest.approx(1.0)
    assert provider.metadata.dimension == 2
    assert provider.metadata.device == "cpu"


def test_model_config_loads_from_yaml() -> None:
    config_path = Path("configs/embeddings/embedder_model_config_e5_small.yaml")

    config = load_embedding_model_config(config_path)

    assert config.model_name == "intfloat/multilingual-e5-small"
    assert config.device == "cpu"
    assert config.normalized is True


@pytest.mark.manual
def test_real_cpu_embedding_smoke() -> None:
    """Download the configured model and run a real CPU inference smoke test."""
    config = load_embedding_model_config(
        Path("configs/embeddings/embedder_model_config_e5_small.yaml")
    )
    provider = TransformersEmbeddingProvider(config)

    vectors = provider.embed_documents(
        [
            "RAG использует retrieval и generation вместе.",
            "Embeddings превращают текст в числовые vectors.",
        ]
    )

    assert len(vectors) == 2
    assert all(len(vector) == provider.metadata.dimension for vector in vectors)
    assert all(
        sum(value * value for value in vector) == pytest.approx(1.0, abs=1e-5)
        for vector in vectors
    )
