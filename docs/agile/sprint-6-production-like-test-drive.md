# Sprint 6 — Production-like PostgreSQL Test Drive

> Статус: `completed`
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

- [x] Выполнить полный локальный ingestion DLS1+DLS2.
- [x] Зафиксировать total/new/changed/unchanged/failed/stale counters.
- [x] Рассчитать duration и success rate из database state.
- [x] Проверить rollback и recovery после искусственной failure.
- [x] Проверить version mismatch и stale handling.
- [x] Выполнить consistency checks между inventory, notes, states и runs.
- [x] Проверить foreign keys, unique constraints и transaction boundaries.
- [x] Подготовить operational queries и список ограничений.
- [x] Подготовить handoff contract для будущей связи `note → chunks`.

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

- [x] Полный локальный DLS1+DLS2 run завершён с наблюдаемым summary.
- [x] Повторный run без изменений не создаёт дубликаты.
- [x] Failure одной note не приводит к неконтролируемому partial state.
- [x] Rollback/recovery behavior подтверждён тестом.
- [x] Version mismatch корректно маркирует устаревший результат.
- [x] Consistency checks проходят.
- [x] Результаты и ограничения записаны для перехода к Phase 3.

## Definition of Done

- [x] Scope выполнен; carry-over отсутствует, deferred chunking передан в Phase 3.
- [x] Acceptance Criteria проверены.
- [x] Tests и Ruff проходят.
- [x] CI проходит после публикации.
- [x] Vault остаётся read-only.
- [x] Секреты не добавлены в Git.
- [x] Production-like evidence и metrics записаны.
- [x] Пользователь подтвердил завершение Sprint 6.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Sprint draft created | Implementation зависит от Sprint 5 idempotent ingestion |
| 2026-08-13 | Scope approved for implementation | `DATA-003`: full DLS1+DLS2 run, repeatability, consistency, failure/recovery, version/stale checks и Phase 3 handoff; chunking/retrieval остаются out of scope |
| 2026-08-13 | Baseline production-like run | `run_id=85`; 230 discovered, 230 unchanged, 0 failed, 0 stale; database duration `5.768s`; success rate `100%`; consistency `PASS` |
| 2026-08-13 | Repeatability and SQL audit | Second unchanged run produced no duplicate paths; latest run had 230 states, 0 duplicate paths, 0 orphan note/run/index references; notes in DLS1+DLS2 scope: 230 |
| 2026-08-13 | Failure/recovery and version/scope tests | PostgreSQL scenarios cover isolated parse failure, fixed-source retry, parser version mismatch (`changed`) and scope-aware stale exclusion; counters observed as expected |
| 2026-08-13 | Implementation PR merged | PR [#17](https://github.com/DaniilJechev/obsidian-rag-lab/pull/17) merged into `main` with merge commit `f1f9afb0`; CI `Lint and test` passed |
| 2026-08-13 | Sprint closeout | DoD confirmed; no carry-over inside Sprint 6; chunking remains explicitly deferred to Phase 3 |

## Validation Evidence

Production-like validation выполнена локально:

- `python -m rag_based_on_obsidian.ingestion.test_drive` завершил полный
  DLS1+DLS2 run `85`: `total=230`, `unchanged=230`, `failed=0`, `stale=0`,
  `success_rate=100%`, consistency `PASS`.
- Read-only PostgreSQL audit подтвердил `0` duplicate paths, `0` orphan note
  states, `0` orphan run states и `0` orphan index states.
- Повторный ingestion не увеличил число `notes`: в разрешённом scope осталось
  `230` записей.
- Integration scenarios проверяют failure isolation, rollback через test
  transaction, retry после исправления source, parser-version mismatch и
  scope-aware stale detection.
- Ruff проходит: `uv run ruff check src/ tests/`.
- Project-local pytest temp root `.pytest-tmp` устраняет Windows cleanup failure
  на `%LOCALAPPDATA%\\Temp\\pytest-of-*\\pytest-current`; default validation
  теперь завершается с `40 passed, 1 skipped, 14 deselected`.
- PostgreSQL integration suite `tests/test_postgres_schema.py` помечен как
  `manual`, чтобы обычный `uv run pytest -q` и CI не зависели от локального
  Docker/PostgreSQL. Явный запуск `uv run pytest tests/test_postgres_schema.py
  -q -m manual` завершается с `11 passed`.
- На Windows для этого ручного integration run рекомендуется запускать
  PowerShell/Terminal от имени администратора как operational precaution для
  доступа к Docker/PostgreSQL и file locks; стандартный project-local pytest
  workflow от администратора не зависит.

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

**Итоговый статус:** `completed`; Sprint 6 implementation PR merged, closeout
evidence recorded, and Phase 3 handoff confirmed.
