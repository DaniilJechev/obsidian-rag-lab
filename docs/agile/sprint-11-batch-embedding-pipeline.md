# Sprint 11 — Batch Embedding Pipeline and Temporary Artifacts

> Статус: `ready-for-closeout`
>
> Ветка: `sprint/11-batch-embedding-pipeline`
>
> Связанная фаза roadmap: `Фаза 4`
>
> Backlog: `EMB-002`

## Sprint Goal

Построить воспроизводимый batch pipeline, который читает versioned chunks из
PostgreSQL, создаёт embeddings и сохраняет временные JSON artifacts с manifest.

## Why

Embedding всего корпуса по одному chunk неэффективен и плохо восстанавливается
после ошибки. Batch processing нужен для throughput, memory control, progress,
retry и измеримого success rate.

JSON в этом sprint — только временный transport/debug handoff. Он не является
production vector store и будет удалён после Qdrant handoff в Phase 5.

## Scope

- [x] Читать chunks из PostgreSQL по явной `chunking_version`.
- [x] Реализовать stable ordering и configurable batch size.
- [x] Добавить progress reporting, bounded database batches и recoverable retries.
- [x] Валидировать dimensions, NaN/Inf и normalization каждого batch.
- [x] Сохранять temporary `embeddings.json`, `manifest.json` и `metrics.json`.
- [x] Логировать model, chunking и processing metadata в MLflow.
- [x] Покрыть pipeline deterministic, failure и rerun tests.

## Out of Scope

- Qdrant collection и similarity search.
- Удаление temporary JSON до Phase 5 handoff.
- BM25/RRF, FastAPI, LLM и golden-question retrieval evaluation.
- Semantic selection лучшей chunking policy.

## Expected Artifacts

- `src/rag_based_on_obsidian/embeddings/pipeline.py` — batch orchestration.
- `configs/embeddings/` — batch/retry/device configuration.
- `artifacts/embeddings/<embedding-version>/` — temporary JSON artifacts.
- `tests/embeddings/` — batch, validation and failure tests.
- MLflow run с throughput, duration, batch size и failure metrics.

## Acceptance Criteria

- [x] Весь выбранный набор chunks обрабатывается batch pipeline.
- [x] Каждый vector однозначно сопоставлен с `chunk_id`.
- [x] Все vectors имеют одинаковую dimension.
- [x] Failed embeddings видны отдельно и не маскируются.
- [x] Повторный запуск контролируем и version-aware.
- [x] Manifest содержит model, version, dimension, chunking version и count.
- [x] Temporary JSON можно использовать как вход для будущего Qdrant loader.

## Definition of Done

- [x] Scope выполнен или явно перенесён в backlog.
- [x] Acceptance Criteria проверены.
- [x] Tests проходят.
- [x] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлены в remote.
- [x] Vault не изменён и секреты не добавлены.
- [x] Документация и конфигурация обновлены.
- [x] Пользователь подтвердил завершение implementation run.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| planned | Sprint created | Implementation not started |
| 2026-08-16 | Batch pipeline implementation | PostgreSQL streaming reader, retries, validation, JSON artifacts and MLflow adapter implemented |
| 2026-08-16 | Local validation | Ruff passed; 80 passed, 1 skipped, 17 deselected |
| 2026-08-16 | Full embedding run | 733 chunks processed; 733 vectors succeeded; 0 failures; 23 batches |
| 2026-08-16 | Rerun verification | User confirmed repeated runs produce the same result and no duplicate artifact entries |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run rag-cli embed --model-config configs/embeddings/embedder_model_config_e5_small.yaml --batch-config configs/embeddings/pipeline_embedder_config.yaml
```

### Test and Lint Results

- Tests: `PASS — 80 passed, 1 skipped, 17 deselected`
- Lint: `PASS — uv run ruff check .`
- Full embedding run: `PASS — 733/733 embeddings, 0 failures`
- Rerun: `PASS — user confirmed identical idempotent result`
- MLflow: `PASS — metrics observed in MLflow UI; run ID was not captured in the provided output`
- CI: `NOT VERIFIED — closeout branch not pushed yet`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| chunks_total | 733 | Selected `sprint9-policy-512-v2` PostgreSQL generation |
| embeddings_succeeded | 733 | Full selected dataset run |
| embeddings_failed | 0 | Full selected dataset run |
| batches_total | 23 | Pipeline batch size 32 |
| attempts_total | 23 | No retries required |
| duration_seconds | 229.3164251 | User-observed MLflow run |
| embeddings_per_second | 3.196456 | User-observed MLflow run |
| failure_rate | 0 | User-observed MLflow run |

## Review

### Not Completed

- CI, PR review and merge are not completed yet.
- Sprint closeout and remote Issue update are not completed yet.

### Technical Debt

- Full audit integration with `index_versions`, `ingestion_runs` и
  `ingestion_states` remains a separate hardening item.
- Successful vectors are accumulated in memory until final JSON write; streaming
  artifact writing is a future memory-hardening improvement.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран.

**Итоговый статус:** `ready-for-closeout`

**Дата завершения:** `implementation complete; remote closeout pending`
