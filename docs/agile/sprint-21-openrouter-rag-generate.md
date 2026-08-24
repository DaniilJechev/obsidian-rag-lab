# Sprint 21 — OpenRouter RAG generate

> Статус: `in-progress`
>
> Ветка: `sprint/21-openrouter-rag-generate`
>
> Связанная фаза roadmap: `Фаза 9`
>
> Backlog: `LLM-001`
>
> GitHub: Milestone/Issue ещё не созданы (нужно отдельное разрешение).
> Фазовый план: `.cursor/plans/phase_9_openrouter_rag_810008fc.plan.md`

## Sprint Goal

Тот же FastAPI-процесс после hybrid retrieval отдаёт JSON-ответ LLM:
`answer`, `citations[]`, `confidence`, либо явный отказ, если контекста мало.
Вызов идёт через `LLMProvider` → OpenRouter; ключ не попадает в git.

## Why

Phase 7 измерила retrieval, Phase 8 отдала его по HTTP. Без generate нет
ответа с цитатами и не к чему вешать RAGAS (Phase 10). LangGraph раньше
generate не делается: нечем мерить «до/после».

Сравнение нескольких моделей (roadmap 9.5) в этот спринт **не входит**: без
RAGAS это cost/latency и взгляд «на глаз», не proper evaluation. Bake-off
переносится в Phase 10 / `MLOPS-001`.

## Scope

- [x] Контракт `LLMProvider` (по образцу `EmbeddingProvider`):
      `generate(...)` → текст/JSON + usage (tokens, latency, model id).
- [x] OpenRouter-адаптер на `httpx.AsyncClient`; ключ из env; 401/429/5xx →
      typed errors → HTTP `503`. Ключ не логировать.
- [x] RAG-сборка: hybrid retrieve → token-budget pack → промпт «цитируй
      `[[заметку]]`» → structured JSON. Retrieval не переписываем
      (`RetrieverRuntime.search()`).
- [x] Отказ, если хитов нет или retrieval слишком слабый (порог в YAML, не
      ML-классификатор). Тот же JSON-контракт, `refused: true`, без вызова LLM.
- [x] `POST /generate` на существующем app: `query`, optional `method`/`top_k`;
      `422` / `503` как у `/search`. Search и ingest не блокируются.
- [x] YAML в `configs/llm/openrouter.yaml`: pin `openai/gpt-4o-mini`
      (выбран при старте реализации).
- [x] Тесты с моком OpenRouter (без живого ключа в CI).
- [x] Live smoke владельцем: 1 вопрос на **одной** модели (`openai/gpt-4o-mini`);
      tokens / latency записаны ниже. Cost с дашборда OpenRouter не снимали.
      Это ops-чек, не bake-off.
- [x] Новые зависимости не понадобились (`httpx` / `pydantic` уже были).

## Out of Scope

- RAGAS / Faithfulness / Answer Relevancy (Phase 10 / `MLOPS-001`).
- Bake-off нескольких моделей (бывший roadmap 9.5) — тоже Phase 10.
- LangGraph, rerank, cache, Telegram, vLLM, платные embeddings.
- Расширение `query_logs` под generate (CHECK только `dense|bm25|hybrid`).
- Смена hybrid-default и embedding-модели.
- Реализация на ветке `main`.

## Expected Artifacts

- `src/rag_based_on_obsidian/llm/` — контракт + OpenRouter adapter.
- `configs/llm/` — pin одной модели (имя выбирается при старте реализации).
- `POST /generate` + Pydantic schemas в `src/rag_based_on_obsidian/api/`.
- `tests/llm/` и расширение `tests/api/`.
- Этот sprint-документ (execution log и метрики — только после реализации).

## Acceptance Criteria

- [x] `/generate` возвращает JSON с цитатами на chunk/note, не сырой текст
      провайдера.
- [x] Пустой/слабый контекст → отказ в том же контракте, не `500`
      (юнит-тесты pipeline; live refuse на пустом индексе не гоняли).
- [x] Нет ключа / OpenRouter недоступен → `503`; search/ingest живы
      (live: пустой ключ в контейнере; search 200 на том же процессе).
