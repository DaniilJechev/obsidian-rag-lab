# Phase 5 — Qdrant and Retrieval Foundation

## Storage contract

PostgreSQL remains the source of truth for versioned chunks and provenance.
Qdrant stores one point per successfully embedded chunk:

```text
PostgreSQL chunks
    → ChunkRepository
    → EmbeddingProvider
    → vector validation
    → VectorSink
    → Qdrant collection
```

The application-level `EmbeddingSink` contract keeps the batch pipeline
independent of the Qdrant SDK. `QdrantVectorSink` creates a collection with an
explicit vector dimension and cosine distance, then performs durable batch
upserts with stable point IDs derived from source identity and index version.
The mutable PostgreSQL `chunk_id` remains in payload for provenance but is not
used as the deduplication key.

Collections are versioned by the configured base collection and
`chunking_version`, for example:

```text
rag_chunks__sprint9-policy-512-v2
```

The Qdrant payload contains the chunk identity, text, section provenance,
source path and character offsets needed to reconstruct retrieval results.

## Operational behavior

- Provider output is validated before persistence.
- Qdrant upsert retries are bounded and use configured backoff.
- A failed Qdrant batch becomes a partial pipeline failure; already persisted
  batches remain durable.
- `tqdm` advances after the batch upsert, so displayed progress includes both
  embedding and Qdrant persistence.
- MLflow records upsert duration, throughput, errors, point count and the raw
  float32 vector storage estimate.
- The runtime pipeline does not create or read `embeddings.json`.

## Consistency verification

`QdrantConsistencyVerifier` compares one explicit PostgreSQL
`chunking_version` with all Qdrant points in its versioned collection. It
reports:

- chunks missing from Qdrant;
- extra Qdrant points;
- payload fields that differ;
- total mismatch count.

The verification CLI emits a deterministic JSON report and records the same
counts in MLflow.

## CLI

```text
uv run rag-cli vector-store create --vector-size <model-dimension>
uv run rag-cli vector-store embed
uv run rag-cli vector-store verify
```

`rag-cli embed` remains as a compatibility alias for the embedding operation.

## Retrieval boundary

Sprint 15 will add query embeddings, dense Qdrant search, BM25 over versioned
PostgreSQL chunks and RRF fusion. Phase 5 smoke tests verify technical
correctness only; semantic quality metrics and gold questions belong to Phase 7.
