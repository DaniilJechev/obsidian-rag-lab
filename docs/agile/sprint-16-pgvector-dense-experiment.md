# Sprint 16 — pgvector Dense Experiment

> Статус: `completed`
>
> Ветка: `sprint/16-pgvector-dense-experiment` (`bd39d20`)
>
> Связанная фаза roadmap: `Фаза 6`
>
> Backlog: `PGV-001`
>
> Closeout: implementation **не влита в `main`**. Qdrant остаётся единственным
> retrieval path на `main`. Ветка оставлена как архив SQL-ANN эксперимента.

## Sprint Goal

На отдельной ветке поднять dense retrieval через PostgreSQL + pgvector на тех
же versioned chunks и том же `EmbeddingProvider`, что уже лежат в Qdrant, и
зафиксировать наблюдаемые отличия от Qdrant dense — без замены стека.

## Why

Roadmap Phase 6 требует comparison path: Qdrant — deep path, pgvector — учебное
сравнение. Semantic quality (nDCG/MRR) ещё нельзя мерить честно: gold set —
Phase 7. Этот спринт закрывает операционное понимание: тип `vector`, индекс,
SQL `ORDER BY embedding <=> query`, отдельный ANN-инстанс рядом с Qdrant.

pgvector не умеет BM25. Lexical/hybrid остаются в Qdrant (`dense` + sparse
`bm25` на одном point).

## Scope

- [x] Включить `pgvector` в Postgres на экспериментальной ветке (образ/extension),
  не ломая текущий `postgres_data` на `main`.
- [x] Добавить таблицу/колонку `vector(384)` с versioned identity тех же chunks.
- [x] Upsert тех же embeddings, что используются для Qdrant dense.
- [x] Dense search, который возвращает существующий `RetrievedChunk`.
- [x] CLI вроде `rag-cli search pgvector` для synthetic smoke.
- [x] Записать 3–5 наблюдаемых отличий vs `rag-cli search dense` (Qdrant).

## Out of Scope

- Merge implementation-ветки в `main`.
- Смена default retrieval: hybrid/dense остаются на Qdrant.
- BM25, `tsvector` и hybrid в PostgreSQL.
- LangChain retriever adapters.
- Gold questions, nDCG/MRR, RAGAS — Phase 7.
- FastAPI, OpenRouter, смена embedding-модели (`EMB-003`).
- Query classifier / XGBoost — Phase 11.

## Expected Artifacts

Implementation живёт только на `sprint/16-pgvector-dense-experiment`, не на
`main`:

- Docker profile `pgvector` (`pgvector/pgvector:pg16` on port 5433).
- Table `chunk_embeddings_pgvector` created by `PgvectorVectorSink.ensure_schema`
  (`CREATE EXTENSION vector` + HNSW `vector_cosine_ops`). Not added to the main
  Alembic chain, so source Postgres `:5432` is not migrated.
- pgvector sink и dense retriever поверх `RetrievedChunk`.
- CLI: `vector-store create-pgvector`, `vector-store upsert-pgvector`,
  `search pgvector`.
- Наблюдения vs Qdrant dense — в этом документе.

## Observed differences vs Qdrant dense

Live smoke: один и тот же synthetic query, `top_k=5`, тот же
`index_generation` / collection
`rag_chunks_dense_sparse__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384`.
Top-k `point_key` и ranking совпали с `rag-cli search dense`. Это не nDCG и не
утверждение semantic quality.

1. **Протокол поиска.** Qdrant: client `query_points` по named vector `dense`.
   pgvector: SQL `ORDER BY embedding <=> query LIMIT k`; HNSW задаётся DDL
   `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`, не флагом search.
2. **Что индексируется.** pgvector — только dense. BM25 и hybrid остаются в
   Qdrant (два named vector на одной точке + Python RRF).
3. **Где лежат данные.** Source chunks — Postgres `:5432`. Экспериментальный
   dense index — отдельный Postgres `:5433` (свой volume). Qdrant — `:6333`.
   Это не колонка в таблице `chunks`.
4. **Identity.** Тот же `stable_point_key` и `versioned_collection_name`, payload
   денормализован в строку pgvector (текст хита без join на `:5432` при search).
5. **Latency CLI.** Узкое место — загрузка `multilingual-e5-small` на каждый
   `rag-cli` (~6.7 с на `search dense`). `connect_qdrant` ~0.04 с. Постоянный
   TCP из одноразового CLI не лечит cold start; тёплый `EmbeddingProvider` —
   FastAPI (Phase 8).

