# Sprint 12 — Embedding Benchmark and Qdrant Handoff

> Статус: `planned`
>
> Ветка: `sprint/12-embedding-benchmark-qdrant-handoff`
>
> Связанная фаза roadmap: `Фаза 4`
>
> Backlog: `EMB-003` (proposed)

## Sprint Goal

Сравнить локальные embedding models по operational metrics и подготовить
versioned handoff для загрузки vectors в Qdrant Phase 5.

## Why

До появления golden questions нельзя честно выбрать модель по retrieval quality.
Но уже можно сравнить CPU feasibility, throughput, latency, memory, dimension и
failure modes. Это даст Phase 5 воспроизводимый provisional embedding baseline.

Qdrant подключается после независимой проверки vectors. Temporary JSON artifacts
используются как одноразовый input для loader и удаляются после consistency check.

## Scope

- [ ] Выбрать две локальные multilingual model candidates.
- [ ] Запустить обе модели на одинаковом chunk corpus и chunking version.
- [ ] Сравнить load time, throughput, latency, RAM и failure rate.
- [ ] Сравнить dimension, vector norm distribution и artifact size.
- [ ] Логировать каждый candidate как отдельный MLflow run.
- [ ] Зафиксировать provisional model baseline и model/version contract.
- [ ] Описать Qdrant loader input, payload schema и cleanup step для Phase 5.

## Out of Scope

- Production Qdrant collection и dense retrieval implementation.
- BM25/RRF и hybrid search.
- Финальный retrieval baseline по MRR/nDCG.
- Golden questions, RAGAS, LLM и generation quality.
- Fine-tuning embedding models.

## Expected Artifacts

- `configs/embeddings/model_*.yaml` — benchmark candidates.
- `artifacts/embeddings/benchmark/` — JSON/CSV/Markdown comparison.
- MLflow experiment with one run per model.
- `docs/architecture/phase-4-embeddings.md` — versioned handoff contract.
- Phase 5 Qdrant loader contract and temporary artifact cleanup procedure.

## Acceptance Criteria

- [ ] Benchmark runs use identical chunks, ordering, device and batch protocol.
- [ ] At least one model completes the baseline corpus on CPU.
- [ ] Operational metrics are recorded from real runs.
- [ ] Provisional model choice is explained by multiple criteria.
- [ ] Manifest maps every vector to `chunk_id` and `chunking_version`.
- [ ] Qdrant payload contract is versioned and documented.
- [ ] Temporary JSON deletion happens only after successful handoff validation.

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

Будут измеряться после реализации: model load time, throughput, latency,
dimension, RAM, failure rate, vector norm statistics и artifact size.

## Review

### Not Completed

- Model benchmark and Qdrant handoff are not implemented.

### Technical Debt

- Retrieval quality comparison remains deferred until Phase 7 gold evaluation.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
