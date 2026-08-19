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

`QdrantVectorSink` creates one versioned collection with two named vector
slots on the same point: `dense` (cosine, model dimension) and `bm25`
(sparse, `modifier=IDF`). Upserts write both the dense embedding and a
`Document(text=..., model="Qdrant/bm25")` inference input. The mutable
PostgreSQL `chunk_id` remains in payload for provenance but is not used as
the deduplication key. Legacy unnamed dense collections are rejected; rebuild
them with `--recreate` so dense and BM25 share one point.

Collections are versioned by the configured base collection,
`chunking_version`, embedding model, model revision and vector dimension, for
example:

```text
rag_chunks_dense_sparse__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384
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
uv run rag-cli vector-store upsert-dense-sparse
uv run rag-cli vector-store verify
```

`rag-cli upsert-dense-sparse` is a shortcut for the same ingest: dense
embeddings plus BM25 sparse vectors on one Qdrant point.

## Retrieval boundary

Sprint 15 adds a backend-independent `RetrievedChunk` contract over three
retrieval stages:

```text
query
  → one query embedding
  → asyncio.to_thread(dense Qdrant search using="dense")
  → asyncio.to_thread(sparse Qdrant BM25 search using="bm25")
  → rank-based Python RRF fusion
  → deterministic top-k RetrievedChunk results
```

Dense search uses Qdrant cosine/HNSW retrieval against the `dense` named
vector in the collection whose model, revision, dimension and chunking
version match the query provider. BM25 uses Qdrant's built-in sparse index
(`Qdrant/bm25`, IDF modifier, `avg_len=191.0` from Sprint 9 mean token
length) on the same points. PostgreSQL remains the source of truth for
chunks; it is no longer scanned at query time to build an in-memory
`rank-bm25` index. `rank-bm25` remains a leftover dependency until it is
explicitly removed.

Dense and BM25 raw scores are not added directly because their scales differ.
RRF combines their rank positions, removes duplicate stable chunk identities
and preserves dense/BM25 scores as diagnostic fields. Phase 5 smoke tests
verify technical correctness only; semantic quality metrics and gold questions
belong to Phase 7.
