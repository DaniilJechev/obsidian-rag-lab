# Sprint 10 — EmbeddingProvider and Local CPU Model

> Статус: `ready-for-closeout`
>
> Ветка: `sprint/10-embedding-provider-contract`
>
> Связанная фаза roadmap: `Фаза 4`
>
> Backlog: `EMB-001`
>
> GitHub: [Issue #28](https://github.com/DaniilJechev/obsidian-rag-lab/issues/28)
> · [Milestone Phase 4 — Local Embeddings](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/6)

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

- [x] Определить typed `EmbeddingProvider` contract для documents и queries.
- [x] Подключить первую локальную multilingual модель через Transformers/PyTorch.
- [x] Реализовать model loading, CPU device selection, pooling и normalization.
- [x] Возвращать и валидировать `dimension`, model/version и device metadata.
- [x] Добавить unit tests и CPU smoke test на deterministic sample chunks.
- [x] Логировать smoke experiment в MLflow.

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

- [x] Один provider умеет `embed_documents()` и `embed_query()`.
- [x] CPU inference возвращает vectors одинаковой dimension.
- [x] В vectors нет NaN/Inf; normalization проверяется.
- [x] Model name, version, dimension и device сохраняются.
- [x] Smoke test воспроизводим на фиксированном sample.
- [x] Замена модели не требует изменений в pipeline contract.

## Definition of Done

- [x] Scope выполнен или явно перенесён в backlog.
- [x] Acceptance Criteria проверены.
- [x] Tests проходят.
- [x] Ruff/lint проходит.
- [x] CI будет проверен после публикации sprint branch в remote.
- [x] Vault не изменён и секреты не добавлены.
- [x] Документация и конфигурация обновлены.
- [x] Пользователь подтвердил завершение sprint.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-15 | Sprint created | Planned Phase 4 scope |
| 2026-08-16 | Implemented provider slice | Contract, multilingual E5 CPU provider, pooling, normalization and MLflow tracking completed |
| 2026-08-16 | Local validation | Ruff passed; 70 passed, 1 skipped, 16 deselected |
| 2026-08-16 | CPU/MLflow smoke | Run `a023f4a528314856b36eafdb9ec5794c`; RAM and throughput evidence captured |
| 2026-08-16 | PR and merge | [PR #31](https://github.com/DaniilJechev/obsidian-rag-lab/pull/31) merged with CI success; merge commit `3fab49856c66b0d1b9e266f28ee0d0a6c13e8c56` |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest tests/embeddings -q
```

### Test and Lint Results

- Tests: `PASS — 70 passed, 1 skipped, 16 deselected`
- Lint: `PASS — uv run ruff check .`
- CPU smoke: `PASS — multilingual-e5-small, CPU, 2 documents`
- MLflow: `PASS — run a023f4a528314856b36eafdb9ec5794c`
- CI: `PASS — [Lint and test](https://github.com/DaniilJechev/obsidian-rag-lab/actions/runs/31950381824/job/95172830561)`

### Metrics

Зафиксировано в MLflow run `a023f4a528314856b36eafdb9ec5794c`:

- `dimension`: `384`
- `duration_seconds`: `0.056493700001738034`
- `documents_per_second`: `35.402177586854286`
- `vector_norm_mean`: `1.0000000227304429`
- `vector_norm_min`: `1.0000000221968457`
- `vector_norm_max`: `1.0000000232640398`
- `ram_usage_mb`: `874.05859375`
- `ram_delta_mb`: `87.0546875`

## Review

### Review Decision

- PR [#31](https://github.com/DaniilJechev/obsidian-rag-lab/pull/31) was merged
  by the owner.
- Independent review was not performed; the owner explicitly accepted a
  self-merge/review waiver for this sprint.
- CI required check `Lint and test` passed.

### Not Completed

- Final model comparison remains deferred to Sprint 12.

### Technical Debt

- `model_revision: main` should be pinned to an immutable Hugging Face revision
  before a long-lived production deployment.
- Tokenizer-aware splitting for chunks over the model limit belongs to the
  follow-up embedding pipeline hardening.
- Full-corpus batch embedding, retries and temporary JSON manifest belong to
  Sprint 11.
- Wikilink persistence into PostgreSQL `note_links` remains a separate
  ingestion follow-up.

## Retrospective

### What Went Well

- The provider contract isolated pipeline code from Transformers/PyTorch details.
- A real multilingual CPU inference and MLflow run were completed.
- Vector normalization, process RSS, throughput and vector norm metrics became
  visible evidence rather than assumptions.
- The full local suite remained green throughout the implementation.

### Difficulties

- An inherited `socks4://` proxy environment variable initially blocked the
  Hugging Face Hub client.
- The first Windows RSS measurement returned zero because the WinAPI ctypes
  signature and error handling were incomplete; this was corrected and a new
  run recorded non-zero memory metrics.
- The current smoke CLI intentionally processes only two sample documents; it
  is not yet a full-corpus embedding pipeline.

### Follow-up Actions

- Start Sprint 11 for PostgreSQL chunk loading, batching, retries and manifests.
- Pin the Hugging Face model revision and add tokenizer-aware overflow handling.
- Keep Sprint 12 for model comparison and provisional baseline selection.

## Completion

- [x] Definition of Done проверен локально.
- [x] Review decision recorded, including the owner self-merge waiver.
- [x] Retrospective заполнена.
- [x] Implementation and closeout commits выполнены.
- [x] PR created and merged.
- [x] Backlog обновлён.
- [x] Следующий sprint выбран: Sprint 11.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-16`

**Phase 4 note:** Milestone [Phase 4 — Local Embeddings](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/6)
remains open because Sprint 11 and Sprint 12 issues are still open.
