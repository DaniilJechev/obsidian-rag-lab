# Sprint 25 — LangGraph rewrite, self-check, observability

> Статус: `in-progress` (implementation done locally; PR/closeout ещё нет)
>
> Ветка: `sprint/25-langgraph-rewrite-selfcheck`
>
> Связанная фаза roadmap: `Фаза 11`
>
> Backlog: `GRAPH-001`
>
> GitHub: [Issue #65](https://github.com/DaniilJechev/obsidian-rag-lab/issues/65),
> [Milestone Phase 11](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/11)

## Sprint Goal

На каркасе Sprint 24 граф умеет **лёгкий classify**, **rewrite query** и
**короткий self-check** с максимум одним retry; structured path/trace стабильно
виден для отладки и будущего «до/после» на ragas-judge.

## Why

После Sprint 24 граф уже повторяет линейный RAG. Ценность Phase 11 — условные
рёбра и наблюдаемость без раздувания `pipeline.py`. Rewrite/self-check —
минимальная «прокачка», после которой можно закрывать `GRAPH-001` и Milestone
11, не заходя в rerank/cache.

## Scope

- [x] Light classify (rule): rag_qa vs early refuse (не XGBoost / не LLM).
- [x] Node rewrite на conditional edge после failed self-check.
- [x] Node self-check после generate; жёсткий max retries = 1
      (rewrite → retrieve).
- [x] Structured trace в payload (`graph_trace` + `graph_path`).
- [x] Тесты на ветки графа; обновить этот документ.
- [ ] При closeout фазы: `GRAPH-001` → done в backlog (после merge/closeout).

## Out of Scope

- Rerank (`ML-001` / Phase 12), cache (Phase 13).
- Multi-turn session memory, Telegram, vLLM.
- Бесконечные agent loops; обязательный полный bake-off Phase 10 заново.
- LLM-based classify/rewrite/judge (оставлены rule heuristics для CI/cost).

## Expected Artifacts

- `docs/agile/sprint-25-langgraph-rewrite-selfcheck.md` — этот документ.
- `lang_graph/policies.py` + расширенный `workflow.py` / `state.py`.
- API: optional `graph_trace`, `retry_count`, `rewritten_query`.
- Тесты: policies, retry path, retry cap, classify refuse.

## Acceptance Criteria

- [x] Хотя бы один controlled retry path покрыт тестом.
- [x] Self-check не может зациклиться (max retries enforced).
- [x] Trace воспроизводим в unit-тестах.
- [x] Ruff / pytest зелёные локально; vault / secrets ok.
- [x] Ограничения (latency/cost) записаны здесь.

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

- Sprint 24 merged в `main` (`11555e2` / closeout `32c291d`).
- Rule-based policies: zero extra LLM calls for classify/rewrite/self-check;
  only retrieve+generate (and at most one retry generate) hit OpenRouter.
- Не раздуть Phase 11 в rerank/cache.

## Estimate

12–18 часов.

## Proposed branch

`sprint/25-langgraph-rewrite-selfcheck`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-26 | Planning | Документ создан; Issue [#65](https://github.com/DaniilJechev/obsidian-rag-lab/issues/65) |
| 2026-08-26 | Implementation | classify→retrieve→gate→generate→self_check; rewrite max 1; `graph_trace` |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
```

### Test and Lint Results

- Tests: `236 passed, 1 skipped, 18 deselected` (exit 0)
- Lint: `uv run ruff check .` — All checks passed
- CI: pending push/PR

### Metrics / limits

| Metric | Value | Context |
|---|---:|---|
| Max self-check retries | 1 | hard cap |
| Extra LLM for classify/rewrite/check | 0 | rule heuristics |
| Worst-case generate calls | 2 | initial + one retry |

## Review

### Completed

- Rule classify / rewrite / self-check wired.
- Trace + retry fields on generate payload.

### Not Completed

- Push / PR / closeout / GRAPH-001 → done.

### Changed Decisions

- Classify/rewrite/self-check = rules, not LLM (cost/CI determinism).

### Technical Debt

- Heuristic rewrite may not improve retrieval; measure later with ragas if needed.
- After retry cap, low-confidence answer is still returned (not force-refuse).

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
