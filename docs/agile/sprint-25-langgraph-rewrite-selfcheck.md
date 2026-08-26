# Sprint 25 — LangGraph rewrite, self-check, observability

> Статус: `planned`
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

- [ ] Light classify (rule или маленький LLM-call): rag_qa vs early refuse
      (не XGBoost).
- [ ] Node rewrite на conditional edge.
- [ ] Node self-check после generate; жёсткий max retries = 1
      (rewrite → retrieve).
- [ ] Structured trace в payload/logs (sequence + reasons).
- [ ] Тесты на ветки графа; обновить этот документ.
- [ ] При closeout фазы: `GRAPH-001` → done в backlog.

## Out of Scope

- Rerank (`ML-001` / Phase 12), cache (Phase 13).
- Multi-turn session memory, Telegram, vLLM.
- Бесконечные agent loops; обязательный полный bake-off Phase 10 заново.

## Expected Artifacts

- `docs/agile/sprint-25-langgraph-rewrite-selfcheck.md` — этот документ.
- Расширение графа Sprint 24: classify / rewrite / self-check nodes.
- Тесты conditional edges и retry cap.
- Trace-поля, совместимые с отладкой (и опционально с MLflow позже).

## Acceptance Criteria

- [ ] Хотя бы один controlled retry path покрыт тестом.
- [ ] Self-check не может зациклиться (max retries enforced).
- [ ] Trace воспроизводим в unit-тестах.
- [ ] CI / Ruff / pytest зелёные; vault / secrets ok.
- [ ] Ограничения (latency/cost) записаны здесь.

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

- **Жёсткая зависимость:** Sprint 24 merged в `main`.
- Доп. LLM-вызовы (rewrite/check) ↑ latency/cost — держать max retries = 1.
- Не раздуть Phase 11 в rerank/cache.

## Estimate

12–18 часов.

## Proposed branch

`sprint/25-langgraph-rewrite-selfcheck`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-26 | Planning | Документ создан; Issue [#65](https://github.com/DaniilJechev/obsidian-rag-lab/issues/65); ждёт merge Sprint 24 |

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

- Планирование Sprint 25 зафиксировано.

### Not Completed

- Implementation (после Sprint 24).

### Changed Decisions

- —

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
