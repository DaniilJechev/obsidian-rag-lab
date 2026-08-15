# Sprint 11 — Batch Embedding Pipeline and Temporary Artifacts

> Статус: `planned`
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

- [ ] Читать chunks из PostgreSQL по явной `chunking_version`.
- [ ] Реализовать stable ordering и configurable batch size.
- [ ] Добавить progress reporting, bounded memory и recoverable retries.
- [ ] Валидировать dimensions, NaN/Inf и normalization каждого batch.
- [ ] Сохранять temporary `embeddings.json`, `manifest.json` и `metrics.json`.
- [ ] Логировать model, chunking и processing metadata в MLflow.
- [ ] Покрыть pipeline deterministic, failure и rerun tests.

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

- [ ] Весь выбранный набор chunks обрабатывается batch pipeline.
- [ ] Каждый vector однозначно сопоставлен с `chunk_id`.
- [ ] Все vectors имеют одинаковую dimension.
- [ ] Failed embeddings видны отдельно и не маскируются.
- [ ] Повторный запуск контролируем и version-aware.
- [ ] Manifest содержит model, version, dimension, chunking version и count.
- [ ] Temporary JSON можно использовать как вход для будущего Qdrant loader.

## Definition of Done

- [ ] Scope выполнен или явно перенесён в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Tests проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлены в remote.
- [ ] Vault не изменён и секреты не добавлены.
- [ ] Документация и конфигурация обновлены.
- [ ] Пользователь подтвердил завершение sprint.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| planned | Sprint created | Implementation not started |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest tests/embeddings -q
```

### Test and Lint Results

- Tests: `NOT VERIFIED — sprint not started`
- Lint: `NOT VERIFIED — sprint not started`
- CI: `NOT VERIFIED — no implementation push`

### Metrics

Будут измеряться после реализации: processed chunks, success rate, failed
embeddings, batch throughput, total duration, memory failures и artifact size.

## Review

### Not Completed

- Batch pipeline and temporary artifact contract are not implemented.

### Technical Debt

- Full audit integration with `index_versions`, `ingestion_runs` и
  `ingestion_states` remains a separate hardening item.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
