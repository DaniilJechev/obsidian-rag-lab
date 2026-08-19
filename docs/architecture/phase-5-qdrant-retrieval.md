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

Collections are versioned by the configured base collection,
`chunking_version`, embedding model, model revision and vector dimension, for
example:

```text
rag_chunks__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384
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

## Rebuild modes

The default `run-and-verify` mode creates or updates the target generation and
does not delete older collections. The explicit `--recreate` mode deletes only
that target collection before rebuilding it. The destructive mode is never
implicit.

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

Sprint 15 adds a backend-independent `RetrievedChunk` contract over three
retrieval stages:

```text
query
  → one query embedding
  → asyncio.to_thread(dense Qdrant search)
  → asyncio.to_thread(BM25 search)
  → rank-based RRF fusion
  → deterministic top-k RetrievedChunk results
```

Dense search uses Qdrant cosine/HNSW retrieval against the collection whose
model, revision, dimension and chunking version match the query provider.
BM25 uses `rank-bm25` over one explicit version of PostgreSQL chunks. The BM25
index is an in-memory process structure: PostgreSQL remains its source of truth,
and the index is rebuilt after process restart or version change.

Dense and BM25 raw scores are not added directly because their scales differ.
RRF combines their rank positions, removes duplicate stable chunk identities
and preserves dense/BM25 scores as diagnostic fields. Phase 5 smoke tests
verify technical correctness only; semantic quality metrics and gold questions
belong to Phase 7.
