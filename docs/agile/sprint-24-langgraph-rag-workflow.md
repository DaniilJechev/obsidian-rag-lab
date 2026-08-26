# Sprint 24 — LangGraph retrieve→generate/refuse

> Статус: `done`
>
> Ветка: `sprint/24-langgraph-rag-workflow`
>
> Связанная фаза roadmap: `Фаза 11`
>
> Backlog: `GRAPH-001` (частично: каркас; остаток в Sprint 25)
>
> GitHub: [Issue #64](https://github.com/DaniilJechev/obsidian-rag-lab/issues/64) (closed),
> [PR #66](https://github.com/DaniilJechev/obsidian-rag-lab/pull/66) merged (`11555e2`),
> [Milestone Phase 11](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/11) (open — Sprint 25)

## Sprint Goal

Вопрос проходит **наблюдаемый** LangGraph: hybrid retrieve → context gate →
generate **или** refuse. Поведение ≈ текущий `run_rag_generate`, форма —
граф. `POST /generate` остаётся совместимым со Sprint 21/23.

## Why

Phase 10 дала измеримый generate (ragas 0–1 + bake-off). Дальше по живому
roadmap — оркестрация (LangGraph), не rerank и не cache. Сейчас логика в
одной функции `llm/pipeline.py`; явный граф нужен, чтобы ветки refuse/generate
были читаемы, path трассировался, а Phase 12/13 встраивались узлами, а не
раздуванием pipeline. Sprint 24 — только каркас (без rewrite/self-check).

## Scope

- [x] Добавить dependency `langgraph` (владелец: `uv add` вручную).
- [x] Typed graph state: query, method, top_k, chunks, packed, answer,
      refused, path/trace.
- [x] Nodes: `retrieve` → `gate` → `generate` | `refuse` (reuse packing,
      parser, OpenRouter из `llm/`).
- [x] Wire API/runtime: `/generate` вызывает граф (thin facade над старым
      pipeline ok).
- [x] Unit/smoke без live OpenRouter в CI.
- [x] Этот sprint-документ обновлять по ходу execution.
- [x] Optional: Studio entrypoint + langsmith package (dev tooling).

## Out of Scope

- Rewrite, self-check, classify ML (Sprint 25).
- Rerank (`ML-001` / Phase 12), cache / token budget (Phase 13).
- Смена gold, judge, bake-off моделей.
- Telegram, vLLM, session memory.

## Expected Artifacts

- `docs/agile/sprint-24-langgraph-rag-workflow.md` — этот документ.
- Пакет `src/rag_based_on_obsidian/lang_graph/` — state, workflow, studio.
- Wiring: `llm/pipeline.run_rag_generate` → `run_generate_graph`; `graph_path`
  в `GenerateResponse`.
- Тесты: `tests/graph/`, обновлённый `tests/llm/test_pipeline.py`.
- `langgraph.json` для optional local Studio.

## Acceptance Criteria

- [x] Граф выполняет retrieve→gate→generate/refuse; path виден в ответе
      (`graph_path`).
- [x] Слабый контекст → refuse без hallucinated answer (семантика
      `should_refuse`).
- [x] HTTP JSON `/generate` совместим с eval-клиентом (`rag-cli ragas`).
- [x] CI-локально: Ruff/pytest зелёные без `OPENROUTER_API_KEY`.
- [x] Vault / secrets не тронуты; ограничения записаны здесь.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит, если изменения отправлялись в remote (PR #66).
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [x] Пользователь подтвердил завершение спринта (merge #66 + closeout).

## Dependencies and risks

- `uv add langgraph` только владелец (manual uv policy) — сделано.
- Не сломать контракт `/generate` для live ragas harness.
- Не тащить rewrite/self-check в этот спринт.
- Tech debt Sprint 23: перед любым «до/после» eval — probe `/search` vs
  эталонные packed_paths.

## Estimate

12–18 часов.

## Proposed branch

`sprint/24-langgraph-rag-workflow`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-26 | Planning | Документ создан; Issue [#64](https://github.com/DaniilJechev/obsidian-rag-lab/issues/64); Milestone 11 |
| 2026-08-26 | Pre-impl commit | `c6d4142` docs + `langgraph` dep |
| 2026-08-26 | Implementation | Пакет `lang_graph/`: retrieve→gate→generate\|refuse; facade; `graph_path` |
| 2026-08-26 | Studio/LangSmith | `langgraph-cli[inmem]` (dev), `langsmith`; `langgraph.json` + `studio.py` |
| 2026-08-26 | PR / merge | [PR #66](https://github.com/DaniilJechev/obsidian-rag-lab/pull/66) → `11555e2`; Issue #64 closed |
| 2026-08-26 | Closeout | Этот документ + backlog; Milestone 11 остаётся open (Sprint 25) |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run langgraph dev --allow-blocking   # live Studio (optional)
```

### Test and Lint Results

- Tests: `230 passed, 1 skipped, 18 deselected` (exit 0)
- Lint: `uv run ruff check .` — All checks passed
- CI: PR #66 merged
- Studio live: retrieve→gate→generate with OpenRouter (`openai/gpt-4o-mini`); live needs `--allow-blocking`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Graph answer path | retrieve→gate→generate | unit + Studio live |
| Graph refuse path | retrieve→gate→refuse | unit mock |
| Studio live model | openai/gpt-4o-mini | HyDE query, ~12s latency |

## Review

### Completed

- LangGraph каркас в generate path; `graph_path` в API.
- Optional Studio stub/live entrypoint.
- Issue #64 closed via PR #66.

### Not Completed / carry-over

- Sprint 25: classify, rewrite, self-check, richer trace (`GRAPH-001` остаток).

### Changed Decisions

- Phase 11 = два спринта (24 каркас, 25 прокачка); rerank/cache не в фазе.
- Пакет `lang_graph`, не `graph` (path collision).
- Studio — optional local tooling, не отдельный graph-microservice.

### Technical Debt

- Compile graph per request in `run_generate_graph`.
- Live Studio: `--allow-blocking` из‑за sync import transformers в Agent Server.

## Retrospective

### What went well

- Тонкий facade сохранил контракт `/generate` и eval harness.
- Studio помог визуально подтвердить live path без смены архитектуры API.

### Difficulties

- `graph` vs `lang_graph` path collision на Windows/Cursor.
- Live Studio + blockbuster BlockingError на import runtime.
- Windows `git switch` / `.git/HEAD` иногда permission-locked.

### Changes for next sprint

- Сразу закладывать async-friendly / lazy heavy imports для Studio live.
- Не смешивать Studio tooling с пониманием prod path в онбординге.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.
- [x] Следующий sprint выбран или запланирован (Sprint 25 / Issue #65).

**Итоговый статус:** `done`

**Дата завершения:** 2026-08-26
