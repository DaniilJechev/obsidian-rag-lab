# Sprint 6 — Production-like PostgreSQL Test Drive

> Статус: `draft`
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

## Validation Evidence

До начала реализации validation не выполнялась.

**Итоговый статус:** `draft`
