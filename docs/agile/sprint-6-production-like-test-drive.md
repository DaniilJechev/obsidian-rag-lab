# Sprint 6 — Production-like PostgreSQL Test Drive

> Статус: `planned`
>
> Ветка реализации: `sprint/6-production-like-test-drive`
>
> Связанная фаза roadmap: `Фаза 2`
>
> Зависимость: Sprint 5 — idempotent ingestion

## Sprint Goal

Провести полный локальный ingestion DLS1+DLS2 и доказать через consistency,
failure-recovery и operational checks, что PostgreSQL data layer готов к
Phase 3 chunking.

## Why

Unit и integration tests показывают локальную корректность отдельных частей.
Production-like test drive проверяет, что все слои работают вместе на полном
разрешённом корпусе и дают наблюдаемый, согласованный результат.

## Backlog and estimate

- Backlog: `DATA-003`
- Estimate: 1 короткий sprint, ориентировочно 5–10 часов.
- Expected artifacts:
  - repeatable local test-drive command;
  - operational consistency queries;
  - observed baseline/repeat-run metrics;
  - failure/recovery evidence;
  - Phase 3 `note → chunks` handoff contract.

## Scope

- [ ] Выполнить полный локальный ingestion DLS1+DLS2.
- [ ] Зафиксировать total/new/changed/unchanged/failed/stale counters.
- [ ] Рассчитать duration и success rate из database state.
- [ ] Проверить rollback и recovery после искусственной failure.
- [ ] Проверить version mismatch и stale handling.
- [ ] Выполнить consistency checks между inventory, notes, states и runs.
- [ ] Проверить foreign keys, unique constraints и transaction boundaries.
- [ ] Подготовить operational queries и список ограничений.
- [ ] Подготовить handoff contract для будущей связи `note → chunks`.

## Metrics and invariants

Для каждого production-like run фиксируются только наблюдаемые значения:

```text
duration_seconds = finished_at - started_at
success_rate = (new + changed + unchanged) / total
```

При `total = 0` success rate равен `0.0`, чтобы не допускать деления на ноль.

Обязательные invariants:

- каждый discovered path в текущем scope имеет одну текущую запись `notes`;
- `notes.relative_path` уникален;
- каждая запись `ingestion_states` ссылается на существующие
  `note_id`, `run_id` и `index_version_id`;
- в одном run не более одного state для одной note;
- сумма `new + changed + unchanged + failed` равна количеству discovered
  documents;
- `stale` считается только внутри текущего `corpus_scope`;
- повторный run не увеличивает количество `notes` для уже известных paths;
- vault остаётся read-only.

## Dependencies and risks

- Sprint 5 implementation и migration head должны быть применены в PostgreSQL.
- Для полного run нужны `OBSIDIAN_VAULT_ROOT`, доступ к PostgreSQL и healthy
  Docker service.
- Полный run читается локально и не должен запускаться автоматически в CI.
- Реальные counters, duration и success rate нельзя определить заранее.
- Если consistency audit найдёт дефект ingestion, он становится carry-over, а
  не скрытой частью Sprint 6 validation.

## Out of Scope

- Cloud deployment и local-vs-cloud comparison — Phase 13.
- Chunker и выбор chunk size — Phase 3.
- Embeddings — Phase 4.
- Qdrant, BM25 и RRF — Phase 5.
- Retrieval metrics и gold eval set — Phase 7.
- Изменение файлов в `obsidianNotes`.

## Acceptance Criteria

- [ ] Полный локальный DLS1+DLS2 run завершён с наблюдаемым summary.
- [ ] Повторный run без изменений не создаёт дубликаты.
- [ ] Failure одной note не приводит к неконтролируемому partial state.
- [ ] Rollback/recovery behavior подтверждён тестом.
- [ ] Version mismatch корректно маркирует устаревший результат.
- [ ] Consistency checks проходят.
- [ ] Результаты и ограничения записаны для перехода к Phase 3.

## Definition of Done

- [ ] Scope выполнен или carry-over записан в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Tests и Ruff проходят.
- [ ] CI проходит после публикации.
- [ ] Vault остаётся read-only.
- [ ] Секреты не добавлены в Git.
- [ ] Production-like evidence и metrics записаны.
- [ ] Пользователь подтвердил завершение Sprint 6.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Sprint draft created | Implementation зависит от Sprint 5 idempotent ingestion |
| 2026-08-13 | Scope approved for implementation | `DATA-003`: full DLS1+DLS2 run, repeatability, consistency, failure/recovery, version/stale checks и Phase 3 handoff; chunking/retrieval остаются out of scope |

## Validation Evidence

До начала реализации production-like validation не выполнялась.

## Phase 3 handoff contract

Будущий chunker получает от текущего data layer:

```text
note_id
relative_path
content_hash
parser_version
source_directory
title
source_mtime
```

Каждый chunk должен будет дополнительно хранить:

```text
note_id
chunk_index
text
section_title
section_level
section_path
start_offset
end_offset
word_count
token_count
chunking_version
```

Sprint 6 фиксирует только handoff contract; chunker и выбор chunk size относятся
к Phase 3.

**Итоговый статус:** `planned`
