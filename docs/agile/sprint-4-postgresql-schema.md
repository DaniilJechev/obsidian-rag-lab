# Sprint 4 — PostgreSQL Schema and Migrations

> Статус: `planned`
>
> Ветка реализации: `sprint/4-postgresql-schema`
>
> Связанная фаза roadmap: `Фаза 2`
>
> GitHub Milestone: `Phase 2 — PostgreSQL Data Layer`

## Sprint Goal

Спроектировать и воспроизводимо создать PostgreSQL schema, которая безопасно
хранит metadata DLS1+DLS2, ingestion runs/states, pipeline versions и
будущую связь notes с chunks.

## Why

Phase 1 дала inventory и EDA, но JSON snapshot не является production-like
источником текущего состояния. До реализации ingestion нужно определить
таблицы, связи, constraints и migrations. Иначе идемпотентность Sprint 5
будет опираться на незафиксированные правила.

## Scope

- [ ] Зафиксировать entity/data contract для `notes`, `ingestion_runs`,
  `ingestion_states`, `index_versions` и `chunks`.
- [ ] Определить PostgreSQL types, nullability, defaults и JSONB contracts.
- [ ] Определить primary keys, foreign keys, unique/check constraints и indexes.
- [ ] Создать SQLAlchemy Core table metadata без ORM.
- [ ] Настроить Alembic и initial migrations.
- [ ] Поднять локальный PostgreSQL через Docker Compose и применить migrations
  на пустой базе.
- [ ] Добавить schema integration tests на PostgreSQL.
- [ ] Документировать связи, инварианты и SQL-эквиваленты существенных операций.

## Out of Scope

- Реализация ingestion batch и repositories — Sprint 5.
- Проверка idempotent ingestion на полном корпусе — Sprint 5.
- Chunker и выбор `chunk_size` — Phase 3.
- Embeddings — Phase 4.
- Qdrant, BM25 и RRF — Phase 5.
- Cloud deployment и local-vs-cloud comparison — Phase 13.
- ORM, Django и полноценные `eval_items`, `query_logs`, `model_metadata`,
  `cache` features.

## Expected Artifacts

- `alembic/` — versioned schema migrations.
- `src/rag_based_on_obsidian/db/` — SQLAlchemy Core metadata/configuration.
- `tests/` — PostgreSQL schema integration tests.
- `docs/architecture/phase-2-database-schema.md` — schema/data contract.
- `docs/agile/sprint-4-postgresql-schema.md` — execution evidence.

## Acceptance Criteria

- [ ] Пустая PostgreSQL database поднимается через Docker Compose.
- [ ] `alembic upgrade head` создаёт всю согласованную schema.
- [ ] Повторный `alembic upgrade head` не создаёт повторных объектов.
- [ ] `notes.relative_path` имеет уникальное ограничение.
- [ ] Foreign keys для note/run/state/chunk relationships проверяются.
- [ ] JSONB-поля имеют описанный shape и validation expectations.
- [ ] Schema tests запускаются на PostgreSQL, а не только на SQLite.
- [ ] `obsidianNotes` не изменяется.

## Definition of Done

- [ ] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит после публикации изменений.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Документация schema и migrations согласована.
- [ ] Пользователь подтвердил завершение Sprint 4.

## Учебный порядок

```text
1. PostgreSQL: database/table/row/column
2. Primary key и foreign key
3. Unique/check constraints
4. Indexes
5. Transactions на уровне schema operations
6. SQLAlchemy Core table metadata
7. Alembic revision и upgrade
8. Integration tests на реальном PostgreSQL
```

На каждом шаге сначала разбирается SQL, затем его Python-представление.
SQLAlchemy Core не должен скрывать смысл schema от пользователя.

## Draft Sprint 5

Sprint 5 реализует repositories и ingestion decision logic поверх готовой
schema:

```text
discover → parse → hash → compare → new/changed/unchanged/stale/failed
       → transaction → PostgreSQL state → run summary
```

Главная проверка: одинаковые `relative_path + content_hash +
parser_version` не приводят к ненужной повторной обработке или дубликатам.

## Draft Sprint 6

Sprint 6 проводит production-like test drive полного DLS1+DLS2:

- проверяет counters, success rate и duration;
- проверяет rollback, recovery и version mismatch;
- проверяет consistency между inventory и PostgreSQL;
- фиксирует operational queries и ограничения;
- подтверждает готовность data layer к Phase 3.

Это не cloud deployment. Cloud comparison остаётся отдельной задачей Phase 13.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-11 | Phase 2 decomposition | Sprint 4 — schema, Sprint 5 — idempotent ingestion, Sprint 6 — production-like test drive |
| 2026-08-11 | Stack decision | PostgreSQL, Docker Compose, psycopg, SQLAlchemy Core, Alembic, pytest |
| 2026-08-11 | Corpus decision | Первый полный ingestion: DLS1 + DLS2 |

## Validation Evidence

До начала реализации validation не выполнялась. Здесь будут записаны реальные
команды и результаты Sprint 4; выдуманные результаты не добавляются.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены.
- [ ] Backlog обновлён.

**Итоговый статус:** `planned`

**Дата планирования:** 2026-08-11
