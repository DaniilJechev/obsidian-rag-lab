# Sprint 26 — Cross-encoder rerank wiring

> Статус: `in-progress` (implementation on branch; PR ещё нет)
>
> Ветка: `sprint/26-cross-encoder-rerank`
>
> Связанная фаза roadmap: `Фаза 12`
>
> Backlog: `ML-001`
>
> GitHub: [Issue #70](https://github.com/DaniilJechev/obsidian-rag-lab/issues/70),
> [Milestone Phase 12](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/12)

## Sprint Goal

После hybrid retrieval в LangGraph появляется узел **`rerank`** (cross-encoder
`bge-reranker-v2-m3`): RRF `candidate_k` → CE → request `top_k`; тот же CE-helper
доступен `/search`; при флаге off узел — passthrough, поведение как baseline.

## Why

Phase 7 gold и hybrid baseline (Sprint 18) уже есть. Rerank как явный шаг
оркестрации виден в Studio/`graph_path`; общий helper не ломает `/search` и eval.

## Scope

- [x] Config pin: **`BAAI/bge-reranker-v2-m3`**, optional `model_revision`,
      `candidate_k` / `top_k`, enable flag, **FP16** when CUDA.
- [x] Shared CE module (score pairs → top-K).
- [x] LangGraph node **`rerank`** after `retrieve`, before `gate`
      (`classify → retrieve → rerank → gate → …`); off = passthrough.
- [x] `/search` calls the same helper after hybrid when flag on.
- [x] Warm-load when `warm_load: true` **and** `enabled: true` (else lazy /
      Identity); **tqdm** on load.
- [x] Unit/integration tests; flag off = baseline; on → `rerank` in path/trace.
- [x] Latency / RAM notes записаны в этот документ.
- [x] `rerank.yaml` слито в `retrieval.yaml` (`rerank:` block); `top_n` убран —
      пул = top-level `candidate_k`.

## Out of Scope

- nDCG/MRR before/after (Sprint 27 / Issue #71).
- XGBoost / CatBoost intent classifier.
- Cache (Phase 13), CE fine-tune, LLM-rerank, INT8/4-bit (только FP16).

## Expected Artifacts

- `docs/agile/sprint-26-cross-encoder-rerank.md` — этот документ.
- CE module + LangGraph `rerank` node + `/search` hook (same helper).
- Tests covering on/off, graph path, and ordering.
- Updated deps only if required (manual `uv` by user).

## Acceptance Criteria

- [x] With rerank off, ranked results match pre-sprint behavior (same contract).
- [x] With rerank on, `graph_path` / `graph_trace` include `rerank`.
- [x] With rerank on, top-K order can differ from hybrid-only for a fixture set.
- [x] `candidate_k` → CE → `top_k` enforced (`candidate_k ≥ top_k`).
- [x] Model load shows progress (tqdm or equivalent) for download and disk load.
- [x] Ruff / pytest green locally (focused suite); vault / secrets ok.
- [x] Latency/RAM limits documented here.

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Документация и конфигурация обновлены, если это необходимо.
- [x] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Phase 11 done (`main` @ closeout Sprint 25).
- Hybrid path: `retrieval/pipeline.py` (+ API runtime); graph: `lang_graph/workflow.py`.
- Model: `BAAI/bge-reranker-v2-m3` (~2.27 GB on disk); FP16 ≈ half weight RAM vs FP32;
  same process also holds e5 — need spare system RAM beyond weights alone.
- Default in `retrieval.yaml`: `enabled: false`, `warm_load: false` until
  Sprint 27 metrics decide otherwise.
- New dependency may need user-run `uv add` / sync.

## Estimate

12–18 часов.

## Proposed branch

`sprint/26-cross-encoder-rerank`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-27 | Planning | Документ создан; Issue #70; Milestone 12 |
| 2026-08-27 | Model pin | `BAAI/bge-reranker-v2-m3` + FP16 + tqdm on load |
| 2026-08-27 | Placement | LangGraph node `rerank` + shared CE helper for `/search` |
| 2026-08-27 | Implementation | CE module, config, graph node, runtime `/search` hook |
| 2026-08-27 | Config tidy | `rerank.yaml` → `retrieval.yaml` nested `rerank:` |
| 2026-08-27 | Pool unify | removed `top_n`; RRF→CE pool = `candidate_k` |
| 2026-08-27 | Local smoke then default off | tried on locally; merge default `enabled`/`warm_load` false; `max_length: 728` |
| 2026-08-27 | Status report | доклад; commit/push → PR by user |

## Validation Evidence

### Commands

```text
uv run ruff check … (sprint-26 paths)
uv run pytest tests/graph/test_workflow.py tests/retrieval/test_rerank.py tests/llm/test_pipeline.py tests/api/test_runtime.py -q
```

### Test and Lint Results

- Tests: focused suite exit 0 (последний прогон: 13 passed, graph/rerank/pipeline/runtime)
- Lint: ruff All checks passed (sprint-26 paths)
- CI: pending push/PR
- Live HF download of m3: not asserted in unit tests (Identity / mocks)

### Metrics / limits

| Metric | Value | Context |
|---|---:|---|
| Model disk | ~2.27 GB | `model.safetensors` |
| FP16 weight RAM | ~1.1–1.3 GB | CUDA only; CPU stays FP32 |
| Default YAML | enabled=false, warm_load=false | on after Sprint 27 if metrics win |
| Pool / final | candidate_k=20 / request top_k | RRF then CE then cut |
| max_length | 728 | token truncation query+chunk |
| Gate score | hybrid score kept | CE in `rerank_score` only |

## Review

### Completed

- Планирование Sprint 26 зафиксировано.
- CE wiring: module, LangGraph `rerank`, `/search` hook, tests.
- Config: nested `rerank:` in `retrieval.yaml`; single pool `candidate_k`.

### Not Completed

- Commit / push / PR → Issue #70.
- CI green on remote.
- User sign-off на DoD / closeout.
- Sprint 27 eval (nDCG/MRR) — отдельный спринт.

### Changed Decisions

- Phase 12 = CE only; XGBoost classifier dropped from this phase.
- Model = `BAAI/bge-reranker-v2-m3` with FP16; tqdm on every load.
- Placement = LangGraph `rerank` node after `retrieve`; shared CE helper also used by `/search`.
- No separate `rerank.yaml` / `top_n` — one retrieval config, pool = `candidate_k`.
- Default CE **off** until Sprint 27 evidence.

### Technical Debt

- `model_revision: null` — pin HF commit before reproducible Sprint 27 runs.

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `in-progress` (implementation complete locally; commit/PR pending)

**Дата завершения:** —

---

## Доклад (2026-08-27)

**Цель спринта:** встроить cross-encoder после hybrid так, чтобы он был
видимым узлом графа и общим helper для `/search`, без ломки baseline при off.

**Сделано**
1. Узел `rerank` в пути `classify → retrieve → rerank → gate → …`.
2. `CrossEncoderReranker` / `IdentityReranker`; gate смотрит hybrid `score`,
   CE пишет в `rerank_score`.
3. Конфиг: блок `rerank:` в `configs/retrieval/retrieval.yaml`.
4. Пул: dense/BM25 → RRF на `candidate_k` → CE → срез `top_k`.
5. Тесты: on/off, path/trace, reverse-order fixture; ruff + focused pytest green.

**Не сделано (вне DoD wiring / следующий шаг)**
- Git: commit → PR к #70 → CI.
- Метрики nDCG/MRR (Sprint 27 / #71).
- Pin `model_revision` под eval.

**Дефолт в YAML:** `enabled: false`, `warm_load: false`, `max_length: 728`,
`candidate_k: 20`, `top_k: 5`.

**Риски:** RAM (e5 + CE) when on, первый старт с tqdm/~2.3 GB download,
воспроизводимость без `model_revision`.
