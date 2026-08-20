# Sprint 18 — Retrieval Baseline on Frozen Gold

> Статус: `planned`
>
> Ветка: `sprint/18-retrieval-eval-baseline` (ещё не создана)
>
> Связанная фаза roadmap: `Фаза 7`
>
> Backlog: `EVAL-002`
>
> GitHub: [Issue #44](https://github.com/DaniilJechev/obsidian-rag-lab/issues/44),
> [Milestone Phase 7](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/8)

## Sprint Goal

На замороженном note-level gold (`dataset_version=phase7-note-level-v1`)
измерить dense, bm25 и hybrid retrieval, записать nDCG/MRR/Recall/Hit в
MLflow и объявить эти три run каноническим baseline до rerank/cache.

## Why

Sprint 17 даёт набор и формулы. Без live прогона на том же индексе, что
сейчас в Qdrant, нечем сравнивать будущие фазы. Каждый eval run обязан
уйти в MLflow — иначе «улучшение» снова станет анекдотом.

## Scope

- [ ] `EVAL-002` — eval runner: читает `eval_items`, вызывает существующий
  retrieval (dense / bm25 / hybrid), collapse chunks→notes, считает метрики.
- [ ] Три MLflow run на одном `dataset_version` и одном
  `chunking_version` / collection: dense, bm25, hybrid.
- [ ] Per-question artifact (predicted notes, ranks, misses) как MLflow
  artifact.
- [ ] Зафиксировать baseline в этом sprint-документе **только после**
  реального запуска (никаких выдуманных чисел).
- [ ] Experiment tags: phase=7, sprint=18, task=EVAL-002,
  experiment_type=eval; description в `mlflow.note.content`.

## Out of Scope

- FastAPI — Phase 8.
- Generate / RAGAS — Phase 9 / 10.
- Изменение gold после freeze без бампа `dataset_version`.
- Rerank, LangGraph, новая embedding-модель.
- pgvector comparison.
- Смена default retrieval с Qdrant hybrid.

## Expected Artifacts

- `src/rag_based_on_obsidian/eval/` — live runner поверх Sprint 17 harness.
- CLI вроде `rag-cli eval retrieve --method hybrid` (точное имя — при
  implementation).
- MLflow experiment `phase-7-retrieval-eval` с тремя comparable runs.
- Таблица observed metrics в этом документе после запуска.

## Acceptance Criteria

- [ ] Gold v1 заморожен после review Sprint 17.
- [ ] Dense, bm25 и hybrid прогнаны на полном наборе 50 вопросов.
- [ ] Каждому прогону соответствует MLflow run с reproducibility tags.
- [ ] nDCG@5/10, MRR@10, Recall@5/10, Hit@10 записаны из этого запуска.
- [ ] Hybrid не объявляется «лучше» без этих чисел.
- [ ] Vault не изменён.

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

- Зависит от Sprint 17 (таблица, loader, метрики, reviewed gold).
- Cold start e5 в one-shot CLI будет доминировать latency; quality-метрики
  от этого не зависят, operational duration логируем честно.
- Если Qdrant collection и Postgres notes разъехались после смены vault
  root, сначала ingest/embed, потом eval.

## Estimate

8–14 часов после закрытого Sprint 17.

## Proposed branch

`sprint/18-retrieval-eval-baseline`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-20 | Planning | Документ создан; ждать Sprint 17 |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
```

Live eval-команда появится в Sprint 18; `rag-cli search` сам по себе
baseline не считает.

### Test and Lint Results

- Tests: не запускались для этого sprint (планирование)
- Lint: не запускались для этого sprint (планирование)
- CI: нет

### Metrics

| Metric | Value | Context |
|---|---:|---|
| nDCG@5 | — | появится после live run |
| nDCG@10 | — | появится после live run |
| MRR@10 | — | появится после live run |

## Review

### Completed

- Планирование live baseline.

### Not Completed

- Implementation.

### Changed Decisions

- FastAPI сознательно после Phase 7.

### Technical Debt

-

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

**Дата завершения:**
