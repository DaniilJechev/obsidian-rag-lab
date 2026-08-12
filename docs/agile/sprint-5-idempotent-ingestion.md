# Sprint 5 — Idempotent Ingestion

> Статус: `ready-for-closeout`
>
> Ветка реализации: `sprint/5-idempotent-ingestion`
>
> Связанная фаза roadmap: `Фаза 2`
>
> Зависимость: Sprint 4 — PostgreSQL schema and migrations

## Sprint Goal

Реализовать воспроизводимый ingestion flow для `DLS1 + DLS2`, который сравнивает
incoming metadata с PostgreSQL state и безопасно выбирает `new`, `changed`,
`unchanged`, `stale` или `failed`.

Главное свойство:

```text
same relative_path
+ same content_hash
+ same parser_version
= unchanged
→ повторную обработку можно пропустить
```

## Why

После Sprint 4 база имеет структуру, но не знает, как Python pipeline должен
сохранять notes и принимать решение `new/changed/unchanged/stale/failed`.
Идемпотентность нужна, чтобы повторный запуск был безопасным и предсказуемым.

Sprint 5 разделяет четыре уровня:

```text
Ingestion
    весь pipeline обработки и синхронизации данных

Ingestion orchestration
    координатор шагов pipeline

Decision logic
    чистое правило выбора действия для конкретной note

Repositories
    Python-слой доступа к PostgreSQL через SQLAlchemy Core
```

## Scope

- [x] Создать DB repositories поверх SQLAlchemy Core и существующего
  `src/rag_based_on_obsidian/db/connection.py`.
- [x] Реализовать repositories для `notes`, `ingestion_runs`,
  `ingestion_states` и `index_versions`.
- [x] Создать чистый decision module с детерминированными правилами:
  - отсутствующая note → `new`;
  - изменённый `content_hash` → `changed`;
  - изменённый `parser_version` → `changed`;
  - совпадающие path/hash/parser version → `unchanged`;
  - отсутствие ранее известной note в полном discovery scope → `stale`;
  - исключение при обработке note → `failed`.
- [x] Создать ingestion orchestration для discovery/parser/statistics
  contracts.
- [x] Сохранять `content_hash`, `parser_version`, run/state records и counters.
- [x] Реализовать transaction boundaries и изоляцию ошибки одной note через
  savepoint или эквивалентную SQLAlchemy Core стратегию.
- [x] Добавить unit tests для decision logic.
- [x] Добавить PostgreSQL integration tests для первого, повторного,
  изменённого и ошибочного запусков.
- [ ] Не включать полный corpus production-like run; он остаётся Sprint 6.

## Out of Scope

- Chunker и выбор chunk size — Phase 3.
- Embeddings — Phase 4.
- Qdrant, BM25 и RRF — Phase 5.
- Полный production-like DLS1+DLS2 test drive, duration/success-rate
  benchmark и consistency audit — Sprint 6.
- Cloud deployment — Phase 13.
- Изменение файлов в `obsidianNotes`.
- ORM и новые schema tables без отдельного согласования.

## Acceptance Criteria

- [x] Первый запуск контролируемого DLS2 scenario сохраняет новую note без дубликатов.
- [x] Повторный запуск без изменений пропускает unchanged note.
- [x] Изменение content hash вызывает reprocessing изменённой note.
- [x] Изменение parser version вызывает reprocessing.
- [x] Ошибка одной note сохраняется и не останавливает batch.
- [x] Run summary содержит `total`, `new`, `changed`, `unchanged`, `stale`,
  `failed`.
- [x] Состояния привязаны к конкретным `run_id`, `note_id` и
  `index_version_id`.
- [x] Повторное выполнение одного и того же batch не создаёт дубликаты.
- [x] Integration assertions проходят на PostgreSQL; локальный process exit
  загрязняется Windows pytest cleanup `PermissionError [WinError 5]`.
- [x] `obsidianNotes` не изменяется.

## Definition of Done

- [x] Scope выполнен или carry-over записан в backlog.
- [x] Acceptance Criteria проверены на контролируемых сценариях.
- [x] Unit и PostgreSQL integration assertions проходят; Windows cleanup
  остаётся локальным environmental carry-over.
