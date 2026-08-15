# Sprint 9 — Chunking Experiments and MLflow Baseline

> Статус: `completed`
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

- [x] Зафиксировать experiment protocol: полный allowlisted corpus `DLS1 + DLS2`,
  deterministic ordering, parser/chunking versions, Git commit и критерии
  baseline.
- [x] Определить typed experiment/result contracts: config identity, run
  identity, `chunking_version`, metric schema и output manifest.
- [x] Подготовить YAML candidate policies `256`, `512` и `1024` через
  deterministic `estimated_token_count`.
- [x] Зафиксировать в каждой YAML separators, selective-overlap policy,
  structural-block preservation rules и `chunking_version`.
- [x] Реализовать deterministic experiment runner поверх `ChunkingPolicy` и
  `chunk_section_tree`.
- [x] Собрать metrics: chunk count, median/mean/p95 length, rate of chunks
  strictly below 25% of the configured token budget, explicit short-chunk
  threshold, oversized-section count, overlap usage, boundary violations,
  duplicate hashes, metadata completeness, storage size и generation latency.
- [x] Сгенерировать JSON summary, CSV comparison data, Markdown report и
  YAML/config snapshots в `artifacts/chunking/<policy-name>/`; визуальное
  сравнение выполнять через MLflow UI.
- [x] Логировать каждый run в локальный MLflow: parameters, metrics, tags,
  Git commit, config snapshot и artifacts.
- [x] Подключить локальный MLflow UI к tracking location, открыть его в
  браузере и проверить отображение runs, параметров, metrics и artifacts для
  всех candidate policies.
- [x] Добавить reproducibility tests для config, deterministic rerun, metrics,
  artifacts и selective overlap.
- [x] Выполнить controlled matrix: `256/512/1024` с no-overlap baseline и
  selective overlap только для oversized text sections.
- [x] Сравнить structural properties runs в MLflow UI и сохранить provisional
  candidate set по нескольким заранее объявленным критериям.
- [x] Зафиксировать provisional versioned `chunk → embedding` handoff для Phase 4;
  финальный retrieval baseline переносится до появления embeddings и gold
  questions.

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
- `src/rag_based_on_obsidian/chunking/experiments/` — experiment contracts,
  corpus runner, matrix runner и MLflow boundary.
- `src/rag_based_on_obsidian/chunking/chunking_cli.py` —
  CLI для experiments и полной materialization выбранной policy в PostgreSQL.
- `tests/chunking/experiments/` — config, runner, CLI и MLflow tests.
- `artifacts/chunking/<policy-name>/` — JSON, CSV, Markdown reports и config
  snapshots для каждого candidate run.
- `mlflow.db` — SQLite metadata backend, не включать в Git.
- `artifacts/mlflow/` — MLflow artifact store, не включать в Git.
- Локальный MLflow UI — визуальное сравнение runs `256/512/1024`, overlap
  policies, metrics и artifacts.
- `docs/architecture/phase-3-chunking.md` — выбранный baseline и handoff contract.

## Acceptance Criteria

- [x] Каждый experiment run однозначно связан с YAML config и chunking version.
- [x] Повторный запуск той же конфигурации даёт сопоставимые deterministic metrics.
- [x] MLflow содержит параметры, метрики и artifacts фактически выполненных runs.
- [x] Локальный MLflow UI запускается с согласованным tracking location и
  показывает все фактически выполненные runs без потери parameters, metrics и
  artifacts.
- [x] Reports позволяют сравнить кандидатов без чтения внутреннего кода.
- [x] Отдельно видны oversized sections и влияние selective overlap.
- [x] Boundary violations и metadata completeness измеряются, а не оцениваются субъективно.
- [x] Structural candidate set и критерии сравнения зафиксированы; semantic
  baseline selection явно deferred до Phase 4/7.
- [x] MLflow UI показывает сравнение runs по размерам и overlap policy;
  JSON/CSV/Markdown artifacts сохраняют воспроизводимые результаты без
  обязательного plotting stack.
- [x] Phase 4 получает versioned contract с chunk text, metadata и source identity.
- [x] Generated tracking data и секреты не попадают в Git.

## Definition of Done

- [x] Все задачи Scope выполнены или явно перенесены в backlog.
- [x] Structural Acceptance Criteria проверены; semantic retrieval selection
  явно перенесён в Phase 4/7.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит: PR #26 required check `Lint and test` завершился `SUCCESS`.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Provisional baseline, ограничения и Phase 4 handoff записаны в этот
  sprint-документ и backlog.
