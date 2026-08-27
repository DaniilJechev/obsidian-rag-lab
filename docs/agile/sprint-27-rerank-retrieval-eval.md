# Sprint 27 — Rerank retrieval eval

> Статус: `planned`
>
> Ветка: `sprint/27-rerank-retrieval-eval`
>
> Связанная фаза roadmap: `Фаза 12`
>
> Backlog: `ML-001`
>
> GitHub: [Issue #71](https://github.com/DaniilJechev/obsidian-rag-lab/issues/71),
> [Milestone Phase 12](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/12)

## Sprint Goal

На замороженном Phase 7 gold сравнены **hybrid** и **hybrid+rerank**
(nDCG/MRR) в MLflow; по цифрам принято решение default on/off; `ML-001`
готов к closeout Phase 12.

## Why

Без before/after на том же gold wiring CE — непроверенная гипотеза. Sprint 27
закрывает `ML-001` evidence-based, не на глаз.

## Scope

- [ ] Eval runs: hybrid vs hybrid+rerank на Phase 7 gold (same k).
- [ ] MLflow / sprint-doc table with nDCG/MRR.
- [ ] Decide default rerank flag from evidence.
- [ ] Update this document; prepare `ML-001` → done at phase closeout.

## Out of Scope

- Re-wiring CE (Sprint 26 / Issue #70).
- Embedding model change, cache, generate/RAGAS as primary gate.
- XGBoost classifier.

## Expected Artifacts

- `docs/agile/sprint-27-rerank-retrieval-eval.md` — этот документ.
- MLflow runs (or equivalent logged metrics) for before/after.
- Decision note: default on vs off.

## Acceptance Criteria

- [ ] Before/after metrics recorded on the same gold freeze.
- [ ] Default flag decision written here with rationale.
- [ ] Ruff / pytest green if code touched; vault / secrets ok.
- [ ] `ML-001` ready to mark done at Phase 12 closeout.

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят (если код менялся).
- [ ] Ruff/lint проходит (если код менялся).
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Документация и конфигурация обновлены, если это необходимо.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- **Жёсткая зависимость:** Sprint 26 CE path merged (or available).
- Gold freeze: Sprint 17/18 canon (`phase7_GT_note_level_v0` / sprint-18 doc).
- Live Qdrant + embeddings needed for live eval.

## Estimate

8–14 часов.

## Proposed branch

`sprint/27-rerank-retrieval-eval`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-27 | Planning | Документ создан; Issue #71; Milestone 12 |

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
| — | — | заполняется при execution |

## Review

### Completed

- Планирование Sprint 27 зафиксировано.

### Not Completed

- Evaluation (после Sprint 26).

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
