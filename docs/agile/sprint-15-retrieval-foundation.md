# Sprint 15 — Dense, BM25 and Retrieval Contract

> Статус: `completed`
>
> Ветка: `sprint/15-retrieval-foundation`
>
> Связанная фаза roadmap: `Фаза 5`
>
> Backlog: `RET-002`, `RET-003`

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

- [x] Создать `RetrievedChunk` contract с `chunk_id`, text, scores, metadata,
  retrieval method и version fields.
- [x] Реализовать query embedding через тот же versioned
  `EmbeddingProvider`, что используется для document vectors.
- [x] Реализовать dense Qdrant search с `top_k` и metadata filters.
- [x] Создать lexical index contract boundary и первую Qdrant sparse BM25
  реализацию по named vector `bm25` (IDF) на тех же points, что и dense.
- [x] Реализовать BM25 lexical search с теми же `chunk_id` и metadata.
- [x] Реализовать RRF fusion dense и BM25 результатов с устранением дублей.
- [x] Добавить CLI для synthetic dense и hybrid search.
- [x] Добавить deterministic retrieval unit tests и понятный JSON console output.
- [x] Зафиксировать Phase 5 retrieval architecture и границы до Phase 7/9.

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
  Qdrant sparse BM25 и RRF fusion.
- `src/rag_based_on_obsidian/cli_rag.py` — dense/BM25/hybrid search commands и
  ingest alias `upsert-dense-sparse`.
- `configs/retrieval/` — `top_k`, filters и RRF configuration.
- `configs/vector_store/qdrant.yaml` — Qdrant URL, base collection name,
  `bm25_avg_len` и `bm25_model`.
- `tests/retrieval/` — contract, dense, sparse BM25, RRF, filter и CLI tests.
- `docs/architecture/phase-5-qdrant-retrieval.md` — retrieval data flow and
  contracts.
- MLflow experiment `searching` и JSON console evidence for synthetic smoke.

## Acceptance Criteria

- [x] Query embedding совместим с dimension и model version collection.
- [x] Dense search возвращает deterministic top-k results с payload metadata.
- [x] Metadata filters ограничивают результаты ожидаемым образом.
- [x] BM25 находит chunks по exact terms и возвращает стабильные `chunk_id`.
- [x] RRF объединяет dense и BM25 без duplicate chunks.
- [x] `RetrievedChunk` скрывает backend-specific детали Qdrant и BM25.
- [x] CLI выводит synthetic dense/hybrid top-k results с scores и provenance.
- [x] Smoke tests подтверждают техническую корректность, но не semantic quality.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Documentation/configuration обновлены.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [x] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| implementation | Added retrieval contracts, Qdrant dense adapter, first BM25 path, RRF and async hybrid pipeline | First retrieval vertical slice implemented |
| implementation | Added `rag-cli search dense/bm25/hybrid` and `configs/retrieval/retrieval.yaml` | CLI and configuration boundary implemented |
| implementation | Replaced in-memory `rank-bm25` with Qdrant named sparse `bm25` on the same points as dense; Python RRF stays in-process | Search CLI no longer loads PostgreSQL chunks at query time |
| implementation | Renamed ingest CLI from `embed` to `upsert-dense-sparse` | Command name states dense cosine plus BM25 sparse upsert |
| implementation | Removed unused `rank-bm25` dependency (`RET-003`) | Lexical search uses only Qdrant sparse `bm25` |
| validation | Live hybrid search against `rag_chunks_dense_sparse__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384` | JSON top-5 with `retrieval_method=hybrid`, both `dense_score` and `bm25_score`, payload provenance |
| validation | Full Ruff and pytest | Ruff passed; `104 passed, 1 skipped, 18 deselected` |
| closeout | Merged PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41); CI Lint and test SUCCESS; Issue [#38](https://github.com/DaniilJechev/obsidian-rag-lab/issues/38) closed | Merge commit `46b4234`; `RET-002`/`RET-003` complete |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run rag-cli vector-store upsert-dense-sparse
uv run rag-cli search hybrid --query "synthetic retrieval query"
```

### Test and Lint Results

- Tests: `PASS — uv run --no-sync pytest -q` (`104 passed, 1 skipped, 18 deselected`)
- Lint: `PASS — uv run --no-sync ruff check .`
- Retrieval smoke: `PASS — live hybrid JSON top-5 against collection rag_chunks_dense_sparse__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384`; no semantic-quality claim
- CI: `PASS — GitHub Actions Lint and test` on PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41) (`SUCCESS`, 2026-08-19T19:09:09Z)

### Metrics

Observed on live hybrid smoke: `result_count=5`, both `dense_score` and `bm25_score` present, `retrieval_method=hybrid`. Query-embedding model load remains the dominant CLI cold-start cost; Qdrant dense+sparse search is not the bottleneck. Exact stage latencies were not recorded as committed metrics.

## Review

### Completed

- Retrieval scope согласован как technical smoke foundation без evaluation.
- Dense, Qdrant sparse BM25 и Python RRF работают на одной versioned collection.
- Live hybrid CLI smoke подтверждён пользователем.

### Not Completed

- Sprint 16 planned as branch-only pgvector experiment
  (`docs/agile/sprint-16-pgvector-dense-experiment.md`); not merged to `main`.

### Changed Decisions

- Synthetic queries используются только для проверки pipeline correctness, а не
  для выбора embedding-модели или оценки retrieval quality.
- BM25 больше не строится in-memory из PostgreSQL; lexical search идёт в Qdrant
  sparse slot `bm25` с `modifier=IDF`.
- Ingest CLI называется `upsert-dense-sparse`, не `embed`.

### Technical Debt

- `postgres_batch_size` in `configs/retrieval/retrieval.yaml` is leftover from
  the in-memory BM25 loader.
- CLI search reloads the embedding model on every process start; a long-lived
  FastAPI process (Phase 8) should keep the provider warm. This is not a
  Sprint 15 blocker.

## Retrospective

- Что сработало: один Qdrant point с named vectors `dense`+`bm25` убрал join
  Postgres↔Qdrant на query path и оставил Python RRF прозрачным для тестов.
- Что улучшить: cold start `rag-cli search` упирается в загрузку e5, не в Qdrant.
- Перенести: semantic evaluation в Phase 7; warm embedding process в serving.

### Backlog Updates

- Добавить: держать embedding model в долгоживущем процессе (Phase 8 API), не в CLI.
- `RET-003` выполнен в том же PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41).
- Перенести: gold evaluation и quality metrics в Phase 7.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.
- [x] Следующий sprint выбран или запланирован.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-19`