## Acceptance Criteria

- [x] Локально: `CREATE EXTENSION vector` воспроизводится на экспериментальном
  Postgres `:5433`.
- [x] pgvector хранит те же `chunk_id` / chunking version / model / dimension,
  что Qdrant payload (тот же generation и `point_key`).
- [x] Dense search возвращает `RetrievedChunk` с явным pgvector retrieval method.
- [x] Повторный upsert идемпотентен.
- [x] Записаны наблюдаемые отличия vs Qdrant dense (не ranking quality).
- [x] Код и default CLI на `main` не меняются этим спринтом.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Наблюдения записаны в этот sprint-документ.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Implementation не влита в `main`.
- [x] Пользователь подтвердил, что эксперимент достаточно увидели; дальше с
  pgvector не работает.

CI, PR и merge implementation в `main` сознательно не являются Definition of
Done этого спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-19 | Sprint planned; Qdrant stays on `main`; pgvector is branch-only | Planning docs committed to `main` (`a666f8d`) |
| 2026-08-20 | Implemented experimental pgvector storage and dense search | Commit `bd39d20` on `sprint/16-pgvector-dense-experiment`; pushed, not merged |
| 2026-08-20 | Live `upsert-pgvector` + `search pgvector` vs `search dense` | Top-k совпал; bottleneck = embedding model load |
| 2026-08-20 | Docs closeout on `main`; implementation branch kept | `PGV-001` done; Qdrant remains default |

## Validation Evidence

### Commands

На ветке `sprint/16-pgvector-dense-experiment`, не на `main`:

```text
docker compose --env-file .env -f docker/compose.yml --profile pgvector up -d postgres-pgvector
uv run rag-cli vector-store create-pgvector
uv run rag-cli vector-store upsert-pgvector
uv run rag-cli search pgvector --query "..."
uv run rag-cli search dense --query "..."
```

### Test and Lint Results

Записано с implementation-ветки (не прогонялись повторно на docs-closeout `main`):

- Tests: `PASS — uv run pytest -q` (`118 passed, 1 skipped, 18 deselected`)
- Lint: `PASS — uv run ruff check .`
- Live smoke: `PASS` — top-k `search pgvector` совпал с `search dense`; no
  semantic-quality claim
- CI / merge to `main`: не требуется

### Metrics

| Metric | Value | Context |
|---|---:|---|
| `search dense` `load_embedding_model` | ~6.73 s | CLI cold start, e5-small |
| `search dense` `connect_qdrant` | ~0.04 s | not the bottleneck |
| Live top-k vs Qdrant dense | matched | synthetic query, `top_k=5` |

## Review

### Completed

- Отдельный pgvector Postgres `:5433`, sink, HNSW, `search pgvector`.
- Live сравнение с Qdrant dense: одинаковый top-k.
- Qdrant остаётся default на `main`; ветка не merge.

### Not Completed

- LangChain retriever adapters — out of scope, не переносим.
- nDCG/MRR на одном gold-сете — Phase 7, не этот спринт.
- Дальнейшая работа с pgvector не планируется.

### Changed Decisions

- Phase 6 comparison закрыт операционным smoke на ветке, без замены Qdrant.
- Quality metrics не входят в Sprint 16.
- Implementation-ветка сохраняется как архив, не удаляется и не вливается.

### Technical Debt

- Код pgvector есть только на `sprint/16-pgvector-dense-experiment`.
- CLI cold start модели остаётся; лечится serving-слоем (Phase 8), не pgvector.

## Retrospective

### What Went Well

- Два Postgres (source vs experimental) не сломали `:5432` / Alembic.
- Одна identity с Qdrant сделала live top-k сравнимым без gold-набора.

### What Was Difficult

- `register_vector` до `CREATE EXTENSION` → `vector type not found`.
- Чтение размерности как `atttypmod - 4` (формула varchar) давало ложные 380
  вместо 384; нужен `format_type`.

### What We Will Change

- Не тащить SQL-ANN в `main`, пока Qdrant закрывает hybrid.
- Не оптимизировать CLI TCP: мерить стадии, прежде чем кешировать коннекты.

### Backlog Updates

- `PGV-001` → `done`.
- Не добавлять pgvector follow-up.
- Дальше по roadmap: Phase 7 gold eval или Phase 8 FastAPI — решение после
  closeout.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Implementation-ветка не merge'ится в `main`.
- [x] Backlog обновлён.
- [x] Следующий sprint не стартован автоматически; обсуждается после closeout.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-20`