- [x] Ruff проходит.
- [ ] CI проходит после публикации.
- [x] `obsidianNotes` остаётся read-only.
- [x] Секреты не добавлены в Git.
- [x] Идемпотентное поведение, counters и ограничения задокументированы.
- [ ] Пользователь подтвердил завершение Sprint 5.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Sprint draft created | Implementation зависит от Sprint 4 schema |
| 2026-08-12 | Scope approved | Вариант B: repositories, decision logic, orchestration и контролируемые PostgreSQL integration scenarios; полный corpus test drive оставлен Sprint 6 |
| 2026-08-12 | Implementation started | Добавлены pipeline contracts, `PARSER_VERSION`, decision logic, SQLAlchemy Core repositories, orchestration, savepoint isolation и unit/integration test scenarios |
| 2026-08-12 | Schema contract refined | Добавлена Alembic migration `c4f8a0d6e2b1`, разрешающая `new/changed/unchanged` в `ingestion_states.status` |
| 2026-08-13 | Migration and parity validated | Пользователь применил `alembic upgrade head`; `alembic check` сообщил `No new upgrade operations detected` |
| 2026-08-13 | Failure/stale coverage expanded | PostgreSQL scenario покрывает `new`, `unchanged`, `changed`, `failed`, `stale`; полный модуль дал 9 успешных assertions |
| 2026-08-13 | Review fixes | Исправлен статус пустого batch: `0` документов завершается как `completed`, а не `failed` |
| 2026-08-13 | Code review fixes | Исправлены retry после failed note, сохранение успешной note projection, race-safe index versions, failed-state persistence, concurrent run serialization, scope-aware stale detection, deterministic latest state и безопасный downgrade guard |

## Validation Evidence

Реальные команды и наблюдения:

- `uv run ruff check src/rag_based_on_obsidian tests/test_ingestion_decision.py tests/test_postgres_schema.py`
  — `All checks passed`.
- `uv run pytest tests/test_ingestion_decision.py -q`
  — `6 passed in 0.09s`, exit code `0`.
- `uv run pytest tests/test_ingestion_decision.py tests/test_markdown_parser.py tests/test_inventory_pipeline.py -q`
  — `16 passed`; process завершился с exit code `1` из-за Windows
  `PermissionError [WinError 5]` при pytest temp-directory cleanup.
- `uv run pytest tests/test_postgres_schema.py -q`
  — первый запуск до migration достиг `......F.`; после применения migration
  повторный полный запуск ещё требуется.
- `uv run alembic upgrade head` — migration `909bce321e14 -> c4f8a0d6e2b1`
  успешно применена пользователем вручную.
- `uv run pytest tests/test_postgres_schema.py::test_ingestion_is_idempotent_and_reprocesses_parser_changes -q -s`
  — assertion-level test прошёл (`.`), database constraint failure после
  migration отсутствует; процесс завершился с exit code `1` только из-за
  Windows `PermissionError [WinError 5]` во время pytest temp-directory cleanup.
- `uv run pytest tests/test_postgres_schema.py -q -s`
  — все 9 PostgreSQL assertions прошли (`.........`), включая idempotent,
  failed-note и stale-note scenarios; итоговый process exit code `1` вызван только тем же
  Windows `PermissionError [WinError 5]` во время pytest temp-directory cleanup.
- `uv run alembic check`
  — `No new upgrade operations detected`; live PostgreSQL schema совпадает с
  SQLAlchemy Core metadata.
- После migration повторный
  `uv run ruff check src/rag_based_on_obsidian tests/test_ingestion_decision.py tests/test_postgres_schema.py`
  — `All checks passed`.
- `uv run ruff check .` после code review fixes — `All checks passed`.
- `uv run pytest tests/test_ingestion_decision.py tests/test_postgres_schema.py -q -s`
  после code review fixes — все assertions прошли (`................`); итоговый
  process exit code `1` вызван только Windows `PermissionError [WinError 5]`
  при pytest temp-directory cleanup.

Migration применена, parity подтверждена. Функциональные assertions проходят.
Локальный Windows cleanup `PermissionError` не устраняется отключением cleanup
или ослаблением тестов; он остаётся environmental carry-over, который должен
быть отдельно проверен в CI/Linux.

## Review

Изменённое решение: состояния `new/changed/unchanged` сохраняются в
`ingestion_states` рядом с техническими статусами Sprint 4; это оформлено
versioned migration, чтобы metadata и live schema оставались воспроизводимыми.
Review проведён: repositories не содержат decision logic, orchestration
использует batch transaction и note-level savepoint, а PostgreSQL integration
проверяет все пять итоговых решений. Дополнительный read-only review выявил и
помог исправить retry после failed note, race conditions, scope-aware stale
detection и downgrade safety.

## Retrospective

Implementation выявила две границы для следующего шага:

1. локальный Windows pytest cleanup требует CI/Linux подтверждения с чистым
   process exit code;
2. полный DLS1+DLS2 прогон, duration/success-rate и consistency audit остаются
   Sprint 6, как и планировалось.

## Completion

- [x] Definition of Done проверен после database validation; CI остаётся
  внешним gate, который ещё не наблюдался для текущей ветки.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.

**Итоговый статус:** `ready-for-closeout`
