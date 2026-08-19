# Sprint 16 — pgvector Dense Experiment

> Статус: `planned`
>
> Ветка: `sprint/16-pgvector-dense-experiment`
>
> Связанная фаза roadmap: `Фаза 6`
>
> Backlog: `PGV-001`
>
> Closeout: implementation **не merge'ится в `main`**. Qdrant остаётся единственным
> retrieval path на `main`. Ветка нужна, чтобы руками увидеть SQL-ANN.

## Sprint Goal

На отдельной ветке поднять dense retrieval через PostgreSQL + pgvector на тех
же versioned chunks и том же `EmbeddingProvider`, что уже лежат в Qdrant, и
зафиксировать наблюдаемые отличия от Qdrant dense — без замены стека.

## Why

Roadmap Phase 6 требует comparison path: Qdrant — deep path, pgvector — учебное
сравнение. Semantic quality (nDCG/MRR) ещё нельзя мерить честно: gold set —
Phase 7. Этот спринт закрывает операционное понимание: тип `vector`, индекс,
SQL `ORDER BY embedding <=> query`, одна БД вместо отдельного ANN-сервиса.

pgvector не умеет BM25. Lexical/hybrid остаются в Qdrant (`dense` + sparse
`bm25` на одном point).

## Scope

- [ ] Включить `pgvector` в Postgres на экспериментальной ветке (образ/extension),
  не ломая текущий `postgres_data` на `main`.
- [ ] Добавить таблицу/колонку `vector(384)` с versioned identity тех же chunks.
- [ ] Upsert тех же embeddings, что используются для Qdrant dense.
- [ ] Dense search, который возвращает существующий `RetrievedChunk`.
- [ ] CLI вроде `rag-cli search pgvector` для synthetic smoke.
- [ ] Записать 3–5 наблюдаемых отличий vs `rag-cli search dense` (Qdrant).

## Out of Scope

- Merge implementation-ветки в `main`.
- Смена default retrieval: hybrid/dense остаются на Qdrant.
- BM25, `tsvector` и hybrid в PostgreSQL.
- LangChain retriever adapters.
- Gold questions, nDCG/MRR, RAGAS — Phase 7.
- FastAPI, OpenRouter, смена embedding-модели (`EMB-003`).
- Query classifier / XGBoost — Phase 11.

## Expected Artifacts

Артефакты живут на `sprint/16-pgvector-dense-experiment`, не на `main`:

- Docker/Postgres с расширением `vector` (отдельный image или profile).
- Alembic migration: `vector(384)` + index + versioned chunk identity.
- pgvector sink и dense retriever поверх `RetrievedChunk`.
- CLI dense search через pgvector.
- Короткая заметка в этом sprint-документе: что увидели vs Qdrant.

## Acceptance Criteria

- [ ] Локально: `CREATE EXTENSION vector` воспроизводится на экспериментальном Postgres.
- [ ] pgvector хранит те же `chunk_id` / chunking version / model / dimension,
  что Qdrant payload.
- [ ] Dense search возвращает `RetrievedChunk` с явным pgvector retrieval method.
- [ ] Повторный upsert идемпотентен.
- [ ] Записаны наблюдаемые отличия vs Qdrant dense (не ranking quality).
- [ ] Код и default CLI на `main` не меняются этим спринтом.

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Наблюдения записаны в этот sprint-документ.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Implementation не влита в `main`.
- [ ] Пользователь подтвердил, что эксперимент достаточно увидели.

CI, PR и merge в `main` сознательно не являются Definition of Done этого спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-19 | Sprint planned; Qdrant stays on `main`; pgvector is branch-only | Planning docs committed to `main` |

## Validation Evidence

### Commands

```text
```

### Test and Lint Results

- Tests: не записаны
- Lint: не записаны
- CI: не требуется для closeout этого спринта

### Metrics

| Metric | Value | Context |
|---|---:|---|
|  |  |  |

## Review

### Completed

- Planning: pgvector — comparison-only, без merge в `main`.

### Not Completed

- Implementation на `sprint/16-pgvector-dense-experiment`.

### Changed Decisions

- Phase 6 comparison не требует замены Qdrant.
- Quality metrics не входят в Sprint 16.

### Technical Debt

-

## Retrospective

### What Went Well

-

### What Was Difficult

-

### What We Will Change

-

### Backlog Updates

- Добавить: `PGV-001` (этот спринт).
- Перенести: LangChain adapters и nDCG comparison — не в этот спринт.
- Изменить приоритет:

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Implementation-ветка не merge'ится в `main`.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:**
