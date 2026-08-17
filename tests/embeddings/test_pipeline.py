"""Unit tests for the Sprint 11 batch embedding pipeline."""

import json
import math
from pathlib import Path

import pytest

from rag_based_on_obsidian.embeddings.contracts import EmbeddingMetadata
from rag_based_on_obsidian.embeddings.pipeline import (
    BatchEmbeddingPipeline,
    EmbeddedChunk,
    JsonArtifactWriter,
    validate_embedding_batch,
)
from rag_based_on_obsidian.embeddings.settings import BatchEmbeddingConfig


class FakeProvider:
    """Deterministic provider double with controllable batch failures."""

    metadata = EmbeddingMetadata(
        model_name="fake-model",
        model_revision="v1",
        device="cpu",
        dimension=2,
        normalized=True,
    )

    def __init__(self, *, failures_before_success: int = 0) -> None:
        self.failures_before_success = failures_before_success
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[tuple[float, float]]:
        self.calls.append(texts)
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise RuntimeError("transient provider failure")
        return [(0.6, 0.8) for _ in texts]

    def embed_query(self, text: str) -> tuple[float, float]:
        del text
        return (0.6, 0.8)


def _config(
    tmp_path: Path,
    *,
    batch_size: int = 2,
    max_retries: int = 0,
) -> BatchEmbeddingConfig:
    return BatchEmbeddingConfig(
        name="test-batch",
        chunking_version="chunk-v1",
        artifact_dir=tmp_path / "artifacts",
        batch_size=batch_size,
        max_retries=max_retries,
        retry_backoff_seconds=0.0,
        show_progress=False,
    )


def _chunk(chunk_id: int, note_id: int, chunk_index: int, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "note_id": note_id,
        "chunk_index": chunk_index,
        "chunking_version": "chunk-v1",
        "text": text,
    }


def _pipeline(
    tmp_path: Path,
    provider: FakeProvider,
    *,
    batch_size: int = 2,
    max_retries: int = 0,
) -> BatchEmbeddingPipeline:
    return BatchEmbeddingPipeline(
        provider,
        _config(
            tmp_path,
            batch_size=batch_size,
            max_retries=max_retries,
        ),
        sleep_fn=lambda _seconds: None,
    )


def test_pipeline_orders_chunks_and_batches_them(tmp_path: Path) -> None:
    provider = FakeProvider()
    pipeline = _pipeline(tmp_path, provider)
    chunks = [
        _chunk(3, 2, 0, "third"),
        _chunk(2, 1, 1, "second"),
        _chunk(1, 1, 0, "first"),
    ]

    result = pipeline.run_chunks(chunks)

    assert [item.chunk_id for item in result.embeddings] == [1, 2, 3]
    assert provider.calls == [["first", "second"], ["third"]]
    assert result.batches_total == 2
    assert result.batches_succeeded == 2


def test_validate_embedding_batch_rejects_bad_vectors(tmp_path: Path) -> None:
    provider = FakeProvider()

    with pytest.raises(ValueError, match="NaN"):
        validate_embedding_batch(
            [(math.nan, 0.0)],
            provider,
            expected_count=1,
        )

    with pytest.raises(ValueError, match="non-normalized"):
        validate_embedding_batch(
            [(1.0, 1.0)],
            provider,
            expected_count=1,
        )

    with pytest.raises(ValueError, match="unexpected number"):
        validate_embedding_batch(
            [(0.6, 0.8)],
            provider,
            expected_count=2,
        )


def test_pipeline_retries_transient_batch_failure(tmp_path: Path) -> None:
    provider = FakeProvider(failures_before_success=1)
    pipeline = _pipeline(tmp_path, provider, max_retries=1)

    result = pipeline.run_chunks([_chunk(1, 1, 0, "retry me")])

    assert len(result.embeddings) == 1
    assert result.failures == ()
    assert result.attempts_total == 2
    assert result.metrics["failure_rate"] == 0.0


def test_pipeline_can_upsert_batches_without_retaining_vectors(
    tmp_path: Path,
) -> None:
    class RecordingSink:
        def __init__(self) -> None:
            self.batches: list[tuple[list[EmbeddedChunk], list[dict]]] = []

        def upsert_batch(
            self,
            embeddings: list[EmbeddedChunk],
            chunks: list[dict],
        ) -> None:
            self.batches.append((embeddings, chunks))

    provider = FakeProvider()
    pipeline = _pipeline(tmp_path, provider)
    sink = RecordingSink()
    chunks = [_chunk(1, 1, 0, "direct"), _chunk(2, 1, 1, "qdrant")]

    result = pipeline._run_batches(
        [chunks],
        sink=sink,
        retain_embeddings=False,
    )

    assert result.embeddings == ()
    assert result.embeddings_succeeded == 2
    assert [item.chunk_id for item in sink.batches[0][0]] == [1, 2]
    assert result.metrics["embeddings_succeeded"] == 2.0


def test_pipeline_records_partial_failure_and_continues(
    tmp_path: Path,
) -> None:
    class PartiallyFailingProvider(FakeProvider):
        def embed_documents(self, texts: list[str]) -> list[tuple[float, float]]:
            self.calls.append(texts)
            if "bad" in texts:
                raise RuntimeError("permanent provider failure")
            return [(0.6, 0.8) for _ in texts]

    provider = PartiallyFailingProvider()
    pipeline = _pipeline(tmp_path, provider, max_retries=1)
    chunks = [
        _chunk(1, 1, 0, "good one"),
        _chunk(2, 1, 1, "bad"),
        _chunk(3, 1, 2, "good two"),
    ]

    result = pipeline.run_chunks(chunks)

    assert [item.chunk_id for item in result.embeddings] == [3]
    assert [failure.chunk_id for failure in result.failures] == [1, 2]
    assert result.batches_total == 2
    assert result.batches_succeeded == 1
    assert result.attempts_total == 3


def test_pipeline_rerun_replaces_json_artifacts_without_duplicates(
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    pipeline = _pipeline(tmp_path, provider)
    chunks = [_chunk(1, 1, 0, "same input")]
    writer = JsonArtifactWriter()

    first = pipeline.run_chunks(chunks)
    writer.write(first, provider=provider, config=pipeline.config)
    second = pipeline.run_chunks(chunks)
    writer.write(second, provider=provider, config=pipeline.config)

    payload = json.loads(
        (pipeline.config.artifact_dir / "embeddings.json").read_text(
            encoding="utf-8"
        )
    )
    assert first.embeddings == second.embeddings
    assert len(payload) == 1
    assert payload[0]["chunk_id"] == 1
