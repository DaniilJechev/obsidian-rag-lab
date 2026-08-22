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

- [x] Повторный `POST /search` не перезагружает embedding-модель.
- [x] CLI `rag-cli search` с хоста не сломан.
- [x] Compose-сервис `api` отвечает на `GET /health` с хоста `:8000`.
- [x] Клиент получает JSON и HTTP-коды, не типы Qdrant/SQL.
- [x] Тесты и Ruff зелёные; vault не изменён.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Реализация только на `sprint/19-fastapi-retriever-service`, merge в `main`
  через PR. Planning-файлы живут на `main`.
- Внутри контейнера `localhost` — сам `api`; Postgres/Qdrant — имена сервисов.
- Образ с torch/transformers тяжёлый; без volume HF-кэша каждый `up` качает e5.
- Linux-wheel `torch` с PyPI тянет CUDA/`nvidia-*` (~2 GB). Проект CPU-only:
  lock использует индекс `pytorch-cpu` (`torch==2.13.0+cpu`).
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
| 2026-08-22 | CPU torch lock | `uv lock`: без CUDA/`nvidia-*`; `torch==2.13.0+cpu`. Dockerfile: `UV_HTTP_TIMEOUT=600`. |
| 2026-08-22 | Live compose | `docker-api-1` healthy; e5 CPU once; `/health` 200; `/search` hybrid 5 hits (`chunk_id=2046`); empty query 422; host CLI 5 hits. |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run pytest tests/api -q
```

Live (владелец, 2026-08-22):

```text
docker compose --env-file .env -f docker/compose.yml up -d --build api
docker compose --env-file .env -f docker/compose.yml ps
Invoke-RestMethod http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/search  {"query":"…","method":"hybrid","top_k":5}
uv run rag-cli search hybrid --query "что такое RoPE"
```

`ps`: `api`, `postgres`, `qdrant` — `healthy`; порт `8000`. Логи: e5
`intfloat/multilingual-e5-small` device=cpu один раз, затем только
`GET /health` 200 от Docker healthcheck. HTTP search вернул 5 hits
(`chunk_id=2046`, RoPE). Пустой query → 422. Host CLI: 5 hits, Qdrant
`localhost:6333`; CLI заново грузил e5 (~9 s), контейнер — нет.

PowerShell `ConvertTo-Json` портит кириллицу в теле POST; латиница `RoPE`
в query достаточна для hit. Это клиент, не баг API.

### Test and Lint Results

- Tests: `uv run pytest -q` — 147 passed, 1 skipped, 18 deselected, 1 Starlette/httpx deprecation warning. Первый прогон: 39 ERROR на setup из-за WinError 32 (lock `.pytest-tmp/.../mlflow.db`); повтор — exit 0.
- Lint: `uv run ruff check .` — All checks passed
- CI: ждать required checks на PR (ещё не создан на момент этой записи)

### Metrics

| Metric | Value | Context |
|---|---:|---|
| HTTP `/search` hits | 5 | hybrid, top_k=5, host `:8000` |
| Host CLI hits | 5 | `rag-cli search hybrid`, same RoPE note |

## Review

### Completed

- Планирование Sprint 19.
- FastAPI `/health` + `/search`, TestClient, compose `api`.
- CPU-torch lock так, чтобы Linux-образ не тянул CUDA.
- Live compose: health 200, search 5 hits, CLI с хоста жив.

### Not Completed

- PR review, CI на PR, merge в `main`, closeout Issue [#49](https://github.com/DaniilJechev/obsidian-rag-lab/issues/49).

### Changed Decisions

- API в Docker compose в этом спринте (не только host uvicorn).
- `torch` для Linux/Docker — CPU index, не default PyPI CUDA wheel.

### Technical Debt

- Образ API всё ещё ставит mlflow/matplotlib/seaborn (весь `pyproject`), не extra `api`.
- Docker Hub/PyPI с узкого канала: первый `--build` долгий даже с CPU-torch.
- HF Hub unauthenticated warning в логах контейнера.

## Retrospective

### What Went Well

- Контракт HTTP на FakeRuntime позволил закрыть тесты без Docker.
- Live hit `/search` совпал с CLI (тот же `chunk_id` RoPE).

### What Was Difficult

- Первый `FROM python` и CUDA-torch с PyPI на ~0.1 MB/s; сборка упала по `UV_HTTP_TIMEOUT`.

### What We Will Change

- Для Linux-образов сразу pin CPU-torch, не ждать OOM/timeout на `nvidia-*`.

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

**Итоговый статус:** `in-progress` (ожидает PR review / merge)

**Дата завершения:** —
