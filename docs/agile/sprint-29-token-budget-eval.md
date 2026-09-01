# Sprint 29 — Token budget eval

> Статус: `in_progress`
>
> Ветка: `sprint/29-token-budget-eval`
>
> Связанная фаза roadmap: `Фаза 13`
>
> Backlog: `CACHE-002`
>
> GitHub: [Issue #77](https://github.com/DaniilJechev/obsidian-rag-lab/issues/77),
> [Milestone Phase 13](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/13)

## Sprint Goal

Ablation `max_context_tokens` (800 / 1200 / 1800) на gold subset; MLflow фиксирует
**tokens/query, latency, spot RAGAS, nDCG@5, MRR@5**; per-request override без
пересборки Docker; в sprint-документе — recommended default budget с trade-offs.

**Dedup — out of scope** (атомарные заметки; несколько чанков с одной note сохраняются).

## Why

После semantic cache (Sprint 28) следующий рычаг cost/latency — сколько контекста
пакуем в промпт. Без ablation default `1800` tokens остаётся необоснованным.

Eval в этом спринте — cache **выключен**, чтобы изолировать эффект packing.

## Scope

- [x] Reorg `eval/` → `cache/`, `ragas/`, `retrieval/`, `token_budget/`
- [x] `POST /generate` override `max_context_tokens` (API + `generation_client`)
- [x] Richer gate trace: `packed=`, `budget=`, `est_tokens=`, `refused=`
- [x] `PROMPT_VERSION` bump `generate-v1` → `generate-v2`
- [x] `configs/eval/token_budget/budget.yaml` + loader
- [x] `rag-cli eval budget` + MLflow `phase-13-token-budget-eval`
- [x] Tests: budget yaml/runner/mlflow, API override, import fixes
- [x] Live eval + recommended default budget (2026-08-28 live run)

## Out of Scope

- Dedup в `llm/packing.py`
- Semantic cache changes (eval runs with `enable_cache=false`)
- tiktoken — packing остаётся char/4; acceptance через LLM `prompt_tokens`
- Full 50-q RAGAS regression (subset 15, как RAGAS harness)

## Expected Artifacts

- `configs/eval/token_budget/budget.yaml`
- `src/rag_based_on_obsidian/eval/token_budget/{budget_yaml,budget_runner,budget_mlflow}.py`
- MLflow runs in `phase-13-token-budget-eval` (3 runs: 800, 1200, 1800)

## Acceptance Criteria

- [x] `mean_prompt_tokens(800) <= mean_prompt_tokens(1200) <= mean_prompt_tokens(1800)` — **1196 ≤ 1736 ≤ 1985** (live, 15q)
- [x] API override works without container rebuild
- [x] MLflow logging wired (one run per budget)
- [x] pytest + ruff green
- [x] vault / secrets ok

## Definition of Done

- [x] Все задачи из Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены (live eval 2026-08-28).
- [x] Тесты добавлены или обновлены.
- [x] Ruff/lint проходит (`uv run ruff check src tests` — All checks passed!)
- [ ] CI проходит (после push implementation commit)
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Результаты live eval записаны в этот sprint-дocument.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Sprint 28 merged on `main`; LangGraph generate path stable
- `pack_chunks` uses char/4 token estimate — consistent ablation, not exact tokenizer
- **Quality vs cost:** lower budget may hurt RAGAS on hard questions
- Eval requires Docker API + OpenRouter + MLflow (same stack as Sprint 28)

## Estimate

12–18 часов.

## Proposed branch

`sprint/29-token-budget-eval`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-28 | Sprint 28 closeout + planning | Issue [#77](https://github.com/DaniilJechev/obsidian-rag-lab/issues/77); branch `sprint/29-token-budget-eval` |
| 2026-08-28 | Dedup removed from scope | Atomic notes; budget ablation only |
| 2026-08-28 | Gold reuse | `phase7_GT_note_level_v0.yaml`, `subset_size: 15` |
| 2026-08-28 | Live budget eval | 15q × 3 budgets, ~41 min; MLflow exp `11`, runs `budget-800/1200/1800` |

## Live eval results (2026-08-28)

Command: `uv run rag-cli eval budget --config configs/eval/token_budget/budget.yaml --log-mlflow`

| budget | mean_prompt_tokens | faithfulness | answer_relevancy | mean_latency_ms | refusal_rate |
|---:|---:|---:|---:|---:|---:|
| 800 | 1196.31 | 0.885 | 0.766 | 7956 | 0.0 |
| 1200 | 1736.47 | 0.843 | **0.917** | 8997 | 0.0 |
| 1800 | 1984.80 | 0.784 | 0.826 | 14765 | 0.0 |

MLflow run IDs: `800` → `e6cde26f…`, `1200` → `8e75cf0f…`, `1800` → `78dc7b5a…`  
Experiment: http://127.0.0.1:5000/#/experiments/11

### Recommended default: **1200** (`max_context_tokens`)

| | 800 | **1200** | 1800 |
|---|---|---|---|
| Cost (mean prompt tok) | lowest | mid | highest (+27% vs 1200) |
| Latency | ~8.0 s | ~9.0 s | ~14.8 s (+64% vs 1200) |
| Faithfulness | best (0.89) | good (0.84) | worst (0.78) |
| Answer relevancy | worst (0.77) | **best (0.92)** | mid (0.83) |

**Decision:** keep **`configs/llm/openrouter.yaml` at 1800** for now (no YAML change in this sprint).  
**Recommendation for next change:** switch default to **1200** — лучший answer_relevancy при приемлемой faithfulness и заметно ниже latency/cost, чем 1800. Override per-request (`max_context_tokens`) уже позволяет ablation без rebuild.

**Note:** mean `prompt_tokens` включает system prompt + query + packed context; поэтому при budget=800 mean prompt ≈ 1196 (>800) — budget ограничивает только packed chunks, не весь промпт.

## Validation Evidence

### Commands

```powershell
cd C:\Users\gigachaDick\RAG_based_on_obsidian
uv run pytest -q
uv run ruff check .

docker compose --env-file .env -f docker/compose.yml up -d --build postgres qdrant redis api

uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root .\artifacts\mlflow --host 127.0.0.1 --port 5000

uv run langgraph dev --allow-blocking --no-reload

uv run rag-cli eval budget --config configs/eval/token_budget/budget.yaml --log-mlflow
uv run rag-cli eval budget --config configs/eval/token_budget/budget.yaml --no-ragas
```

### Test and Lint Results

- Tests: `264 passed, 1 skipped` (`uv run pytest -q`, 2026-08-28 post-implementation)
- Lint: `All checks passed!` (`uv run ruff check src tests`, 2026-08-28)
- Live eval: 15q × 3 budgets, monotonic tokens confirmed (see table above)
- CI: `{{TBD after push}}`

## Review

### Completed

- Eval folder reorg (`cache/`, `ragas/`, `retrieval/`, `token_budget/`)
- `max_context_tokens` per-request override
- Gate trace enrichment
- `PROMPT_VERSION = generate-v2`
- `rag-cli eval budget` + MLflow experiment wiring
- Live eval: monotonic tokens; recommend default **1200** (YAML change deferred)

### Not Completed

- Change `openrouter.yaml` default from 1800 → 1200 (documented recommendation only; optional follow-up)

## Retrospective

### What Went Well

- Live ablation подтвердил монотонность prompt_tokens
- Budget 1200 — sweet spot по answer_relevancy без latency 1800
- Per-request override работает без rebuild Docker

### What Was Difficult

- Docker build: transient DNS на `zstandard` wheel (~25 min download)
- Live eval ~41 min (45 generate + RAGAS judge)

## Completion

- [ ] Definition of Done проверен.

**Итоговый статус:** `in_progress`

**Дата завершения:** `{{TBD}}`
