# Sprint 20 — HTTP /ingest and query logs

> Статус: `completed`
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

- [x] `POST /ingest` оркестрирует **существующие** chunk + upsert pipeline,
      не новый алгоритм. Сразу отвечает «принят, `run_id`»; работа в фоне.
- [x] `GET /ingest/{run_id}` — статус запуска (опора на `ingestion_runs` /
      результат batch embedding, без отдельного job-фреймворка).
- [x] Один ingest в полёте; второй `POST /ingest` → `409`.
- [x] Read-only mount vault в контейнер `api` (нужен ingest, не search).
- [x] Таблица `query_logs` (Alembic): timestamp, query, method, top_k,
      latency, result_count, error. Запись после каждого `/search`.
      Это не публичный URL `/query-logs`.
- [x] Короткий sync latency baseline на тёплом процессе — только числа из
      реального прогона, без выдуманных метрик.
- [x] Тесты: второй ingest не стартует; search пишет лог.
- [x] `GET /ingest/current` — последний `ingestion_runs` без копирования
      `run_id` (`/ingest/current` зарегистрирован до `/ingest/{run_id}`).

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

- [x] Клиент `/ingest` не обязан держать HTTP открытым до конца pipeline.
- [x] Параллельный второй ingest отвергается (`409`), пока первый не закончен.
- [x] CLI `chunk` / `upsert-dense-sparse` не сломаны.
- [x] После `/search` есть строка в `query_logs`.
- [x] Vault read-only; секреты не в git.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [x] Пользователь подтвердил live-проверку ingest/`/ingest/current`;
      implementation PR [#54](https://github.com/DaniilJechev/obsidian-rag-lab/pull/54)
      merged.

## Dependencies and risks

- Зависит от merge Sprint 19: без живого `api` некуда вешать ingest.
- Реализация только на `sprint/20-fastapi-ingest-query-logs`.
- Долгий ingest: HTTP не должен ждать минуты (timeout клиента).
- Vault mount обязателен для ingest; без него контейнер не увидит DLS1/DLS2.

## Estimate

8–12 часов разработки.

## Proposed branch

`sprint/20-fastapi-ingest-query-logs`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-21 | Planning на `main` | Документ создан; реализация не начата |
| 2026-08-22 | Implementation | `POST /ingest` 202 + 409, `GET /ingest/{run_id}`, `query_logs` + Alembic, тёплый e5, bind mount vault |
| 2026-08-23 | Schema rename | `ingestion_states` → `ingestion_states_by_note` (Alembic `a8c3e1f6b4d0`) |
| 2026-08-24 | UX | `GET /ingest/current` — последний `ingestion_runs` без копирования `run_id` |
| 2026-08-24 | Live | Owner: ingest `205` completed 230/230; `/ingest/current` совпал с `/ingest/205`; второй POST → already in progress |
| 2026-08-24 | Schema | `query_logs.created_at` DEFAULT `now()` (`d5e1a7c3b9f2`); INSERT пишет UTC timestamp |
| 2026-08-24 | Merge PR [#54](https://github.com/DaniilJechev/obsidian-rag-lab/pull/54) | `c664243` в `main`; Issue [#50](https://github.com/DaniilJechev/obsidian-rag-lab/issues/50) closed. Milestone 9: `open_issues=0` (закрывается в closeout). |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run pytest tests/api -q
```

Live (владелец, после alembic + `--build api`):

```text
docker compose --env-file .env -f docker/compose.yml up -d --build api
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/ingest -H "Content-Type: application/json" --data-raw "{}"
curl.exe http://127.0.0.1:8000/ingest/205
curl.exe http://127.0.0.1:8000/ingest/current
```

Сразу после recreate `curl /health` может дать `Empty reply from server` (e5
ещё грузится). Повтор после warmup: `"status":"ok"`.

`GET /ingest` без id → `Method Not Allowed` (нужен POST или `/ingest/current`).

### Test and Lint Results

- Tests: `uv run pytest -q` — **158 passed**, 1 skipped, 18 deselected
  (`not manual`), 1 Starlette/httpx warning, 2026-08-24 (closeout rerun:
  158 passed, 1 skipped, 18 deselected, 1 warning in 58.83s).
- Lint: `uv run ruff check .` — All checks passed, 2026-08-24.
- CI: PR [#54](https://github.com/DaniilJechev/obsidian-rag-lab/pull/54)
  `Lint and test` SUCCESS, run
  [32708806228](https://github.com/DaniilJechev/obsidian-rag-lab/actions/runs/32708806228).

### Metrics

Только наблюдаемые прогоны. Wall ingest = `finished_at - started_at`.

| Metric | Value | Context |
|---|---:|---|
| POST `/ingest` → 202 | 0.396 s (curl) | run 203; HTTP не ждёт pipeline |
| ingest 203 wall | 274 s | DLS1+DLS2, 230/230/0/0, `completed` |
| ingest 204 wall | 248 s | повторный полный прогон, 230/230/0/0 |
| ingest 205 wall | 298 s | owner live, 08:07:32Z–08:12:30Z, 230/230/0/0 |
| second POST while running | 409 | owner: `an ingest run is already in progress` |
| hybrid `/search` during ingest | 0.414 s curl / 368 ms log | search не падает на фоне upsert |
| hybrid `/search` after ingest | 0.266 s curl / 215 ms log | probe `sprint20-query-log-probe` |
| empty query | 422 | не пишется в `query_logs` |
| `/ingest/current` | same JSON as `/ingest/205` | owner, after rebuild, 205 `completed` |

## Review

### Completed

- HTTP `POST /ingest` 202 + `run_id`, фон, `GET /ingest/{run_id}`, `GET /ingest/current`.
- `409` на второй ingest, пока первый `running`.
- `query_logs` + Alembic; `created_at` через SQL `now()` и UTC в INSERT.
- Read-only vault bind `ML_NLP`; live ingest 205 230/230.
- Latency baseline записан из live-прогонов.

### Not Completed

- Нет. Implementation merged; следующий sprint не планировался в этом closeout.

### Changed Decisions

- Ingest — фоновый job (`run_id`), не blocking POST до конца pipeline.
- `GET /ingest/current` — последний run по `run_id`, не 404 когда job уже
  `completed`.

### Technical Debt

- HTTP ingest (`materialize_policy`) не пишет `ingestion_states_by_note`;
  статус job — только `ingestion_runs`.
- Старые `query_logs` строки до `d5e1a7c3b9f2` сохранили застывший
  `created_at`; новые INSERT — живое время.

## Retrospective

### What Went Well

- Один FastAPI-процесс закрыл и search, и ingest без Celery.
- Owner смог прогнать ingest/`current` без копирования `run_id` после UX-правки.

### What Was Difficult

- Bind mount: корень должен быть `ML_NLP` (дети DLS1/DLS2), не весь vault.
- PowerShell ломает JSON в `-d "{\"query\":...}"`; нужен файл или `--data-raw "{}"`.
- `server_default="now()"` в Alembic запек константу timestamptz.

### What We Will Change

- Compose `--env-file .env` и путь vault проверять до первого HTTP ingest.
- Для DateTime defaults в миграциях использовать `sa.text("now()")`.

### Backlog Updates

- Перенести: bounded asyncio — после профилирования, не в этом спринте.
- Изменить приоритет: нет.
- Не в этом спринте: per-note audit на HTTP `--to-pg` path.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён (owner merge PR [#54](https://github.com/DaniilJechev/obsidian-rag-lab/pull/54), `c664243`; GitHub review records на PR пустые).
- [x] Retrospective заполнена.
- [x] Commit/PR/merge implementation выполнены; closeout PR следует.
- [x] Backlog обновлён (`API-002` → done).
- [x] Следующий sprint выбран или запланирован. *(не планировался в этом closeout; Phase 8 закрыта, Phase 9 / `LLM-001` — только после phase gate)*

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-24`