- [x] Пользователь подтвердил завершение implementation scope.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-13 | Sprint document created from approved Phase 3 plan | Sprint 9 scope defined; experiments not started |
| 2026-08-14 | Planning refinement | Ordered protocol, runner, metrics, MLflow UI and visualization artifacts defined; implementation not started |
| 2026-08-14 | Implementation items 1–8 | Added versioned YAML candidates, experiment contracts, deterministic runner, metric collector, per-policy JSON/CSV/Markdown artifacts under `artifacts/chunking/`, MLflow adapter and focused tests |
| 2026-08-15 | Experiment package split and orchestration | Moved experiment internals to `chunking/experiments/`, added corpus/matrix runner, SQLite-backed MLflow server contract and `chunking_cli.py`; validation pending environment recovery |
| 2026-08-15 | PostgreSQL chunk materialization | Added `--to-pg`; the command clears `chunks` and rebuilds it atomically from one explicit YAML policy; real-vault run and PostgreSQL checks confirmed by owner |
| 2026-08-15 | PR and merge closeout | PR [#26](https://github.com/DaniilJechev/obsidian-rag-lab/pull/26) merged into `main` as `60259d9`; CI passed; independent review was waived by owner |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest tests/chunking/experiments -q
uv run pytest -q
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root .\artifacts\mlflow --host 127.0.0.1 --port 5000
uv run chunking-cli --vault-root C:\Users\gigachaDick\obsidianNotes --all-policies --tracking-uri http://127.0.0.1:5000
uv run alembic upgrade head
uv run chunking-cli --vault-root C:\Users\gigachaDick\obsidianNotes --policy policy_chunking_512 --to-pg
```

### Test and Lint Results

- Tests: `62 passed, 1 skipped, 15 deselected`
- Focused CLI/config and full suite passed after the CLI move and PostgreSQL
  full-refresh path.
- Lint: `uv run ruff check .` — `All checks passed`
- IDE lints: `no errors`
- CI: `не запускался локально; remote CI не является частью текущего commit/push шага`
- PostgreSQL migration: owner confirmed `uv run alembic upgrade head`
- PostgreSQL materialization: owner confirmed successful real-vault execution,
  row-count, `chunking_version`, stale-row, `note_id`, offset and metadata checks
- Manual PostgreSQL integration test: owner confirmed passed

### Metrics

Фактические per-policy metrics сохраняются в generated reports и MLflow.
PostgreSQL materialization использует одну явно выбранную policy; перед записью
таблица `chunks` полностью очищается, поэтому в базе остаётся только актуальная
generation.

## Review

### Completed

- Определены experiment matrix, MLflow scope, metrics и baseline handoff.
- Уточнено, что runs сравниваются как independent policies, а не как training
  epochs: `chunk_size`, overlap policy и optional repeat/iteration являются
  параметрами сравнения.
- MLflow выбран основным tracking/UI; JSON/CSV artifacts используются для
  воспроизводимых данных, Markdown report — для review.
- PR [#26](https://github.com/DaniilJechev/obsidian-rag-lab/pull/26) merged в
  `main` commit `60259d9`; required CI check passed.

### Review waiver

- Независимое review не проводилось: `reviews = []`.
- Владелец репозитория осознанно выполнил merge без review и отдельно разрешил
  завершить cleanup ветки.
- Это зафиксировано как review waiver, а не как выполненное independent review.

### Not Completed

- Retrieval-based semantic baseline selection отложен до Phase 4/7, когда будут
  embeddings и gold questions.
- Полный audit trail через `index_versions`, `ingestion_runs` и
  `ingestion_states` для нового `--to-pg` path остаётся отдельным production
  hardening item; он не блокирует chunking → PostgreSQL handoff.

### Carry-over

- Финальный retrieval baseline selection переносится в Phase 4/7 вместе с
  embeddings, golden questions и Recall@k/MRR/nDCG evaluation.
- Production audit trail для `index_versions`, `ingestion_runs` и
  `ingestion_states` остаётся отдельным hardening item.

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

- [x] Definition of Done проверен с documented review waiver; implementation,
  structural validation и CI завершены.
- [x] Review waiver зафиксирован; independent review не проводился.
- [x] Retrospective заполнена.
- [x] Commit/push/PR/merge выполнены.
- [x] Backlog обновлён.
- [x] Следующий sprint выбран или запланирован: Phase 4 embeddings/evaluation
  handoff подготовлен.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-15`
