# Sprint 29 — Token budget + dedup eval

> Статус: `planned`
>
> Ветка: `sprint/29-token-budget-eval`
>
> Связанная фаза roadmap: `Фаза 13`
>
> Backlog: `CACHE-002`
>
> GitHub: [Issue #77](https://github.com/DaniilJechev/obsidian-rag-lab/issues/77),
> [Milestone Phase 13](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/13)

## Sprint Goal

Dedup retrieved chunks и ablation `max_context_tokens`; MLflow фиксирует
**tokens/query, latency, spot RAGAS**; в sprint-документе зафиксирован
**recommended default budget** с trade-offs.

## Why

После semantic cache (Sprint 28) следующий рычаг cost/latency — сколько контекста
пакуем в промпт. Без dedup один note может занять budget дублями; без ablation
default `1800` tokens остаётся необоснованным.

Eval в этом спринте — cache **выключен**, чтобы изолировать эффект packing.

## Scope

- [ ] Dedup в `llm/packing.py` (по `note_path` или stable chunk identity)
- [ ] Token budget config + логирование `prompt_tokens` в generate trace / API
- [ ] Ablation grid **800 / 1200 / 1800** на gold subset
- [ ] MLflow experiment `phase-13-token-budget-eval`
- [ ] CLI `--max-context-tokens` для `rag-cli eval` / generate path
- [ ] Tests: dedup reduces duplicate paths; budget caps packed chunks
- [ ] Sprint doc: recommended default + rationale after live eval

## Out of Scope

- Semantic cache changes (default off; eval runs with cache off)
- Session memory / multi-turn history (Phase 13.3+)
- Full 50-q RAGAS regression (spot-check subset)
- Router tiny/big model (roadmap 13.3)

## Expected Artifacts

- `docs/agile/sprint-29-token-budget-eval.md` — этот документ
- Updates to `llm/packing.py`, `llm/settings.py`, eval CLI
- MLflow runs in `phase-13-token-budget-eval`

## Acceptance Criteria

- [ ] Dedup reduces duplicate note paths in packed context
- [ ] Lower budget → lower mean `prompt_tokens` (MLflow)
- [ ] Sprint doc recommends default with trade-offs
- [ ] pytest + ruff green; vault / secrets ok

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Sprint 28 merged on `main` (`1a3708a`); LangGraph generate path stable
- `pack_chunks` uses char/4 token estimate — consistent ablation, not exact tokenizer
- **Quality vs cost:** lower budget may hurt RAGAS on hard questions
- Eval requires Docker API + OpenRouter + MLflow (same stack as Sprint 28)

## Estimate

12–18 часов.

## Proposed branch

`sprint/29-token-budget-eval`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-28 | Sprint 28 closeout + planning | Issue [#77](https://github.com/DaniilJechev/obsidian-rag-lab/issues/77); branch `sprint/29-token-budget-eval` |

## Validation Evidence

### Commands

```text
uv run pytest -q
uv run ruff check .
# TBD after implementation:
uv run rag-cli eval ... --max-context-tokens 800
```

### Test and Lint Results

- Tests: `{{TBD}}`
- Lint: `{{TBD}}`
- CI: `{{TBD}}`

## Review

### Completed

- {{TBD}}

### Not Completed

- {{TBD}}

## Retrospective

### What Went Well

- {{TBD}}

### What Was Difficult

- {{TBD}}

## Completion

- [ ] Definition of Done проверен.

**Итоговый статус:** `planned`

**Дата завершения:** `{{TBD}}`
