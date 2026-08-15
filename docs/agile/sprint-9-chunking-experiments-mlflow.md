# Sprint 9 — Chunking Experiments and MLflow Baseline

> Статус: `implementation-in-progress`
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

- [ ] Зафиксировать experiment protocol: полный allowlisted corpus `DLS1 + DLS2`,
  deterministic ordering, parser/chunking versions, Git commit и критерии
  baseline.
- [ ] Определить typed experiment/result contracts: config identity, run
  identity, `chunking_version`, metric schema и output manifest.
- [ ] Подготовить YAML candidate policies `256`, `512` и `1024` через
  deterministic `estimated_token_count`.
- [ ] Зафиксировать в каждой YAML separators, selective-overlap policy,
  structural-block preservation rules и `chunking_version`.
- [ ] Реализовать deterministic experiment runner поверх `ChunkingPolicy` и
  `chunk_section_tree`.
- [ ] Собрать metrics: chunk count, median/mean/p95 length, rate of chunks
  strictly below 25% of the configured token budget, explicit short-chunk
  threshold, oversized-section count, overlap usage, boundary violations,
  duplicate hashes, metadata completeness, storage size и generation latency.
- [ ] Сгенерировать JSON summary, CSV comparison data, Markdown report и
  YAML/config snapshots в `artifacts/chunking/<policy-name>/`; визуальное
  сравнение выполнять через MLflow UI.
- [ ] Логировать каждый run в локальный MLflow: parameters, metrics, tags,
  Git commit, config snapshot и artifacts.
- [ ] Подключить локальный MLflow UI к tracking location, открыть его в
  браузере и проверить отображение runs, параметров, metrics и artifacts для
  всех candidate policies.
- [ ] Добавить reproducibility tests для config, deterministic rerun, metrics,
  artifacts и selective overlap.
- [ ] Выполнить controlled matrix: `256/512/1024` с no-overlap baseline и
  selective overlap только для oversized text sections.
- [ ] Сравнить runs в MLflow UI, выбрать baseline по
  нескольким заранее объявленным критериям.
- [ ] Зафиксировать versioned `chunk → embedding` handoff для Phase 4.

## Out of Scope

- Semantic splitting до появления embeddings.
- Retrieval precision/recall, MRR, nDCG и gold eval set — Phase 7.
- Сравнение embedding-моделей — Phase 4.
- Qdrant, BM25/RRF, reranking, LLM и LangGraph.
- Production MLflow tracking server и MLOps hardening — поздние фазы.
- TensorBoard, pyplot и отдельный HTML visualization stack; для этого sprint
  достаточно MLflow UI и machine-readable report artifacts.
- Изменение исходного vault.

## Expected Artifacts

- `configs/chunking/*.yaml` — candidate experiment policies.
- `src/rag_based_on_obsidian/chunking/experiments.py` — experiment contracts,
  runner, metrics и MLflow boundary.
- `tests/test_chunking_experiments.py` — config/metric reproducibility tests.
- `artifacts/chunking/<policy-name>/` — JSON, CSV, Markdown reports и config
  snapshots для каждого candidate run.
- `mlruns/` или согласованный local MLflow tracking location — только если
  tracking storage не включён в Git.
- Локальный MLflow UI — визуальное сравнение runs `256/512/1024`, overlap
  policies, metrics и artifacts.
- `docs/architecture/phase-3-chunking.md` — выбранный baseline и handoff contract.

## Acceptance Criteria

- [ ] Каждый experiment run однозначно связан с YAML config и chunking version.
- [ ] Повторный запуск той же конфигурации даёт сопоставимые deterministic metrics.
- [ ] MLflow содержит параметры, метрики и artifacts фактически выполненных runs.
- [ ] Локальный MLflow UI запускается с согласованным tracking location и
  показывает все фактически выполненные runs без потери parameters, metrics и
  artifacts.
- [ ] Reports позволяют сравнить кандидатов без чтения внутреннего кода.
- [ ] Отдельно видны oversized sections и влияние selective overlap.
- [ ] Boundary violations и metadata completeness измеряются, а не оцениваются субъективно.
- [ ] Baseline выбран по заранее объявленным критериям, а не по одному показателю.
- [ ] MLflow UI показывает сравнение runs по размерам и overlap policy;
  JSON/CSV/Markdown artifacts сохраняют воспроизводимые результаты без
  обязательного plotting stack.
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
| 2026-08-14 | Planning refinement | Ordered protocol, runner, metrics, MLflow UI and visualization artifacts defined; implementation not started |
| 2026-08-14 | Implementation items 1–8 | Added versioned YAML candidates, experiment contracts, deterministic runner, metric collector, per-policy JSON/CSV/Markdown artifacts under `artifacts/chunking/`, MLflow adapter and focused tests |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest tests/test_chunking_experiments.py -q
uv run pytest -q
```

### Test and Lint Results

- Tests: `4 passed` (focused Sprint 9 tests)
- Tests: `58 passed, 1 skipped, 15 deselected` (full suite)
- Lint: `All checks passed` (`uv run ruff check .`)
- CI: `не запускался`

### Metrics

До запуска не фиксируются значения chunk count, length percentiles, rates,
latency или storage. Sprint должен сохранить фактические значения и контекст
каждого run в MLflow и generated reports.

## Review

### Completed

- Определены experiment matrix, MLflow scope, metrics и baseline handoff.
- Уточнено, что runs сравниваются как independent policies, а не как training
  epochs: `chunk_size`, overlap policy и optional repeat/iteration являются
  параметрами сравнения.
- MLflow выбран основным tracking/UI; JSON/CSV artifacts используются для
  воспроизводимых данных, Markdown report — для review.

### Not Completed

- Full-corpus YAML runs, local MLflow UI verification, candidate comparison и
  baseline selection ещё не выполнялись.

### Changed Decisions

- MLflow tracking начинается в Phase 3, а не откладывается целиком до Phase 15.

### Technical Debt

- Retrieval-based selection criteria нельзя закрыть до появления embeddings и gold eval set.
- TensorBoard не добавляется в baseline stack; при необходимости его можно
  рассмотреть позднее для training-oriented задач.

## Retrospective

### What Went Well

- Scope привязан к CHUNK-002 и разделён на protocol, contracts, runner, metrics,
  tracking, visualization, tests и baseline handoff.

### What Was Difficult

- Chunking experiments не имеют естественной оси training epochs; сравнение
  нужно строить по independent runs и policies.

### What We Will Change

- Сначала зафиксировать protocol и metric schema, затем писать runner и только
  после этого запускать полный корпус.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [x] Следующий sprint выбран или запланирован: Sprint 9 planned; implementation
  ещё не начата.

**Итоговый статус:** `implementation-in-progress`

**Дата завершения:** `не завершён`
