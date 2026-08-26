# Sprint 24 — LangGraph retrieve→generate/refuse

> Статус: `in-progress` (implementation done; PR/closeout ещё нет)
>
> Ветка: `sprint/24-langgraph-rag-workflow`
>
> Связанная фаза roadmap: `Фаза 11`
>
> Backlog: `GRAPH-001`
>
> GitHub: [Issue #64](https://github.com/DaniilJechev/obsidian-rag-lab/issues/64),
> [Milestone Phase 11](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/11)

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

## Out of Scope

- Rewrite, self-check, classify ML (Sprint 25).
- Rerank (`ML-001` / Phase 12), cache / token budget (Phase 13).
- Смена gold, judge, bake-off моделей.
- Telegram, vLLM, session memory.

## Expected Artifacts

- `docs/agile/sprint-24-langgraph-rag-workflow.md` — этот документ.
- Пакет `src/rag_based_on_obsidian/lang_graph/` — state, workflow, compile
  (имя `lang_graph`, не `graph`: на Windows/Cursor путь `graph` коллидирует).
- Wiring: `llm/pipeline.run_rag_generate` → `run_generate_graph`; optional
  `graph_path` в `GenerateResponse`.
- Тесты: `tests/graph/test_workflow.py` + обновлённый `tests/llm/test_pipeline.py`.

## Acceptance Criteria

- [x] Граф выполняет retrieve→gate→generate/refuse; path виден в ответе
      (`graph_path`).
- [x] Слабый контекст → refuse без hallucinated answer (семантика
      `should_refuse`).
- [x] HTTP JSON `/generate` совместим с eval-клиентом (`rag-cli ragas`):
      новые поля optional; клиент читает через `.get`.
- [x] CI-локально: Ruff/pytest зелёные без `OPENROUTER_API_KEY`.
- [x] Vault / secrets не тронуты; ограничения записаны здесь.

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

- `uv add langgraph` только владелец (manual uv policy) — сделано до implementation.
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
| 2026-08-26 | Implementation | Пакет `lang_graph/`: retrieve→gate→generate\|refuse; facade `run_rag_generate`; `graph_path` в API schema |
| 2026-08-26 | Studio/LangSmith deps | `langgraph-cli[inmem]` (dev), `langsmith`; `langgraph.json` + `studio.py` stub entrypoint |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run langgraph dev --allow-blocking   # live Studio (optional)
```

### Test and Lint Results

- Tests: `230 passed, 1 skipped, 18 deselected` (exit 0)
- Lint: `uv run ruff check .` — All checks passed (after import fix)
- CI: pending after push/PR
- Studio live: retrieve→gate→generate with OpenRouter (`openai/gpt-4o-mini`); live needs `--allow-blocking` due to sync import of transformers in Agent Server

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Graph answer path | retrieve→gate→generate | unit + Studio live |
| Graph refuse path | retrieve→gate→refuse | unit mock |
| Studio live model | openai/gpt-4o-mini | HyDE query, ~12s latency |

## Review

### Completed

- Планирование Sprint 24 зафиксировано.
- LangGraph каркас wired в generate path.
- Path наблюдаем через `graph_path`.

### Not Completed

- Push / implementation PR / remote CI.
- User confirmation / closeout.
- Sprint 25 (rewrite/self-check).

### Changed Decisions

- Phase 11 = два спринта (24 каркас, 25 прокачка); rerank/cache не в фазе.
- Пакет назван `lang_graph`, не `graph` (path collision).

### Technical Debt

- Compile graph per request in `run_generate_graph` (простая корректность;
  при latency-профиле можно кэшировать compiled app по config fingerprint).

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `in-progress` (implementation complete locally)

**Дата завершения:** —
