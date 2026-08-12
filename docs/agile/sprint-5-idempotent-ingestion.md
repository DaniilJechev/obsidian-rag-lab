# Sprint 5 — Idempotent Ingestion

> Статус: `planned`
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

- [ ] Создать DB repositories поверх SQLAlchemy Core и существующего
  `src/rag_based_on_obsidian/db/connection.py`.
- [ ] Реализовать repositories для `notes`, `ingestion_runs`,
  `ingestion_states` и `index_versions`.
- [ ] Создать чистый decision module с детерминированными правилами:
  - отсутствующая note → `new`;
  - изменённый `content_hash` → `changed`;
  - изменённый `parser_version` → `changed`;
  - совпадающие path/hash/parser version → `unchanged`;
  - отсутствие ранее известной note в полном discovery scope → `stale`;
  - исключение при обработке note → `failed`.
- [ ] Создать ingestion orchestration для discovery/parser/statistics
  contracts.
- [ ] Сохранять `content_hash`, `parser_version`, run/state records и counters.
- [ ] Реализовать transaction boundaries и изоляцию ошибки одной note через
  savepoint или эквивалентную SQLAlchemy Core стратегию.
- [ ] Добавить unit tests для decision logic.
- [ ] Добавить PostgreSQL integration tests для первого, повторного,
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

- [ ] Первый запуск DLS1+DLS2 сохраняет новые notes без дубликатов.
- [ ] Повторный запуск без изменений пропускает unchanged notes.
- [ ] Изменение content hash вызывает reprocessing только изменённой note.
- [ ] Изменение parser version вызывает reprocessing.
- [ ] Ошибка одной note сохраняется и не останавливает batch.
- [ ] Run summary содержит `total`, `new`, `changed`, `unchanged`, `stale`,
  `failed`.
- [ ] Состояния привязаны к конкретным `run_id`, `note_id` и
  `index_version_id`.
- [ ] Повторное выполнение одного и того же batch не создаёт дубликаты.
- [ ] Integration tests проходят на PostgreSQL.
- [ ] `obsidianNotes` не изменяется.

## Definition of Done

- [ ] Scope выполнен или carry-over записан в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Unit и PostgreSQL integration tests проходят.
- [ ] Ruff проходит.
- [ ] CI проходит после публикации.
- [ ] `obsidianNotes` остаётся read-only.
- [ ] Секреты не добавлены в Git.
- [ ] Идемпотентное поведение, counters и ограничения задокументированы.
- [ ] Пользователь подтвердил завершение Sprint 5.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Sprint draft created | Implementation зависит от Sprint 4 schema |
| 2026-08-12 | Scope approved | Вариант B: repositories, decision logic, orchestration и контролируемые PostgreSQL integration scenarios; полный corpus test drive оставлен Sprint 6 |

## Validation Evidence

До начала реализации validation не выполнялась. После начала implementation здесь
будут записаны только реальные команды и результаты.

## Review

До начала implementation review и changed decisions отсутствуют.

## Retrospective

Будет заполнена после реализации и validation.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.

**Итоговый статус:** `planned`
