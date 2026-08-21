# Sprint 20 — HTTP /ingest and query logs

> Статус: `planned`
>
> Ветка: `sprint/20-fastapi-ingest-query-logs` (создаётся только при старте
> реализации, после merge Sprint 19)
>
> Связанная фаза roadmap: `Фаза 8`
>
> Backlog: `API-002`
>
> GitHub: [Issue #50](https://github.com/DaniilJechev/obsidian-rag-lab/issues/50),
> [Milestone Phase 8](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/9)

## Sprint Goal

Тот же FastAPI-процесс умеет запустить переиндексацию корпуса по HTTP
(`POST /ingest` → `run_id`, статус `GET /ingest/{run_id}`) и пишет каждый
`/search` в PostgreSQL `query_logs`.

## Why

Sprint 19 даёт кассу чтения. Без HTTP-записи после новых заметок снова нужен
CLI (`chunk` + `upsert-dense-sparse`). Query logs нужны, чтобы видеть, что
спрашивали, без разбора контейнерных логов. Roadmap Phase 8 (шаги 8.1, 8.5)
этим закрывается.

## Scope

- [ ] `POST /ingest` оркестрирует **существующие** chunk + upsert pipeline,
      не новый алгоритм. Сразу отвечает «принят, `run_id`»; работа в фоне.
- [ ] `GET /ingest/{run_id}` — статус запуска (опора на `ingestion_runs` /
      результат batch embedding, без отдельного job-фреймворка).
- [ ] Один ingest в полёте; второй `POST /ingest` → `409`.
- [ ] Read-only mount vault в контейнер `api` (нужен ingest, не search).
- [ ] Таблица `query_logs` (Alembic): timestamp, query, method, top_k,
      latency, result_count, error. Запись после каждого `/search`.
      Это не публичный URL `/query-logs`.
- [ ] Короткий sync latency baseline на тёплом процессе — только числа из
      реального прогона, без выдуманных метрик.
- [ ] Тесты: второй ingest не стартует; search пишет лог.

## Out of Scope

- Повтор Sprint 19 (`/health`, `/search`, первый Docker `api`).
- Bounded asyncio / fan-out «на глаз».
- Смена embedding-модели, generate, RAGAS, LangGraph, rerank, Telegram.
- Полный corpus ingest в CI.
- MLflow в compose.
- Реализация на ветке `main`.

## Expected Artifacts

- Маршруты `/ingest` на том же FastAPI app.
- Alembic-миграция `query_logs` + запись из `/search`.
- Compose: read-only vault mount для `api`.
- Таблица observed latency в этом документе после live-прогона.
- Этот sprint-документ.

## Acceptance Criteria

- [ ] Клиент `/ingest` не обязан держать HTTP открытым до конца pipeline.
- [ ] Параллельный второй ingest отвергается (`409`), пока первый не закончен.
- [ ] CLI `chunk` / `upsert-dense-sparse` не сломаны.
- [ ] После `/search` есть строка в `query_logs`.
- [ ] Vault read-only; секреты не в git.

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Документация и конфигурация обновлены, если это необходимо.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Зависит от merge Sprint 19: без живого `api` некуда вешать ingest.
- Реализация только на `sprint/20-fastapi-ingest-query-logs`.
- Долгий ingest: HTTP не должен ждать минуты (timeout клиента).
- Vault mount обязателен для ingest; без него контейнер не увидит DLS1/DLS2.

## Estimate

8–12 часов разработки.

## Proposed branch

`sprint/20-fastapi-ingest-query-logs` — не создана этим planning-шагом.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-21 | Planning на `main` | Документ создан; реализация не начата |

## Validation Evidence

### Commands

```text
(не заполнять до реализации)
```

### Test and Lint Results

- Tests: не запускались (planning only)
- Lint: не запускался (planning only)
- CI: не относится

### Metrics

| Metric | Value | Context |
|---|---:|---|
| — | — | Нет live-прогонов в planning |

## Review

### Completed

- Планирование Sprint 20.

### Not Completed

- HTTP ingest, query logs, latency baseline.

### Changed Decisions

- Ingest — фоновый job (`run_id`), не blocking POST до конца pipeline.

### Technical Debt

- —

## Retrospective

### What Went Well

- —

### What Was Difficult

- —

### What We Will Change

- —

### Backlog Updates

- Перенести: bounded asyncio — после профилирования, не в этом спринте.
- Изменить приоритет: нет.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** —
