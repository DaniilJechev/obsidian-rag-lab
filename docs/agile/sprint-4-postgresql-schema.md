# Sprint 4 — PostgreSQL Schema and Migrations

> Статус: `closed`
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

- [x] Зафиксировать entity/data contract для `notes`, `ingestion_runs`,
  `ingestion_states`, `index_versions`, `chunks` и `note_links`.
- [x] Определить PostgreSQL types, nullability, defaults и JSONB contracts.
- [x] Определить primary keys, foreign keys, unique/check constraints и indexes.
- [x] Создать SQLAlchemy Core table metadata без ORM.
- [x] Настроить Alembic и initial migrations.
- [x] Поднять локальный PostgreSQL через Docker Compose и применить migrations
  на пустой базе.
- [x] Добавить schema integration tests на PostgreSQL.
- [x] Документировать связи, инварианты и SQL-эквиваленты существенных операций.
- [x] Проверить resolved и unresolved wikilinks через `note_links`.

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
- `docs/architecture/phase-2-database-schema.md` — schema/data contract,
  JSONB contracts и `note_links`.
- `docs/agile/sprint-4-postgresql-schema.md` — execution evidence.

## Acceptance Criteria

- [x] Пустая PostgreSQL database поднимается через Docker Compose.
- [x] `alembic upgrade head` создаёт всю согласованную schema.
- [x] Повторный `alembic upgrade head` не создаёт повторных объектов.
- [x] `notes.relative_path` имеет уникальное ограничение.
- [x] Foreign keys для note/run/state/chunk relationships проверяются.
- [x] `note_links` хранит raw references, resolved targets и unresolved links.
- [x] JSONB-поля имеют описанный shape и validation expectations.
- [x] Schema tests запускаются на PostgreSQL, а не только на SQLite.
- [x] `obsidianNotes` не изменяется.

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
| 2026-08-12 | Initial schema implementation | SQLAlchemy Core metadata, Alembic initial migration and PostgreSQL tables applied |
| 2026-08-12 | Schema parity verification | Explicit CHECK constraint names aligned metadata with PostgreSQL; `alembic check` passed |
| 2026-08-12 | Integration tests | PostgreSQL tests cover CHECK, UNIQUE, foreign keys, CASCADE and SET NULL behavior |
| 2026-08-12 | Clean bootstrap | Temporary `rag_bootstrap_test` started with no relations; `upgrade head` created the schema; database was removed after verification |
| 2026-08-12 | Repeatability check | Repeated `upgrade head` on the configured database produced no new upgrade |

## Validation Evidence

Реальные validation results:

```text
uv run alembic current
→ 909bce321e14 (head)

uv run alembic history
→ <base> -> 909bce321e14 (head), create initial schema

uv run alembic check
→ No new upgrade operations detected.

uv run ruff check .
→ All checks passed!

uv run pytest tests/test_postgres_schema.py -q
→ 7 passed

docker compose --env-file .env -f docker/compose.yml exec postgres psql -U rag -d rag_bootstrap_test -P pager=off -c "\dt"
→ Did not find any relations.

uv run alembic upgrade head  # temporary rag_bootstrap_test
→ Running upgrade  -> 909bce321e14, create initial schema

docker compose --env-file .env -f docker/compose.yml exec postgres psql -U rag -d rag_bootstrap_test -P pager=off -c "\dt"
→ 7 relations after bootstrap

uv run alembic upgrade head  # already-current configured database
→ no Running upgrade output
```

PostgreSQL inspection confirmed seven tables including `alembic_version`, the
expected primary/unique constraints, JSONB columns, and `note_links` foreign
keys with `ON DELETE CASCADE` and `ON DELETE SET NULL`.

The clean bootstrap used a temporary PostgreSQL database rather than the
existing Docker volume. The temporary database was dropped after verification;
the primary `rag` database and its volume were preserved.

## Completion

- [x] Definition of Done проверен по локальному и remote evidence.
- [x] Acceptance Criteria проверены; clean bootstrap и повторный `upgrade head`
  подтверждены на PostgreSQL.
- [x] Тесты и Ruff проходят; PostgreSQL integration suite подтвердил 7
  constraint/FK сценариев.
- [x] CI `Lint and test` прошёл в [PR #14](https://github.com/DaniilJechev/obsidian-rag-lab/pull/14).
- [x] Read-only vault не изменён, секреты не добавлены в Git.
- [x] Review/merge evidence подтверждены в
  [PR #14](https://github.com/DaniilJechev/obsidian-rag-lab/pull/14);
  merge commit: `17a711c`.
- [x] Backlog `DATA-001` обновлён до `done`.
- [x] Пользователь подтвердил завершение Sprint 4.

## Review

### Completed

- Schema contract, SQLAlchemy Core metadata и Alembic initial migration
  согласованы и применены к PostgreSQL.
- Constraint и foreign-key behavior покрыты integration tests.
- Воспроизводимость проверена через clean bootstrap временной базы.
- CI failure, вызванный отсутствующим `OBSIDIAN_VAULT_ROOT` в GitHub Actions,
  исправлен: schema tests теперь skip-аются без PostgreSQL credentials, не
  требуя vault-конфигурацию.

### Not Completed

- Repositories и idempotent ingestion не входят в Sprint 4 и перенесены в
  Sprint 5.
- Production-like полный прогон DLS1+DLS2 и consistency checks перенесены в
  Sprint 6.

### Technical Debt

- PostgreSQL integration tests требуют доступную локальную PostgreSQL и
  credentials; в CI без них они skip-аются.
- Windows pytest иногда завершается `WinError 5` при cleanup временной
  директории; сами тестовые assertions при этом проходят. Linux CI завершился
  успешно.
- JSONB shape validation остаётся Python/JSON Schema-layer contract, а не
  PostgreSQL-native JSON Schema constraint.

## Retrospective

- Явные имена `CHECK` constraints необходимы для стабильного `alembic check`;
  без них metadata и PostgreSQL могли ложно расходиться.
- Clean bootstrap на временной базе дал более сильное evidence
  воспроизводимости, чем проверка только существующего Docker volume.
- Schema integration tests нужно отделять от vault-конфигурации, поскольку
  database layer должен тестироваться независимо от read-only corpus.

## Post-merge

- PR [#14](https://github.com/DaniilJechev/obsidian-rag-lab/pull/14) merged
  в `main` с commit `17a711c`.
- Issue [#11](https://github.com/DaniilJechev/obsidian-rag-lab/issues/11)
  закрыт через `Closes #11`.
- Milestone `Phase 2 — PostgreSQL Data Layer` оставлен открытым: Sprint 5 и
  Sprint 6 ещё не завершены.

**Итоговый статус:** `closed`

**Дата планирования:** 2026-08-11
