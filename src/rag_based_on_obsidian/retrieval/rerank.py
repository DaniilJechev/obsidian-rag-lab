"""Cross-encoder rerank: score (query, chunk) pairs and keep top-K.

Uses Hugging Face ``AutoModelForSequenceClassification`` (BGE reranker).
Weights live in the HF hub cache after the first download; loads show tqdm.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Protocol

import torch
from tqdm import tqdm
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from rag_based_on_obsidian.retrieval.contracts import RetrievedChunk
from rag_based_on_obsidian.retrieval.rerank_settings import RerankConfig

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    """Score and reorder retrieved chunks for one query."""

    def ensure_loaded(self) -> None:
        """Load model weights if not already in memory."""

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        top_k: int,
    ) -> list[RetrievedChunk]:
        """Return up to ``top_k`` chunks ordered by cross-encoder score."""


class IdentityReranker:
    """Passthrough used when rerank is disabled (still a graph node)."""

    def ensure_loaded(self) -> None:
        return None

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        top_k: int,
    ) -> list[RetrievedChunk]:
        _ = query
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        trimmed = list(chunks[:top_k])
        return [
            replace(chunk, rank=index)
            for index, chunk in enumerate(trimmed, start=1)
        ]


class CrossEncoderReranker:
    """Local HF cross-encoder (default ``BAAI/bge-reranker-v2-m3``)."""

    def __init__(self, config: RerankConfig) -> None:
        self._config = config
        self._tokenizer: object | None = None
        self._model: object | None = None
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._fp16_active = bool(
            config.use_fp16 and self._device.type == "cuda"
        )

    @property
    def config(self) -> RerankConfig:
        return self._config

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def ensure_loaded(self) -> None:
        if self.is_loaded:
            return
        model_id = self._config.model_name
        revision = self._config.model_revision
        kwargs: dict[str, object] = {}
        if revision:
            kwargs["revision"] = revision
        logger.info(
            "loading cross-encoder model=%s revision=%s device=%s fp16=%s",
            model_id,
            revision,
            self._device,
            self._fp16_active,
        )
        with tqdm(total=3, desc=f"Loading {model_id}", unit="step") as progress:
            progress.set_postfix_str("tokenizer")
            self._tokenizer = AutoTokenizer.from_pretrained(model_id, **kwargs)
            progress.update(1)
            progress.set_postfix_str("weights")
            model = AutoModelForSequenceClassification.from_pretrained(
                model_id,
                **kwargs,
            )
            progress.update(1)
            progress.set_postfix_str(str(self._device))
            model.eval()
            model.to(self._device)
            if self._fp16_active:
                model.half()
            self._model = model
            progress.update(1)
        logger.info("cross-encoder ready model=%s", model_id)

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        *,
        top_k: int,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if not chunks:
            return []
        self.ensure_loaded()
        assert self._tokenizer is not None and self._model is not None
        texts = [chunk.text for chunk in chunks]
        scores = self._score_pairs(query, texts)
        ranked_indexes = sorted(
            range(len(chunks)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]
        result: list[RetrievedChunk] = []
        for rank, index in enumerate(ranked_indexes, start=1):
            chunk = chunks[index]
            meta = dict(chunk.metadata)
            meta["rerank_score"] = float(scores[index])
            result.append(
                replace(
                    chunk,
                    rank=rank,
                    metadata=meta,
                    rerank_score=float(scores[index]),
                )
            )
        return result

    def _score_pairs(self, query: str, passages: list[str]) -> list[float]:
        assert self._tokenizer is not None and self._model is not None
        batch_size = self._config.batch_size
        all_scores: list[float] = []
        batch_starts = range(0, len(passages), batch_size)
        for start in tqdm(
            batch_starts,
            desc="CE scoring",
            unit="batch",
            total=(len(passages) + batch_size - 1) // batch_size,
        ):
            batch = passages[start : start + batch_size]
            pairs = [[query, text] for text in batch]
            encoded = self._tokenizer(
                pairs,
                padding=True,
                truncation=True,
                max_length=self._config.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self._device) for key, value in encoded.items()}
            with torch.no_grad():
                logits = self._model(**encoded, return_dict=True).logits
                if logits.ndim == 2 and logits.shape[-1] == 1:
                    batch_scores = logits.view(-1)
                else:
                    batch_scores = logits.view(-1)
                all_scores.extend(batch_scores.float().cpu().tolist())
        return all_scores


def build_reranker(config: RerankConfig) -> Reranker:
    """Return identity when disabled; otherwise the HF cross-encoder."""
    if not config.enabled:
        return IdentityReranker()
    return CrossEncoderReranker(config)
