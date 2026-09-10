# RAG Based on Obsidian

RAG API over an Obsidian vault (allowlisted `DLS1` / `DLS2` notes). Local stack:
PostgreSQL, Qdrant, Redis, FastAPI (`api` with a warm E5 embedder). Generation
uses OpenRouter.

## Requirements

- Python **3.12**
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop (Compose)
- Obsidian vault path with direct children `DLS1` and `DLS2`
- OpenRouter API key (only for `/generate`)

## Setup

```bash
cp .env.example .env
```

Edit `.env` (required):

| Variable | Purpose |
|----------|---------|
| `OBSIDIAN_VAULT_ROOT` | Host path to `…/ML_NLP` (use forward slashes, e.g. `C:/Users/…/ML_NLP`) |
| `ALLOWED_CORPUS_DIRECTORIES` | Default `DLS1,DLS2` |
| `POSTGRES_PASSWORD` | Non-empty password for local Postgres |
| `OPENROUTER_API_KEY` | Required for `POST /generate` |

Install the package and apply migrations:

```bash
uv sync
uv run alembic upgrade head
```

Compose interpolates `${OBSIDIAN_VAULT_ROOT}` from `--env-file .env`. Always pass
that flag.

## Start the stack

```bash
docker compose --env-file .env -f docker/compose.yml up -d --build
docker compose --env-file .env -f docker/compose.yml ps
```

Services:

| Service | Port | Role |
|---------|------|------|
| `postgres` | `5432` | Metadata, chunks, ingest state, query logs |
| `qdrant` | `6333` | Dense + sparse vectors |
| `redis` | `6379` | Semantic cache store |
| `api` | `8000` | FastAPI (E5 loads on startup; first boot can take a few minutes) |

Health:

```bash
curl http://127.0.0.1:8000/health
```

Expect `"status":"ok"` and `"model_loaded":true` when the embedder is ready.

Stop:

```bash
docker compose --env-file .env -f docker/compose.yml down
```

## Index the corpus

With Postgres + Qdrant healthy and `.env` configured, either:

**HTTP (from a running `api`):**

```bash
curl -X POST http://127.0.0.1:8000/ingest
curl http://127.0.0.1:8000/ingest/current
```

`POST /ingest` returns a `run_id` and continues in the background. A second
ingest while one is running returns `409`.

**CLI (host):**

```bash
uv run rag-cli chunk --help
uv run rag-cli upsert-dense-sparse --help
```

Vault files are mounted read-only into `api` at `/vault`. Do not modify vault
contents from the application.

## HTTP API

Base URL: `http://127.0.0.1:8000`

### `GET /health`

Process liveness, embedder loaded, Qdrant/Postgres reachability, pinned models.

### `POST /search`

Hybrid (default), dense, or BM25 retrieval.

```bash
curl -X POST http://127.0.0.1:8000/search ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"What is RoPE?\",\"method\":\"hybrid\",\"top_k\":5}"
```

Body fields: `query` (required), `method` (`hybrid` \| `dense` \| `bm25`),
`top_k` (optional). Each `/search` is written to Postgres `query_logs`.

### `POST /generate`

Retrieve → pack context → OpenRouter LLM → answer with citations (LangGraph).

```bash
curl -X POST http://127.0.0.1:8000/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"What is RoPE?\",\"method\":\"hybrid\",\"top_k\":5}"
```

Optional overrides (no container rebuild):

- `model` — OpenRouter model id
- `enable_cache` — override Redis semantic cache for this request
- `max_context_tokens` — override packing budget (default **1200** in
  `configs/llm/openrouter.yaml`)

Response includes `answer`, `citations`, `contexts`, `refused`, usage/latency,
and optional cache/graph fields. Missing/invalid OpenRouter key → `503` on
generate; `/search` and `/ingest` remain available.

### Ingest

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/ingest` | Start background reindex; returns `run_id` |
| `GET` | `/ingest/current` | Latest ingest run |
| `GET` | `/ingest/{run_id}` | Status for one run |

## CLI (`rag-cli`)

```bash
uv run rag-cli --help
uv run rag-cli search hybrid --query "What is RoPE?"
uv run rag-cli eval --help
uv run rag-cli ragas --help
```

| Command | Purpose |
|---------|---------|
| `chunk` | Chunk materialization into PostgreSQL |
| `upsert-dense-sparse` | Embed and upsert dense + BM25 into Qdrant |
| `vector-store` | Create / verify Qdrant collections |
| `search` | Dense / BM25 / hybrid search from the host |
| `eval` | Retrieval / cache / token-budget eval runners |
| `ragas` | Score `/generate` answers |

Host CLI uses `.env` and talks to services on localhost. Prefer HTTP `/search`
on a warm `api` process so E5 is not reloaded on every call.

## Defaults (current)

| Setting | Default | Config |
|---------|---------|--------|
| Retrieval | hybrid | `configs/retrieval/retrieval.yaml` |
| Rerank (cross-encoder) | off | `configs/retrieval/retrieval.yaml` → `rerank.enabled` |
| Semantic cache | off | `configs/cache/cache.yaml` → `enabled` |
| Generate model | `openai/gpt-4o-mini` | `configs/llm/openrouter.yaml` |
| Context budget | `1200` tokens | `configs/llm/openrouter.yaml` → `max_context_tokens` |

## Layout

```text
src/        application code
tests/      pytest suite
configs/    YAML configs
docker/     Compose + Dockerfiles
alembic/    DB migrations
docs/       architecture and sprint notes
```

## Tests

```bash
uv run ruff check .
uv run pytest -q
```
