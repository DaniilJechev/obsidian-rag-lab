"""Transformers/PyTorch implementation of the embedding provider contract."""

from collections.abc import Sequence
from typing import Any

import torch
from transformers import AutoModel, AutoTokenizer

from rag_based_on_obsidian.embeddings.contracts import (
    EmbeddingMetadata,
    EmbeddingProvider,
    EmbeddingVector,
    validate_vectors,
)
from rag_based_on_obsidian.embeddings.settings import EmbeddingModelConfig


class TransformersEmbeddingProvider(EmbeddingProvider):
    """Run a Transformer encoder and return normalized CPU vectors."""

    def __init__(
        self,
        config: EmbeddingModelConfig,
        *,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        """Load the tokenizer/model or accept injected test doubles."""
        if (tokenizer is None) != (model is None):
            raise ValueError("tokenizer and model must be provided together")
        self._config = config
        self._device = torch.device(config.device)
        self._tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            config.model_name,
            revision=config.model_revision,
        )
        self._model = model or AutoModel.from_pretrained(
            config.model_name,
            revision=config.model_revision,
        )
        self._model.to(self._device)
        self._model.eval()
        self._metadata = EmbeddingMetadata(
            model_name=config.model_name,
            model_revision=config.model_revision,
            device=str(self._device),
            dimension=self._embedding_dimension(),
            normalized=config.normalized,
        )

    @property
    def metadata(self) -> EmbeddingMetadata:
        """Return model identity and vector shape."""
        return self._metadata

    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[EmbeddingVector]:
        """Embed documents in order using the configured passage prefix."""
        return self._embed_texts(
            texts,
            prefix=self._config.document_prefix,
        )

    def embed_query(self, text: str) -> EmbeddingVector:
        """Embed one query in the same space as document vectors."""
        vectors = self._embed_texts(
            [text],
            prefix=self._config.query_prefix,
        )
        return vectors[0]

    def _embed_texts(
        self,
        texts: Sequence[str],
        *,
        prefix: str,
    ) -> list[EmbeddingVector]:
        if any(not text.strip() for text in texts):
            raise ValueError("embedding texts must not be empty")
        vectors: list[EmbeddingVector] = []
        for start in range(0, len(texts), self._config.batch_size):
            batch_texts = [
                f"{prefix}{text}"
                for text in texts[start : start + self._config.batch_size]
            ]
            encoded = self._tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self._config.max_length,
                return_tensors="pt",
            )
            encoded = {
                key: value.to(self._device)
                for key, value in encoded.items()
            }
            with torch.inference_mode():
                outputs = self._model(**encoded)
                pooled = self._mean_pool(
                    outputs.last_hidden_state,
                    encoded["attention_mask"],
                )
                if self._config.normalized:
                    pooled = torch.nn.functional.normalize(
                        pooled,
                        p=2,
                        dim=1,
                    )
            vectors.extend(
                tuple(float(value) for value in row)
                for row in pooled.cpu().tolist()
            )
        validate_vectors(
            vectors,
            expected_count=len(texts),
            metadata=self.metadata,
        )
        return vectors

    @staticmethod
    def _mean_pool(
        token_embeddings: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Average token states while ignoring padding tokens."""
        mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
        masked_embeddings = token_embeddings * mask
        token_count = mask.sum(dim=1).clamp(min=1e-9)
        return masked_embeddings.sum(dim=1) / token_count

    def _embedding_dimension(self) -> int:
        hidden_size = getattr(self._model.config, "hidden_size", None)
        if hidden_size is not None:
            return int(hidden_size)
        return int(self._model.get_input_embeddings().embedding_dim)
