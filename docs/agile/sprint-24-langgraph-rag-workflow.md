# Sprint 24 — LangGraph retrieve→generate/refuse

> Статус: `planned`
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

- [ ] Добавить dependency `langgraph` (владелец: `uv add` вручную).
- [ ] Typed graph state: query, method, top_k, chunks, packed, answer,
      refused, path/trace.
- [ ] Nodes: `retrieve` → `gate` → `generate` | `refuse` (reuse packing,
      parser, OpenRouter из `llm/`).
- [ ] Wire API/runtime: `/generate` вызывает граф (thin facade над старым
      pipeline ok).
- [ ] Unit/smoke без live OpenRouter в CI.
- [ ] Этот sprint-документ обновлять по ходу execution.

## Out of Scope

- Rewrite, self-check, classify ML (Sprint 25).
- Rerank (`ML-001` / Phase 12), cache / token budget (Phase 13).
- Смена gold, judge, bake-off моделей.
- Telegram, vLLM, session memory.

## Expected Artifacts

- `docs/agile/sprint-24-langgraph-rag-workflow.md` — этот документ.
- Пакет графа (например `src/rag_based_on_obsidian/graph/`) — state, nodes,
  compile.
- Wiring в `api/runtime` / generate path.
- Тесты графа с моками (без live ключа).

## Acceptance Criteria

- [ ] Граф выполняет retrieve→gate→generate/refuse; path виден в ответе или
      логах.
- [ ] Слабый контекст → refuse без hallucinated answer (семантика
      `should_refuse`).
- [ ] HTTP JSON `/generate` совместим с eval-клиентом (`rag-cli ragas`).
- [ ] CI зелёный без `OPENROUTER_API_KEY`; Ruff/pytest проходят.
- [ ] Vault / secrets не тронуты; ограничения записаны здесь.

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

- `uv add langgraph` только владелец (manual uv policy).
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

## Validation Evidence

### Commands

```text
(заполняется при execution)
```

### Test and Lint Results

- Tests: —
- Lint: —
- CI: —

### Metrics

| Metric | Value | Context |
|---|---:|---|
| — | — | — |

## Review

### Completed

- Планирование Sprint 24 зафиксировано.

### Not Completed

- Implementation.

### Changed Decisions

- Phase 11 = два спринта (24 каркас, 25 прокачка); rerank/cache не в фазе.

### Technical Debt

- —

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** —
