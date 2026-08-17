# Sprint 14 — Direct Qdrant Vector Storage

> Статус: `in-progress`
>
> Ветка: `sprint/14-qdrant-vector-storage`
>
> Связанная фаза roadmap: `Фаза 5`
>
> Backlog: `RET-001`

## Sprint Goal

Адаптировать существующий batch embedding pipeline так, чтобы каждый
провалидированный batch vectors сразу записывался в versioned Qdrant collection
без промежуточного JSON vector storage.

## Why

Sprint 11 доказал, что embeddings воспроизводимо создаются из versioned chunks.
Phase 5 должна заменить временный JSON handoff на постоянное operational
хранилище vectors. Прямой batch upsert уменьшает потребление памяти, позволяет
возобновлять загрузку после частичного сбоя и создаёт основу для retrieval.

## Scope

- [ ] Подключить локальный Qdrant service, configuration и health smoke test.
- [x] Ввести `VectorSink` contract и `QdrantVectorSink` implementation.
- [x] Выполнять idempotent Qdrant upsert сразу после validation каждого batch.
- [x] Зафиксировать collection dimension, distance metric, embedding version и
  payload schema.
- [x] Использовать стабильный point ID из source identity и index version;
  `chunk_id` сохраняется в payload.
- [x] Разделить безопасный versioned rebuild и явный `--recreate` режим.
- [x] Добавить collection creation, version checks, batch-upsert metrics и
  partial-failure handling.
- [x] Удалить `embeddings.json` и JSON vector writer из runtime pipeline.
- [x] Добавить CLI-операции для create, embed и verify vector storage.
- [x] Проверять consistency между PostgreSQL chunks и Qdrant points.

## Out of Scope

- Dense/BM25 search и RRF fusion — Sprint 15.
- Gold questions, RAGAS, MRR, nDCG и semantic quality evaluation — Phase 7.
- OpenRouter, LLM generation и FastAPI — более поздние фазы.
- Сравнение embedding-моделей — `EMB-003` deferred до evaluation-ready этапа.
- PostgreSQL + pgvector comparison — Phase 6.

## Expected Artifacts

- `src/rag_based_on_obsidian/vector_store/` — Qdrant client, sink и consistency
  services.
- `src/rag_based_on_obsidian/embeddings/pipeline.py` — direct batch sink
  integration без JSON vector accumulation.
- `configs/vector_store/` — collection, distance, version и connection settings.
- `src/rag_based_on_obsidian/cli_rag.py` — create/embed/verify commands.
- `tests/vector_store/` — Qdrant sink, schema, idempotency и consistency tests.
- `docs/architecture/phase-5-qdrant-retrieval.md` — versioned storage contract.
- MLflow metrics для upsert duration, throughput, failures и consistency checks.

## Acceptance Criteria

- [ ] Каждый успешно провалидированный batch записывается непосредственно в
  Qdrant.
- [ ] Повторный запуск с теми же point IDs не создаёт дубликаты.
- [ ] Collection создаётся с явными dimension, distance и version.
- [ ] Payload восстанавливает `chunk_id`, `note_id`, `chunking_version`,
  source path, section path, chunk index и text.
- [ ] Consistency verification выявляет missing, extra и mismatched points.
- [ ] Runtime pipeline не создаёт и не читает `embeddings.json`.
- [ ] Synthetic storage smoke test проходит на локальном Qdrant.

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
| in-progress | Direct sink slice | Validated batches write directly to versioned Qdrant collections |
| in-progress | Storage hardening | Retries, MLflow upsert metrics and PostgreSQL/Qdrant consistency verifier added |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run rag-cli vector-store create
uv run rag-cli vector-store embed
uv run rag-cli vector-store verify
```

### Test and Lint Results

- Tests: `PASS — 89 passed, 1 skipped, 18 deselected`
- Lint: `PASS — uv run ruff check .`
- Qdrant smoke: `NOT VERIFIED — sprint not started`
- CI: `NOT VERIFIED — no remote implementation push yet`

### Metrics

Будут измеряться после реализации: batch upsert duration, throughput, failure
rate, consistency mismatches, collection point count и process memory.

## Review

### Completed

- Planning scope согласован как direct Qdrant handoff без JSON vector storage.
- Initial direct Qdrant sink and consistency implementation added.
- Commit `b6f695b` records the initial vertical slice.
- Current working tree adds Qdrant retries, metrics, consistency verification,
  vector-store configuration, CLI operations and architecture documentation.
- Collection identity now includes chunking version, model, revision and
  dimension; verify reports explicit PostgreSQL/Qdrant point-count equality.

### Not Completed

- Real local Qdrant health/storage smoke test.
- Final CI evidence and sprint closeout.

### Changed Decisions

- Временный JSON handoff из Phase 4 заменяется прямым batch upsert в Qdrant.

### Technical Debt

- Требуется определить стратегию удаления или архивирования старых collection
  versions после появления нового embedding/index version.

## Retrospective

Будет заполнена после реализации Sprint 14.

### Backlog Updates

- Добавить: consistency и collection-version cleanup после первого Qdrant run.
- Перенести: semantic evaluation в Phase 7.
- Изменить приоритет: `RET-001` подготовлен к Sprint 14.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `in-progress`

**Дата завершения:** `не завершён`
