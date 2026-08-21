# Sprint 18 — Retrieval Baseline on Frozen Gold

> Статус: `completed`
>
> Ветка: `sprint/18-retrieval-eval-baseline`
>
> Связанная фаза roadmap: `Фаза 7`
>
> Backlog: `EVAL-002`
>
> GitHub: [Issue #44](https://github.com/DaniilJechev/obsidian-rag-lab/issues/44),
> [Milestone Phase 7](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/8)

## Sprint Goal

На note-level gold (`dataset_version=phase7_GT_note_level_v0`,
файл `evals/gold/phase7_GT_note_level_v0.yaml`)
измерить dense, bm25 и hybrid retrieval, записать nDCG/MRR/Recall/Hit в
MLflow и объявить эти три run каноническим baseline до rerank/cache.

## Why

Sprint 17 даёт набор и формулы. Без live прогона на том же индексе, что
сейчас в Qdrant, нечем сравнивать будущие фазы. Каждый eval run обязан
уйти в MLflow — иначе «улучшение» снова станет анекдотом.

## Scope

- [x] `EVAL-002` — eval runner: читает `eval_items`, вызывает существующий
  retrieval (dense / bm25 / hybrid), collapse chunks→notes, считает метрики.
- [x] Три MLflow run на одном `dataset_version` и одном
  `chunking_version` / collection: dense, bm25, hybrid.
- [x] Per-question artifact (predicted notes, ranks, misses) как MLflow
  artifact.
- [x] Зафиксировать baseline в этом sprint-документе **только после**
  реального запуска (никаких выдуманных чисел).
- [x] Experiment tags: phase=7, sprint=18, task=EVAL-002,
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
- CLI: `rag-cli eval run --method dense|bm25|hybrid --top-k <k>`
  (`--top-k` обязателен; MLflow on; `--no-log-mlflow` только для отладки).
- MLflow experiment `phase-7-retrieval-eval` с тремя comparable runs.
- Таблица observed metrics в этом документе после запуска.

## Acceptance Criteria

- [x] Gold v1 заморожен после review Sprint 17.
- [x] Dense, bm25 и hybrid прогнаны на полном наборе 50 вопросов.
- [x] Каждому прогону соответствует MLflow run с reproducibility tags.
- [x] nDCG/MRR/Recall/Hit/MAP @k и R-Precision записаны из этого запуска
  (один k с `--top-k`, одинаковый для dense/bm25/hybrid).
- [x] Hybrid не объявляется «лучше» без этих чисел.
- [x] Vault не изменён.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [x] Пользователь подтвердил завершение спринта. *(merge PR #47 + closeout)*

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
| 2026-08-20 | Sprint 17 merged | PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45) (`59188fb`); harness и draft gold на `main`; freeze `v1` остаётся здесь |
| 2026-08-21 | Gold path/version | Gold file `evals/gold/phase7_GT_note_level_v0.yaml`; `dataset_version=phase7_GT_note_level_v0` в `configs/eval/eval.yaml`. `load-gold` делает DELETE всех `eval_items`, затем INSERT текущего YAML. |
| 2026-08-21 | Live runner | `rag-cli eval run --method … --top-k k`: Postgres gold, один embedder на прогон, collapse→IR metrics @k с CLI, MLflow artifact `per_question.json`. |
| 2026-08-21 | Eval defaults | `--top-k` обязателен. Hybrid `candidate_k` дефолт `2 * top_k`. `rrf_k` из `configs/retrieval/retrieval.yaml` (60); `--rrf-k` — override. MLflow metric names `ndcg_at_5` (символ `@` сервер отвергает). |
| 2026-08-21 | Canonical Compare | Owner Compare трёх live run: hybrid / dense / bm25, `top_k=5`, `rrf_k=60`, 50/50 scored. Цифры ниже. Hybrid с `candidate_k=5` и rrf 10 vs 60 — **не** канон (метрики совпали байт-в-байт; пул слишком узкий для RRF). |
| 2026-08-21 | Merge + closeout | PR [#47](https://github.com/DaniilJechev/obsidian-rag-lab/pull/47) merged `6f82a00`; Issue [#44](https://github.com/DaniilJechev/obsidian-rag-lab/issues/44) closed; Milestone 8 closed (`open_issues=0`). |

## Validation Evidence

### Commands

Канонический baseline записан на `--top-k 5` (не 10). Воспроизведение:

```text
uv run ruff check .
uv run pytest -q
uv run rag-cli eval load-gold
uv run rag-cli eval run --method dense --top-k 5
uv run rag-cli eval run --method bm25 --top-k 5
uv run rag-cli eval run --method hybrid --top-k 5
```

`rag-cli search` сам по себе baseline не считает. Live eval читает
`eval_items` (после `load-gold` на `phase7_GT_note_level_v0`), грузит e5
один раз на dense/hybrid прогон и пишет run в `phase-7-retrieval-eval`.

Postgres, Qdrant и MLflow UI поднимает владелец (assistant их не стартует):

```text
docker compose --env-file .env -f docker/compose.yml up -d postgres qdrant
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root .\artifacts\mlflow --host 127.0.0.1 --port 5000
```

### Test and Lint Results

- Tests: `uv run pytest -q` — 139 passed, 1 skipped, 18 deselected (exit 0).
- Lint: `uv run ruff check .` — All checks passed.
- CI: PR [#47](https://github.com/DaniilJechev/obsidian-rag-lab/pull/47)
  `Lint and test` **pass**
  ([job](https://github.com/DaniilJechev/obsidian-rag-lab/actions/runs/32511531417/job/96863518648));
  merge commit CI on `main` **success**
  ([run](https://github.com/DaniilJechev/obsidian-rag-lab/actions/runs/32511586640)).
- Live Qdrant runs: три comparable run в MLflow Compare (скрин владельца 2026-08-21).

### Protocol of the recorded Compare

Общие params трёх колонок (порядок Compare: **hybrid, dense, bm25**):

| Param | Value |
|---|---|
| `run_kind` | live |
| `top_k` / k | 5 |
| `rrf_k` | 60 |
| `question_count` / `scored_count` | 50 / 50 |
| `skipped_count` | 0 |
| `model_name` | `intfloat/multilingual-e5-small` |
| `model_revision` | main |
| `max_length` | 512 |
| `normalized` | True |

`candidate_k` в видимом crop Compare не было. Совпадающий CLI stdout того же дня для dense (`duration_seconds=11.37`) и bm25 (`1.35`) писал `candidate_k=20` (тогда дефолт из `retrieval.yaml`). Поздние hybrid-прогоны с `candidate_k=5` в эту таблицу **не входят**.

Имена метрик в том Compare ещё без суффикса `_at_5` (`ndcg`, `average_precision`). В коде после фикса MLflow это `ndcg_at_5` / `map_at_5`.

### Metrics

Macro-average по 50 вопросам, cutoff **k=5**. Источник: MLflow Compare владельца.

| Metric @5 | hybrid | dense | bm25 |
|---|---:|---:|---:|
| nDCG | 0.616 | 0.619 | 0.536 |
| MRR | 0.797 | 0.817 | 0.726 |
| MAP (`average_precision`) | 0.513 | 0.512 | 0.412 |
| Precision | 0.368 | 0.364 | 0.336 |
| Recall | 0.613 | 0.607 | 0.560 |
| F1 | 0.460 | 0.455 | 0.420 |
| Hit | 0.92 | 0.96 | 0.96 |
| R-Precision | 0.533 | 0.520 | 0.447 |
| duration_seconds | 10.76 | 11.37 | 1.35 |
| questions_per_second | 4.646 | 4.397 | 37.02 |
| ram_usage_mb | 1023.4 | 928.1 | 500.3 |

**Как читать, не объявляя победителя по одной цифре:**

- Ranking (nDCG / MRR): **dense ≥ hybrid >> bm25**. Разница dense vs hybrid на nDCG 0.003 — в пределах шума на 50 вопросах; MRR чуть выше у dense (0.817 vs 0.797).
- Coverage: Hit@5 = 0.96 у dense и bm25, **0.92 у hybrid** — hybrid чаще пропускает *все* gold-заметки в пятёрке, при чуть более высоком Precision/Recall/MAP.
- Latency: BM25 ~1.4 с на 50 вопросов без e5; dense/hybrid ~11 с, в основном cold start модели в one-shot CLI.
- Hybrid **не** объявляется лучше dense на этом baseline.

Совпадающий CLI stdout (тот же день, те же duration): dense run `224f6e9ef3ea48b99e8b5f535b59992e`, bm25 `bd4ee33397b04a96b1f92d45bf21b454`. Hybrid в Compare — колонка `retrieval_method=hybrid` с duration 10.76 с.

## Review

### Completed

- Планирование live baseline.
- Gold freeze `v1` (`phase7_GT_note_level_v0`).
- Live eval runner и CLI `eval run`.
- Три live прогона dense / bm25 / hybrid на 50 вопросах, k=5.
- Observed metrics записаны из MLflow Compare владельца.

### Not Completed

- Нет. Следующая roadmap-фаза — FastAPI (Phase 8 / `API-001`); sprint не
  планировался в этом closeout.

### Changed Decisions

- FastAPI сознательно после Phase 7.
- Eval `candidate_k` по умолчанию `2 * --top-k`, не YAML `20` и не `= top_k`.
- Eval `rrf_k` по умолчанию из `retrieval.yaml` (60, Cormack et al. / ES default).
- MLflow metric names: `ndcg_at_k`, не `ndcg@k` (сервер отвергает `@`).

### Technical Debt

- One-shot CLI каждый run заново грузит e5; duration не чистая retrieval-latency.
- Канонический Compare снят при `candidate_k=20` (YAML того момента). Текущий eval-дефолт — `2 * top_k` (при k=5 → 10). Следующий эксперимент с другим пулом — отдельный MLflow run, не перезапись этой таблицы.
- Hit@5 ≈ 0.92–0.96: на узком DLS1+DLS2 и коротком gold методы почти всегда «находят хоть что-то»; ранжирование смотреть по nDCG/MAP/MRR.
- Несколько failed MLflow run с именами `ndcg@5` (пустые метрики) — игнорировать.

## Retrospective

### What Went Well

- Один `--top-k` для выдачи и метрик; e5 один раз на dense/hybrid прогон.
- MLflow Compare владельца как source of truth: числа не выдуманы.
- Hybrid не объявлен лучше dense: nDCG 0.616 vs 0.619, MRR 0.797 vs 0.817.

### What Was Difficult

- Сначала hybrid тянул YAML `candidate_k=20` при dense/bm25 на `top_k`.
- `candidate_k = top_k` сделал rrf_k=10 vs 60 невидимым (метрики байт-в-байт).
- Имена `ndcg@5` отвергнуты MLflow после уже посчитанного прогона.

### What We Will Change

- Fair eval: cutoff = `--top-k`; шире пул hybrid только явным `--candidate-k`.
- `rrf_k` по умолчанию 60 из YAML; ablation — отдельный run, не тихая смена.
- Metric names только `ndcg_at_k` / `map_at_k`.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён (owner merge PR [#47](https://github.com/DaniilJechev/obsidian-rag-lab/pull/47), `6f82a00`).
- [x] Retrospective заполнена.
- [x] Commit/PR/merge implementation выполнены; closeout PR следует.
- [x] Backlog обновлён (`EVAL-002` → done).
- [ ] Следующий sprint выбран или запланирован. *(Phase 8 FastAPI / API-001 — отдельный sprint-planning)*

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-21`
