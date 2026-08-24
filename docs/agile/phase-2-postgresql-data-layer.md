# Phase 2 — PostgreSQL Data Layer

> Статус: `completed`
>
> Roadmap: `Фаза 2`
>
> Корпус первого полного ingestion: `DLS1 + DLS2`

## Цель фазы

Сделать PostgreSQL источником правды для metadata заметок, ingestion state,
версий pipeline и истории запусков, не изменяя read-only vault.

Phase 2 подготавливает data layer для:

```text
Phase 3 — chunking
Phase 4 — local embeddings
Phase 5 — Qdrant retrieval
Phase 7 — retrieval evaluation
```

PostgreSQL не заменяет исходный `obsidianNotes`. Исходные Markdown-файлы
остаются read-only, а база хранит состояние обработки и производные данные.

## Согласованный stack

```text
PostgreSQL
    сама реляционная база данных

Docker Compose
    локальный запуск PostgreSQL

psycopg
    PostgreSQL driver для Python

SQLAlchemy Core
    явный Python data-access layer без ORM

Alembic
    версионированные изменения schema

pytest
    unit и integration tests
```

Поток данных:

```text
DLS1 + DLS2 read-only
    → discovery
    → Markdown parser
    → statistics/content hash
    → ingestion decision
    → PostgreSQL
```

## Почему фаза разделена на три sprint-а

Каждый sprint отвечает на отдельный инженерный вопрос:

```text
Sprint 4: Как устроены данные?
Sprint 5: Как pipeline безопасно пишет и повторно обрабатывает данные?
Sprint 6: Можно ли доверять результату и готовы ли мы к Phase 3?
```

Такое разделение уменьшает coupling между schema, application logic и
operational validation, а также позволяет отдельно проверять ошибки SQL,
идемпотентности и consistency.

## Sprint 4 — проектирование schema и migrations

Подробный документ: `docs/agile/sprint-4-postgresql-schema.md`.

Результат:

- entity/data contract;
- таблицы `notes`, `ingestion_runs`, `ingestion_states_by_note`,
  `index_versions`, `note_links`;
- schema contract для `chunks`;
- primary/foreign keys, unique/check constraints и indexes;
- JSONB contract для structured metadata;
- Alembic migrations, применяемые на пустом локальном PostgreSQL;
- integration tests схемы.

Sprint 4 не реализует ingestion, chunker, embeddings, Qdrant или API.

## Sprint 5 — реализация и идемпотентность

Подробный draft: `docs/agile/sprint-5-idempotent-ingestion.md`.

### Цель

Подключить существующие discovery/parser contracts к PostgreSQL и доказать,
что повторный ingestion не создаёт дубликаты и не выполняет ненужную работу.

### Scope

- database configuration без секретов в Git;
- SQLAlchemy Core engine через psycopg;
- repositories для notes, runs, states и versions;
- ingestion flow для DLS1+DLS2;
- решения `new`, `changed`, `unchanged`, `stale`, `failed`;
- content hash и parser version comparison;
- transactions и error isolation;
- run counters;
- integration tests на первом, повторном, изменённом и ошибочном запуске.

### Основное правило идемпотентности

```text
same relative_path
+ same content_hash
+ same parser_version
= unchanged: повторную обработку можно пропустить
```

Изменение content hash или parser version требует reprocessing.
Ошибка одной заметки сохраняется, но не должна останавливать весь batch.

### Результат

Первый запуск сохраняет новые notes, повторный запуск пропускает unchanged
documents, изменение документа вызывает reprocessing, а failure accounting
остаётся наблюдаемым.

## Sprint 6 — production-like test drive

Подробный draft: `docs/agile/sprint-6-production-like-test-drive.md`.

### Цель

Провести полный локальный прогон на DLS1+DLS2 и проверить, что data layer
наблюдаем, согласован и готов к Phase 3.

### Scope

- полный локальный ingestion;
- counters `total/new/changed/unchanged/failed/stale`;
- success rate и duration;
- rollback и recovery после failure;
- version mismatch и stale handling;
- consistency checks между inventory, notes, states и runs;
- foreign key, unique constraint и transaction checks;
- operational queries и ограничения;
- handoff contract для будущих chunks.

### Результат

Мы получаем evidence, что PostgreSQL корректно отражает состояние полного
разрешённого корпуса и готов хранить будущие chunks. Это production-like
test drive, а не cloud deployment.

## Границы фазы

В Phase 2 не входят:

- chunker и выбор `chunk_size` — Phase 3;
- embeddings — Phase 4;
- Qdrant и BM25/RRF — Phase 5;
- pgvector comparison — Phase 6;
- gold eval и nDCG/MRR — Phase 7;
- FastAPI — Phase 8;
- cloud deployment/local-vs-cloud comparison — Phase 13.

## Переход к Phase 3

Phase 2 считается готовой к переходу, когда:

- notes имеют стабильный идентификатор и content hash;
- parser/chunking/embedding versions представлены в data contract;
- ingestion повторяем и идемпотентен;
- failed/stale состояния диагностируемы;
- run summary вычисляется из database state;
- schema поддерживает связь `note → chunks`;
- полный локальный DLS1+DLS2 test drive завершён;
- deferred chunking work явно передан в Phase 3.

## Phase 2 closeout evidence

Phase 2 завершена после merge Sprint 6:

- Sprint 4: PostgreSQL schema, SQLAlchemy Core metadata и Alembic migrations
  merged в `main`.
- Sprint 5: repositories и idempotent ingestion merged в `main`; backlog
  `DATA-002` закрыт.
- Sprint 6: production-like DLS1+DLS2 test drive и consistency evidence
  merged в `main` через [PR #17](https://github.com/DaniilJechev/obsidian-rag-lab/pull/17),
  merge commit `f1f9afb0`.
- Local validation: `40 passed, 1 skipped, 14 deselected`; manual PostgreSQL
  suite: `11 passed`; Ruff: `All checks passed`.
- Production-like baseline: `230` discovered notes, `100%` success rate,
  consistency `PASS`, без duplicate paths и orphan references.
- `obsidianNotes` оставлен read-only; secrets в Git не добавлялись.

**Итоговый статус Phase 2:** `completed`. Следующий инженерный результат —
планирование Phase 3 heading-aware/recursive chunking; chunker ещё не
реализован и не считается частью Phase 2.
