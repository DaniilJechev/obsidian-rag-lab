# Sprint 15 — Dense, BM25 and Retrieval Contract

> Статус: `planned`
>
> Ветка: `sprint/15-retrieval-foundation`
>
> Связанная фаза roadmap: `Фаза 5`
>
> Backlog: `RET-002`

## Sprint Goal

Создать технический retrieval foundation, который по synthetic query возвращает
top-k chunks через dense Qdrant search, BM25 lexical search и RRF fusion без
claims о semantic quality.

## Why

После Sprint 14 vectors будут храниться в Qdrant, но система ещё не будет уметь
извлекать chunks. Sprint 15 вводит стабильный retrieval contract и CLI для
проверки dense и hybrid путей. Полноценная оценка качества останется в Phase 7,
а генерация ответов через LLM — в Phase 9.

## Scope

- [ ] Создать `RetrievedChunk` contract с `chunk_id`, text, scores, metadata,
  retrieval method и version fields.
- [ ] Реализовать query embedding через тот же versioned
  `EmbeddingProvider`, что используется для document vectors.
- [ ] Реализовать dense Qdrant search с `top_k` и metadata filters.
- [ ] Создать `LexicalIndex` contract и первую реализацию на `rank_bm25` из
  explicit versioned PostgreSQL chunks.
- [ ] Реализовать BM25 lexical search с теми же `chunk_id` и metadata.
- [ ] Реализовать RRF fusion dense и BM25 результатов с устранением дублей.
- [ ] Добавить CLI для synthetic dense и hybrid search.
- [ ] Добавить deterministic retrieval smoke tests и понятный console output.
- [ ] Зафиксировать Phase 5 retrieval architecture и границы до Phase 7/9.

## Out of Scope

- User-facing API, sessions и production query service.
- Gold questions, human relevance labels, RAGAS, MRR, nDCG и semantic
  evaluation — Phase 7.
- OpenRouter, LLM generation и answer evaluation — Phase 9.
- Выбор лучшей embedding-модели — deferred до evaluation-ready этапа.
- Reranking, query classification и LangGraph — более поздние фазы.
- PostgreSQL + pgvector comparison — Phase 6.

## Expected Artifacts

- `src/rag_based_on_obsidian/retrieval/` — retrieval contracts, dense search,
  BM25 index и RRF fusion.
- `src/rag_based_on_obsidian/cli_rag.py` — dense/hybrid search commands.
- `configs/retrieval/` — `top_k`, filters, BM25 и RRF configuration.
- `tests/retrieval/` — contract, dense, BM25, RRF, filter и smoke tests.
- `docs/architecture/phase-5-qdrant-retrieval.md` — retrieval data flow and
  contracts.
- MLflow or console evidence for synthetic smoke runs, latency и failures.

## Acceptance Criteria

- [ ] Query embedding совместим с dimension и model version collection.
- [ ] Dense search возвращает deterministic top-k results с payload metadata.
- [ ] Metadata filters ограничивают результаты ожидаемым образом.
- [ ] BM25 находит chunks по exact terms и возвращает стабильные `chunk_id`.
- [ ] RRF объединяет dense и BM25 без duplicate chunks.
- [ ] `RetrievedChunk` скрывает backend-specific детали Qdrant и BM25.
- [ ] CLI выводит synthetic dense/hybrid top-k results с scores и provenance.
- [ ] Smoke tests подтверждают техническую корректность, но не semantic quality.

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Documentation/configuration обновлены.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| planned | Sprint created | Implementation not started |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run rag-cli search dense --query "synthetic retrieval query"
uv run rag-cli search hybrid --query "synthetic retrieval query"
```

### Test and Lint Results

- Tests: `NOT VERIFIED — sprint not started`
- Lint: `NOT VERIFIED — sprint not started`
- Retrieval smoke: `NOT VERIFIED — sprint not started`
- CI: `NOT VERIFIED — implementation not started`

### Metrics

Будут измеряться после реализации: query embedding latency, dense search
latency, BM25 latency, RRF latency, top-k result count и retrieval errors.

## Review

### Completed

- Retrieval scope согласован как technical smoke foundation без evaluation.

### Not Completed

- Dense search, BM25, RRF и retrieval contracts ещё не реализованы.

### Changed Decisions

- Synthetic queries используются только для проверки pipeline correctness, а не
  для выбора embedding-модели или оценки retrieval quality.

### Technical Debt

- BM25 index пока строится из PostgreSQL chunks; его persistent/refresh strategy
  потребует отдельного operational hardening после первого baseline.

## Retrospective

Будет заполнена после реализации Sprint 15.

### Backlog Updates

- Добавить: refresh/invalidation strategy для versioned BM25 index.
- Перенести: gold evaluation и quality metrics в Phase 7.
- Изменить приоритет: `RET-002` подготовлен к Sprint 15.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
