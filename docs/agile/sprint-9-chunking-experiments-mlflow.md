# Sprint 9 — Chunking Experiments and MLflow Baseline

> Статус: `planned`
>
> Ветка реализации: `sprint/9-chunking-experiments-mlflow`
>
> Связанная фаза roadmap: `Фаза 3`
>
> Зависимость: Sprint 8 — Versioned Recursive Structural Chunking
>
> Backlog: `CHUNK-002`
>
> GitHub: [Issue #21](https://github.com/DaniilJechev/obsidian-rag-lab/issues/21)
> · [Milestone Phase 3 — LangChain-first Chunking](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/5)

## Sprint Goal

Провести воспроизводимые YAML-driven эксперименты с chunking policies, записать
их параметры, метрики и artifacts в MLflow и выбрать документированный baseline
для Phase 4 embeddings.

## Why

Размер chunk нельзя выбирать только по интуиции или одной красивой note.
Эксперимент должен показать компромисс между сохранением контекста, количеством
chunks, короткими фрагментами, storage cost и временем генерации. MLflow вводится
уже здесь, чтобы результаты разных YAML-конфигураций не терялись и были
воспроизводимыми.

На этом этапе оцениваются структурные свойства chunking. Retrieval quality,
embeddings и RAGAS появятся позже, когда будет готов векторный и evaluation
слой.

## Scope

- [ ] Подготовить YAML-конфигурации candidate policies с budgets `256`, `512` и
  `1024` через deterministic token proxy/estimated token count.
- [ ] Зафиксировать separators, overlap policy, block-preservation rules и
  chunking version каждой конфигурации.
- [ ] Запустить каждый candidate на согласованном representative sample или
  полном allowlisted корпусе, выбранном до запуска.
- [ ] Сравнить режимы без overlap и с overlap только для oversized text sections.
- [ ] Логировать в MLflow config parameters, chunk metrics, Git commit/tag и
  generated artifacts.
- [ ] Создать local JSON/CSV/Markdown/PNG reports и сохранить config snapshots.
- [ ] Измерить chunk counts, median/p95 length, short-chunk rate, boundary
  violations, duplicate hashes, storage/latency и metadata completeness.
- [ ] При необходимости сравнить две LangChain splitter policies как controlled
  comparison.
- [ ] Выбрать Phase 4 baseline и зафиксировать versioned `chunk → embedding`
  handoff contract.

## Out of Scope

- Semantic splitting до появления embeddings.
- Retrieval precision/recall, MRR, nDCG и gold eval set — Phase 7.
- Сравнение embedding-моделей — Phase 4.
- Qdrant, BM25/RRF, reranking, LLM и LangGraph.
- Production MLflow tracking server и MLOps hardening — поздние фазы.
- Изменение исходного vault.

## Expected Artifacts

- `configs/chunking/*.yaml` — candidate experiment policies.
- `src/rag_based_on_obsidian/chunking/experiments.py` — orchestration, если
  реализация выделит её в отдельный модуль.
- `tests/test_chunking_experiments.py` — config/metric reproducibility tests.
- `artifacts/chunking/` — JSON, CSV, Markdown, PNG reports и config snapshots.
- `mlruns/` или согласованный local MLflow tracking location — только если
  tracking storage не включён в Git.
- `docs/architecture/phase-3-chunking.md` — выбранный baseline и handoff contract.

## Acceptance Criteria

- [ ] Каждый experiment run однозначно связан с YAML config и chunking version.
- [ ] Повторный запуск той же конфигурации даёт сопоставимые deterministic metrics.
- [ ] MLflow содержит параметры, метрики и artifacts фактически выполненных runs.
- [ ] Reports позволяют сравнить кандидатов без чтения внутреннего кода.
- [ ] Отдельно видны oversized sections и влияние selective overlap.
- [ ] Boundary violations и metadata completeness измеряются, а не оцениваются субъективно.
- [ ] Baseline выбран по заранее объявленным критериям, а не по одному показателю.
- [ ] Phase 4 получает versioned contract с chunk text, metadata и source identity.
- [ ] Generated tracking data и секреты не попадают в Git.

## Definition of Done

- [ ] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Baseline и ограничения записаны в этот sprint-документ и architecture docs.
- [ ] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-13 | Sprint document created from approved Phase 3 plan | Sprint 9 scope defined; experiments not started |

## Validation Evidence

### Commands

```text
Будет заполнено после начала implementation.
```

### Test and Lint Results

- Tests: `не запускались; sprint находится в статусе planned`
- Lint: `не запускался; implementation отсутствует`
- CI: `не запускался`

### Metrics

До запуска не фиксируются значения chunk count, length percentiles, rates,
latency или storage. Sprint должен сохранить фактические значения и контекст
каждого run в MLflow и generated reports.

## Review

### Completed

- Определены experiment matrix, MLflow scope, metrics и baseline handoff.

### Not Completed

- YAML runs, MLflow artifacts, candidate comparison и baseline selection ещё не выполнялись.

### Changed Decisions

- MLflow tracking начинается в Phase 3, а не откладывается целиком до Phase 15.

### Technical Debt

- Retrieval-based selection criteria нельзя закрыть до появления embeddings и gold eval set.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
