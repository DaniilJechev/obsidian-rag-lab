# Sprint 27 — Rerank retrieval eval

> Статус: `done`
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

- [x] Eval runs: hybrid vs hybrid+rerank на Phase 7 gold (same k).
- [x] MLflow / sprint-doc table with nDCG/MRR.
- [x] Decide default rerank flag from evidence.
- [x] Update this document; prepare `ML-001` → done at phase closeout.

## Out of Scope

- Re-wiring CE (Sprint 26 / Issue #70).
- Embedding model change, cache, generate/RAGAS as primary gate.
- XGBoost classifier.

## Expected Artifacts

- `docs/agile/sprint-27-rerank-retrieval-eval.md` — этот документ.
- MLflow runs (or equivalent logged metrics) for before/after.
- Decision note: default on vs off.

## Acceptance Criteria

- [x] Before/after metrics recorded on the same gold freeze.
- [x] Default flag decision written here with rationale.
- [x] Ruff / pytest green if code touched; vault / secrets ok.
- [x] `ML-001` ready to mark done at Phase 12 closeout.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят (если код менялся).
- [x] Ruff/lint проходит (если код менялся).
- [x] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [x] Пользователь подтвердил завершение спринта (PR #74 merged).

## Dependencies and risks

- Sprint 26 CE path on `main` (`0b8e230`).
- Gold freeze: `phase7_GT_note_level_v0`.
- Live Qdrant + embeddings; CE on CPU ~1.5h for 50 questions.

## Estimate

8–14 часов.

## Proposed branch

`sprint/27-rerank-retrieval-eval`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-27 | Planning | Документ создан; Issue #71; Milestone 12 |
| 2026-08-27 | Eval wiring | CLI `--enable-rerank`/`--no-enable-rerank`; MLflow `phase-12-rerank-retrieval-eval` |
| 2026-08-27 | Live A/B | disable + enable runs on gold v0, k=5, candidate_k=20 |
| 2026-08-27 | Default decision | keep `rerank.enabled: false` (CPU latency) |
| 2026-08-27 | PR #74 | merged `12102b6`; Issue #71 closed; CI SUCCESS |
| 2026-08-27 | Closeout | этот документ + backlog; Milestone 12 closed |

## Validation Evidence

### Commands

```text
uv run rag-cli eval run --method hybrid --top-k 5 --candidate-k 20 --no-enable-rerank
uv run rag-cli eval run --method hybrid --top-k 5 --candidate-k 20 --enable-rerank
uv run ruff check … (sprint-27 paths)
uv run pytest -q   # one full suite before commit
```

### Test and Lint Results

- Lint: `uv run ruff check` (sprint-27 paths) — All checks passed
- Tests: `uv run pytest -q` — **242 passed**, 1 skipped, 18 deselected
- CI: PR [#74](https://github.com/DaniilJechev/obsidian-rag-lab/pull/74) `Lint and test` SUCCESS
  (merge `12102b6`)

### Setup (shared)

| Field | Value |
|---|---|
| dataset_version | `phase7_GT_note_level_v0` |
| method | hybrid |
| k / top_k | 5 |
| candidate_k | 20 |
| rrf_k | 60 |
| collection | `rag_chunks_dense_sparse__sprint9-policy-512-v2__intfloat-multilingual-e5-small__main__384` |
| MLflow experiment | `phase-12-rerank-retrieval-eval` (id 9) |
| questions | 50 scored / 0 skipped |

### Metrics (disable vs enable)

| Metric | disable_rerank | enable_rerank | Δ |
|---|---:|---:|---:|
| nDCG@5 | 0.616 | 0.645 | +0.029 |
| MRR@5 | 0.797 | 0.882 | +0.084 |
| Precision@5 | 0.368 | 0.368 | 0 |
| Recall@5 | 0.613 | 0.613 | 0 |
| F1@5 | 0.460 | 0.460 | 0 |
| Hit@5 | 0.92 | 0.96 | +0.04 |
| MAP@5 | 0.513 | 0.540 | +0.027 |
| R-Precision | 0.533 | 0.533 | 0 |
| duration_seconds | 38.0 | 5253.7 (~1.46 h) | CPU CE dominant |

### MLflow run ids

| Label | run_name | run_id |
|---|---|---|
| disable | `eval-live-hybrid-disable_rerank` | `390af038091c42ae8bdad388b4468f47` |
| enable | `eval-live-hybrid-enable_rerank` | `8b7b3076ec034058b06ee99c62885aee` |

UI: http://127.0.0.1:5000/#/experiments/9

### Decision: default `enabled: false`

**Оставить CE выключенным по умолчанию** в `configs/retrieval/retrieval.yaml`.

- Ranking улучшился (nDCG/MRR/Hit/MAP), P/R/F1@5 без изменений.
- На CPU enable ~**138×** дольше disable (~38s → ~1.5h на 50 q) — неприемлемо как prod default без GPU.
- Opt-in: CLI `--enable-rerank` или YAML `enabled: true` когда есть GPU / допустима latency.

## Review

### Completed

- Live A/B + MLflow experiment + CLI flag.
- Evidence table + default=false decision.
- PR [#74](https://github.com/DaniilJechev/obsidian-rag-lab/pull/74) merged (`12102b6`);
  Issue [#71](https://github.com/DaniilJechev/obsidian-rag-lab/issues/71) closed.
- Phase 12 / `ML-001` complete (Sprint 26 wire + Sprint 27 eval).

### Not Completed / carry-over

- Generate/RAGAS impact of CE — out of scope (future opt-in GPU).
- GPU / Colab latency re-measure — optional later.

### Changed Decisions

- Default CE **off** despite quality gains (latency gate on CPU).

### Technical Debt

- CPU CE too slow for interactive default; pin `model_revision` still null.

## Retrospective

### What went well

- CLI flag без Docker restart для A/B.
- Отдельный MLflow experiment + run names `enable_rerank` / `disable_rerank`.
- Чёткий latency vs quality trade-off для default.

### Difficulties

- CE на CPU ~1.5h / 50 q — eval долгий, но reproducible.
- Windows `.git/HEAD` lock мешает switch веток при closeout.

### Changes for next sprint

- Не включать CE default без GPU; Phase 13+ cache/storage по roadmap.
- Опционально: generate-side impact CE — отдельный эксперимент.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.
- [x] Следующий sprint / phase transition зафиксированы (Phase 12 done).

**Итоговый статус:** `done`

**Дата завершения:** 2026-08-27
