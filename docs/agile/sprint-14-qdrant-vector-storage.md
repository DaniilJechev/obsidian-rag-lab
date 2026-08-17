# Sprint 14 — Direct Qdrant Vector Storage

> Статус: `completed`
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

- [x] Подключить локальный Qdrant service, configuration и health smoke test.
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

- [x] Каждый успешно провалидированный batch записывается непосредственно в
  Qdrant.
- [x] Повторный запуск с теми же point IDs не создаёт дубликаты.
- [x] Collection создаётся с явными dimension, distance и version.
- [x] Payload восстанавливает `chunk_id`, `note_id`, `chunking_version`,
  source path, section path, chunk index и text.
- [x] Consistency verification выявляет missing, extra и mismatched points.
- [x] Runtime pipeline не создаёт и не читает `embeddings.json`.
- [x] Synthetic storage smoke test проходит на локальном Qdrant.

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
| planned | Sprint created | Implementation not started |
| in-progress | Direct sink slice | Validated batches write directly to versioned Qdrant collections |
| in-progress | Storage hardening | Retries, MLflow upsert metrics and PostgreSQL/Qdrant consistency verifier added |
| validated | Real run and rerun | 733 chunks embedded, 733 Qdrant points, no failures or mismatches; rerun reported idempotent behavior |

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

- Tests: `PASS — 90 passed, 1 skipped, 18 deselected`
- Lint: `PASS — uv run ruff check .`
- Qdrant smoke: `PASS — user-reported local smoke test`
- CI: `PASS — PR #39, GitHub Actions Lint and test`
- Merge: `PASS — PR #39 merged into main with merge commit 363a53e9`

### Metrics

Observed real run:

- chunks total: `733`
- embeddings succeeded: `733`
- failures: `0`
- embedding duration: `275.626s`
- Qdrant points: `733`
- consistency mismatches: `0`
- verify duration: `0.228s`
- verdict: `PASS`

## Review

### Completed

- Planning scope согласован как direct Qdrant handoff без JSON vector storage.
- Initial direct Qdrant sink and consistency implementation added.
- Commit `b6f695b` records the initial vertical slice.
- Current working tree adds Qdrant retries, metrics, consistency verification,
  vector-store configuration, CLI operations and architecture documentation.
- Collection identity now includes chunking version, model, revision and
  dimension; verify reports explicit PostgreSQL/Qdrant point-count equality.
- Real embedding and verify run completed successfully; repeated run was
  reported idempotent by the user.

### Not Completed

- Sprint 15 remains open in the Phase 5 milestone; it is the next planned
  retrieval sprint.

### Changed Decisions

- Временный JSON handoff из Phase 4 заменяется прямым batch upsert в Qdrant.

### Technical Debt

- Требуется определить стратегию удаления или архивирования старых collection
  versions после появления нового embedding/index version.

## Retrospective

### What went well

- Direct Qdrant upsert removed the runtime JSON vector handoff while retaining
  bounded batches and partial-failure accounting.
- Stable source-based point IDs, versioned collection names and explicit
  `--recreate` made reruns safe and operationally predictable.
- The real run and consistency verification produced `733/733` points with
  zero failures and zero mismatches.

### Difficulties

- CPU embedding remained the dominant runtime cost: the observed full run took
  `275.626s` for 733 chunks.
- GitHub experienced a temporary web/API outage during PR access and merge
  preparation; the remote merge succeeded after service recovery.

### Follow-up

- Define collection-version cleanup or archival policy.
- Continue with Sprint 15 retrieval contracts, dense search, BM25 and RRF.

### Backlog Updates

- Добавить: collection-version cleanup/archival policy.
- Перенести: semantic evaluation в Phase 7.
- Закрыть: `RET-001` после merge PR #39 — выполнено.

## Completion

- [x] Definition of Done проверен локально и подтверждён remote evidence.
- [x] Review проведён в формате owner-authorized review waiver.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.
- [x] Sprint 15 запланирован как следующий sprint.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-17`
