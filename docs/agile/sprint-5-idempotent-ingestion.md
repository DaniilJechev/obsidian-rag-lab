# Sprint 5 — Idempotent Ingestion

> Статус: `draft`
>
> Ветка реализации: `sprint/5-idempotent-ingestion`
>
> Связанная фаза roadmap: `Фаза 2`
>
> Зависимость: Sprint 4 — PostgreSQL schema and migrations

## Sprint Goal

Подключить discovery/parser pipeline к PostgreSQL и доказать, что повторный
ingestion не создаёт дубликаты и не выполняет ненужную обработку.

## Why

После Sprint 4 база имеет структуру, но не знает, как Python pipeline должен
сохранять notes и принимать решение `new/changed/unchanged/stale/failed`.
Идемпотентность нужна, чтобы повторный запуск был безопасным и предсказуемым.

## Scope

- [ ] Настроить безопасную database configuration.
- [ ] Подключить SQLAlchemy Core через psycopg.
- [ ] Реализовать repositories для notes, runs, states и versions.
- [ ] Соединить существующие discovery/parser/statistics contracts с database layer.
- [ ] Реализовать `new`, `changed`, `unchanged`, `stale`, `failed`.
- [ ] Сохранять content hash и parser version.
- [ ] Добавить transaction boundaries и error isolation.
- [ ] Добавить run counters и success/failure accounting.
- [ ] Написать integration tests на первом, повторном, изменённом и ошибочном
  запуске.

## Out of Scope

- Chunker и выбор chunk size — Phase 3.
- Embeddings — Phase 4.
- Qdrant, BM25 и RRF — Phase 5.
- Cloud deployment — Phase 13.
- Изменение файлов в `obsidianNotes`.

## Acceptance Criteria

- [ ] Первый запуск DLS1+DLS2 сохраняет новые notes без дубликатов.
- [ ] Повторный запуск без изменений пропускает unchanged notes.
- [ ] Изменение content hash вызывает reprocessing только изменённой note.
- [ ] Изменение parser version вызывает reprocessing.
- [ ] Ошибка одной note сохраняется и не останавливает batch.
- [ ] Run summary содержит total/new/changed/unchanged/failed/stale.
- [ ] Integration tests проходят на PostgreSQL.

## Definition of Done

- [ ] Scope выполнен или carry-over записан в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Tests и Ruff проходят.
- [ ] CI проходит после публикации.
- [ ] Vault остаётся read-only.
- [ ] Секреты не добавлены в Git.
- [ ] Идемпотентное поведение и ограничения задокументированы.
- [ ] Пользователь подтвердил завершение Sprint 5.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Sprint draft created | Implementation зависит от Sprint 4 schema |

## Validation Evidence

До начала реализации validation не выполнялась.

**Итоговый статус:** `draft`
