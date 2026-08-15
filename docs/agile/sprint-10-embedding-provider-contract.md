# Sprint 10 — EmbeddingProvider and Local CPU Model

> Статус: `planned`
>
> Ветка: `sprint/10-embedding-provider-contract`
>
> Связанная фаза roadmap: `Фаза 4`
>
> Backlog: `EMB-001`

## Sprint Goal

Создать стабильный `EmbeddingProvider` и подключить первую локальную multilingual
embedding-модель для CPU inference на тестовых chunks.

## Why

Phase 3 подготовила versioned chunks, но embedding model нельзя подключать
напрямую к ingestion-коду. Provider boundary позволит менять модели и backend
без переписывания pipeline.

Рекомендуемый учебно-production вариант: `Transformers + PyTorch` на CPU.
Конкретная модель выбирается после smoke test по размеру, языкам и доступной RAM.

## Scope

- [ ] Определить typed `EmbeddingProvider` contract для documents и queries.
- [ ] Подключить первую локальную multilingual модель через Transformers/PyTorch.
- [ ] Реализовать model loading, CPU device selection, pooling и normalization.
- [ ] Возвращать и валидировать `dimension`, model/version и device metadata.
- [ ] Добавить unit tests и CPU smoke test на deterministic sample chunks.
- [ ] Логировать smoke experiment в MLflow.

## Out of Scope

- Qdrant и similarity search.
- Batch embedding всего корпуса.
- BM25/RRF, FastAPI, LLM и retrieval evaluation.
- Финальный выбор chunking или embedding baseline по MRR/nDCG.

## Expected Artifacts

- `src/rag_based_on_obsidian/embeddings/` — provider contracts и implementation.
- `configs/embeddings/` — model/device configuration.
- `tests/embeddings/` — contract and smoke tests.
- MLflow run — model, dimension, normalization и device metadata.
- Документированный model → vector contract для Sprint 11.

## Acceptance Criteria

- [ ] Один provider умеет `embed_documents()` и `embed_query()`.
- [ ] CPU inference возвращает vectors одинаковой dimension.
- [ ] В vectors нет NaN/Inf; normalization проверяется.
- [ ] Model name, version, dimension и device сохраняются.
- [ ] Smoke test воспроизводим на фиксированном sample.
- [ ] Замена модели не требует изменений в pipeline contract.

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

Будут измеряться после реализации: dimension, model load time, smoke latency,
vector norm validity и failed inference count.

## Review

### Not Completed

- Implementation and model selection are not started.

### Technical Debt

- Exact model choice remains open until CPU smoke test and memory check.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