- [ ] CI зелёный без `OPENROUTER_API_KEY` (ещё не пушили).
- [x] Vault не изменён; секреты не в git.
- [x] Live smoke записан числами из реального вызова одной модели.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены (кроме GitHub CI до push/PR).
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Нужен `OPENROUTER_API_KEY` в локальном `.env` (слот уже в `.env.example`).
  CI в сеть OpenRouter не ходит.
- Модель v1 не зафиксирована в плане; выбираем при старте реализации.
- Compose `api` уже читает `env_file: ../.env`; ключ попадёт в контейнер
  без нового bind, если он есть в `.env`.
- PowerShell ломает JSON в `curl -d`; для live — файл или `--data-raw`.
- GitHub Milestone/Issue ещё нет; PR без `Closes #N`, пока их не создадим.

## Estimate

10–14 часов разработки.

## Proposed branch

`sprint/21-openrouter-rag-generate`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-24 | Planning | Документ создан на `sprint/21-openrouter-rag-generate`; реализация не начата |
| 2026-08-24 | Implementation | `LLMProvider`, OpenRouter adapter, pack/refuse, `POST /generate`; pin `openai/gpt-4o-mini` |
| 2026-08-24 | Live smoke | `POST /generate` RoPE, hybrid, top_k=5; HTTP 200; pin/образ `openai/gpt-4o-mini`; без VPN Cloudflare DME отдавал 403 (`Access denied by security policy`) |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
```

### Test and Lint Results

- Tests: `uv run pytest -q` — **181 passed**, 1 skipped, 18 deselected
  (`not manual`), 1 Starlette/httpx warning, 79.78s, 2026-08-24.
- Lint: `uv run ruff check .` — All checks passed, 2026-08-24.
- CI: не публиковалось.
- Live smoke: 2026-08-24, compose `api` `:8000`, VPN on; query
  «Что такое RoPE в трансформерах?», `method=hybrid`, `top_k=5`.
  HTTP 200, `refused: false`, citations `chunk_id` 4245 и 4246
  (`DLS2/RoPE (Rotary Position Embedding) Математика вращения.md`).
  Пустой body `/generate` → 422; без ключа в контейнере → 503
  `OPENROUTER_API_KEY is not configured`; `/search` на том же JSON → 200.

### Metrics

| Metric | Value | Context |
|---|---:|---|
| HTTP `/generate` | 200 | live, hybrid top_k=5, RoPE |
| `model` | openai/gpt-4o-mini | OpenRouter observed id; image pin, not host `ox-alpha` |
| `latency_ms` | 3640 | adapter wall time (retrieve+pack+chat) |
| `prompt_tokens` | 1958 | OpenRouter usage |
| `generated_tokens` | 165 | OpenRouter `completion_tokens` mapped |
| cost USD | — | дашборд не снимали; только tokens |
| HTTP `/generate` empty body | 422 | query required |
| HTTP `/generate` empty key | 503 | before env recreate |

## Review

### Completed

- Planning: scope 9.1–9.4 + HTTP; bake-off моделей вынесен в Phase 10.
- Implementation, unit tests, local ruff/pytest, live `/generate` smoke.

### Not Completed

- GitHub Milestone/Issue, commit/PR/CI, review, merge, closeout.

### Changed Decisions

- Один спринт на всю Phase 9 (не два). Roadmap 9.5 → Phase 10 / RAGAS.

### Technical Debt

- `query_logs` не покрывает generate.
- 401 и 403 OpenRouter схлопнуты в одно `rejected the API key`; live 403
  был Cloudflare policy (PoP DME), не неверный ключ. Нужен VPN с этой сети.
- Хостовый YAML можно сменить на `:free` / Ox Alpha без `--build` — контейнер
  останется на пине образа.
- Текст DoD Phase 9 в живом roadmap ещё содержит «сравнение моделей»;
  файл roadmap не менялся в этом planning.

## Retrospective

### What Went Well

- —

### What Was Difficult

- —

### What We Will Change

- —

### Backlog Updates

- Добавить: нет (bake-off остаётся внутри `MLOPS-001` / Phase 10).
- Перенести: roadmap 9.5 (сравнение моделей) → Phase 10.
- Изменить приоритет: нет.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `in-progress`

**Дата завершения:** —
