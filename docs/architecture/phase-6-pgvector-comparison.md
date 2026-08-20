# Phase 6 — pgvector Comparison (branch-only)

Qdrant remains the production retrieval path on `main`. This document describes
the experimental dense store that lives only on
`sprint/16-pgvector-dense-experiment`.

## Why a second Postgres

The running `postgres:16` volume (`postgres_data`) must not gain a pgvector
extension or a changed image. Compose profile `pgvector` starts
`pgvector/pgvector:pg16` on port `5433` with volume `postgres_pgvector_data`.

```text
source Postgres :5432  →  chunks (source of truth)
experimental Postgres :5433  →  chunk_embeddings_pgvector (dense only)
Qdrant :6333  →  named vectors dense + bm25 (unchanged)
```

## Storage contract

`PgvectorVectorSink` implements the same `EmbeddingSink` as Qdrant, but writes
only the dense embedding. Identity uses `stable_point_key` so a row can be
compared to a Qdrant point. `index_generation` reuses
`versioned_collection_name(...)`.

Schema is created at sink connect time (`CREATE EXTENSION vector` on the same
connection *before* `register_vector`, then table + HNSW `vector_cosine_ops`).
The Python adapter looks up the `vector` type in the catalog, so registering
before the extension exists fails with `vector type not found`. This DDL is
not part of the main Alembic chain, so `alembic upgrade` against `:5432`
cannot break the source database.

## CLI

```text
docker compose --env-file .env -f docker/compose.yml --profile pgvector up -d postgres-pgvector
uv run rag-cli vector-store create-pgvector
uv run rag-cli vector-store upsert-pgvector
uv run rag-cli search pgvector --query "..."
```

`search dense` / `search hybrid` still talk to Qdrant.

## What this is not

pgvector is not BM25. Hybrid fusion stays in Qdrant. This path is not merged to
`main`.
