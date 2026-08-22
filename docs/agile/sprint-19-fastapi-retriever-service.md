# Sprint 19 — FastAPI /health, /search, Docker

> Статус: `in-progress`
>
> Ветка: `sprint/19-fastapi-retriever-service`
>
> Связанная фаза roadmap: `Фаза 8`
>
> Backlog: `API-001`
>
> GitHub: [Issue #49](https://github.com/DaniilJechev/obsidian-rag-lab/issues/49),
> [Milestone Phase 8](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/9)

## Sprint Goal

`docker compose up` поднимает Postgres, Qdrant и контейнер `api`; e5 грузится
один раз при старте процесса; `GET /health` и `POST /search` отдают JSON-контракт
без типов Qdrant, тем же retrieval, что `rag-cli search`.

## Why

Phase 7 измерила retrieval. Дальше generate и Telegram должны ходить в HTTP, а
не поднимать CLI на каждый вопрос. Сейчас каждый `rag-cli search` заново грузит
e5 — это главный operational-долг Sprint 15. Долгоживущий FastAPI в compose
закрывает кассу поиска до LLM.

## Scope

- [x] FastAPI-приложение и lifespan: загрузить `EmbeddingProvider` и Qdrant
      client на старте, закрыть на shutdown (паттерн
      `LiveRetrievalSession`, не копия CLI).
- [x] `GET /health` — процесс жив; отдельно: модель загружена, Qdrant reachable.
- [x] `POST /search` — JSON `query`, `method` (`dense` / `bm25` / `hybrid`,
      default **hybrid**), `top_k`; ответ — ranked chunks без объектов Qdrant.
- [x] Timeouts и structured errors: `422` валидация, `503` если модель/Qdrant
      не готовы.
- [x] Тесты `TestClient` с моком retriever (без vault).
- [x] Dockerfile приложения и сервис `api` в `docker/compose.yml`:
      `depends_on` healthy postgres/qdrant, порт 8000, volume для HF-кэша,
      env `postgres` / `qdrant` внутри сети (CLI на хосте с `localhost` не
      ломать).
- [x] Зависимости FastAPI / uvicorn / httpx добавляет владелец через `uv add`
      (assistant эту команду не запускает).

## Out of Scope

- `POST /ingest`, `GET /ingest/{run_id}`, query logs — Sprint 20 / `API-002`.
- OpenRouter, RAGAS, LangGraph, rerank, Telegram.
- Смена product-default hybrid → dense.
- Vault mount в контейнер (для search индекс уже в Qdrant).
- MLflow в compose.
- Реализация на ветке `main`.

## Expected Artifacts

- `src/rag_based_on_obsidian/api/` — app, schemas, `/health`, `/search`.
- `tests/api/` — контракты и ошибки.
- Dockerfile + сервис `api` в `docker/compose.yml`.
- Этот sprint-документ (execution log — только после реализации).

## Acceptance Criteria

- [ ] Повторный `POST /search` не перезагружает embedding-модель.
- [ ] CLI `rag-cli search` с хоста не сломан.
- [ ] Compose-сервис `api` отвечает на `GET /health` с хоста `:8000`.
- [ ] Клиент получает JSON и HTTP-коды, не типы Qdrant/SQL.
- [ ] Тесты и Ruff зелёные; vault не изменён.

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

- Реализация только на `sprint/19-fastapi-retriever-service`, merge в `main`
  через PR. Planning-файлы живут на `main`.
- Внутри контейнера `localhost` — сам `api`; Postgres/Qdrant — имена сервисов.
- Образ с torch/transformers тяжёлый; без volume HF-кэша каждый `up` качает e5.
- `uv add` — ручная команда владельца.

## Estimate

12–16 часов разработки.

## Proposed branch

`sprint/19-fastapi-retriever-service` — не создана этим planning-шагом.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-21 | Planning на `main` | Документ создан; реализация не начата |
| 2026-08-22 | Implementation | FastAPI `/health`+`/search`, runtime с тёплым e5, TestClient, Dockerfile + compose `api` |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run pytest tests/api -q
```

Live `docker compose ... up` / build образа `api` в этой сессии не запускались
(тяжёлый torch-слой; mutate Docker не входил в command policy). Файлы
Dockerfile и compose готовы к ручному `up` владельцем.

### Test and Lint Results

- Tests: `uv run pytest -q` — 147 passed, 1 skipped, 18 deselected, 1 Starlette/httpx deprecation warning
- Lint: `uv run ruff check .` — All checks passed
- CI: не запускался (нет push этой реализации)

### Metrics

| Metric | Value | Context |
|---|---:|---|
| — | — | Нет live-прогонов в planning |

## Review

### Completed

- Планирование Sprint 19.

### Not Completed

- Реализация FastAPI, Docker `api`, тесты.

### Changed Decisions

- API в Docker compose в этом спринте (не только host uvicorn).

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

- Добавить: `API-002` (Sprint 20) — см. backlog.
- Перенести: `/ingest` и query logs в Sprint 20.
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
