# Sprint 28 — Semantic cache + eval

> Статус: `in-progress`
>
> Ветка: `sprint/28-semantic-cache-eval`
>
> Связанная фаза roadmap: `Фаза 13`
>
> Backlog: `CACHE-001`
>
> GitHub: [Issue #76](https://github.com/DaniilJechev/obsidian-rag-lab/issues/76),
> [Milestone Phase 13](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/13)

## Sprint Goal

Похожие по смыслу вопросы (E5 cosine ≥ **0.92**) обслуживаются из **Redis semantic
cache** без retrieval и LLM; на paraphrase eval-set зафиксированы **hit rate,
latency, tokens** в MLflow и принято решение **default cache on/off**.

## Why

Exact hash-cache почти не даёт hit на note-level gold с перефразировками.
E5 уже в pipeline — один `embed_query` на lookup дешевле full RAG.
Eval в том же спринте — без цифр semantic cache остаётся гипотезой (урок Phase 12).

## Scope

- [x] Redis service in `docker/compose.yml`; `REDIS_URL` in `.env.example`; user adds `redis` dep via `uv add`
- [x] `src/rag_based_on_obsidian/cache/` — settings, cosine similarity, Redis semantic store
- [x] `pipeline_versions.py` — `PROMPT_VERSION`, `cache_pipeline_fingerprint(...)`
- [x] LangGraph nodes `semantic_cache_lookup` / `semantic_cache_write`
- [x] Wire Redis + embedding provider in `api/runtime.py`; trace: `cache_hit`, `cache_similarity`
- [x] Eval set `configs/eval/cache_paraphrase_v0.yaml` (~15–25 paraphrase pairs)
- [x] CLI `rag-cli eval cache` with `--enable-cache` / `--no-enable-cache` and `--log-mlflow`
- [x] MLflow experiment `phase-13-semantic-cache-eval`: runs `semantic-cache-off` vs `semantic-cache-on`
- [x] Tests: similarity, semantic store (in-memory), graph paraphrase hit/miss
- [x] Decision: **default `cache.enabled: false`**; threshold **0.92** (see Validation Evidence)

## Out of Scope

- Exact cache, CE/RRF for query similarity
- Session memory (13.3), token budget (Sprint 29 / CACHE-002)
- PostgreSQL `cache` table, Redis persistence (RDB/AOF)
- Full 50-q RAGAS regression (spot-check only)
- Qdrant vector index for cache entries (Redis linear scan, max_entries 500)

## Expected Artifacts

- `docs/agile/sprint-28-semantic-cache-eval.md` — этот документ
- `configs/cache/cache.yaml` — semantic cache config (`similarity_threshold: 0.92`)
- `configs/eval/cache_paraphrase_v0.yaml` — paraphrase eval set
- `src/rag_based_on_obsidian/cache/` — semantic cache module
- MLflow runs in `phase-13-semantic-cache-eval`

## Acceptance Criteria

- [x] Paraphrase with sim ≥ 0.92: cache hit, no LLM, `graph_path` without `generate` (unit + smoke eval)
- [x] Orthogonal question: miss → full pipeline (graph tests)
- [x] Pipeline version bump → miss (isolated Redis namespace; fingerprint tests)
- [x] MLflow table: hit_rate, latency, tokens (smoke set; full v0 deferred)
- [x] Default `cache.enabled: false` documented (eval 40% hit on smoke — not enough for default on)
- [x] pytest + ruff green locally; vault / secrets ok

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Документация и конфигурация обновлены, если это необходимо.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Phase 12 closed on `main` (`f69997c`); LangGraph + OpenRouter generate path stable
- Warm E5 in API lifespan (Sprint 19)
- **False semantic hits:** threshold 0.92 + manual spot-check 3–5 pairs
- **Linear scan:** cap `max_entries: 500`; Redis down → graceful miss
- User must run `uv add redis` manually (project policy)

## Estimate

14–20 часов.

## Proposed branch

`sprint/28-semantic-cache-eval`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-28 | Planning + GitHub | Milestone [13](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/13); Issues [#76](https://github.com/DaniilJechev/obsidian-rag-lab/issues/76)/[#77](https://github.com/DaniilJechev/obsidian-rag-lab/issues/77); branch `sprint/28-semantic-cache-eval` |

## Validation Evidence

### Commands

```text
docker compose --env-file .env -f docker/compose.yml up -d postgres redis api qdrant
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root .\artifacts\mlflow --host 127.0.0.1 --port 5000
uv run rag-cli eval cache --log-mlflow --no-enable-cache
uv run rag-cli eval cache --log-mlflow --enable-cache
uv run pytest tests/test_cache_similarity.py tests/test_semantic_cache_store.py tests/test_lang_graph_semantic_cache.py -q
uv run ruff check src/ tests/
```

### Test and Lint Results

- Tests: `uv run pytest -q` — **258 passed, 1 skipped** (2026-08-28)
- Lint: `uv run ruff check .` — **All checks passed** (2026-08-28)
- CI: pending (after PR push)

### Metrics

Smoke set `configs/eval/cache_paraphrase_smoke_v0.yaml` (5 groups, 10 API calls), Docker stack + MLflow:

| Run | hit_rate | paraphrase_hits | MLflow run |
|---|---:|---|---|
| `--no-enable-cache` | 0.0 | 0/5 | `5bcec670…` |
| `--enable-cache` | **0.4** | **2/5** | `0d3a9a64…` |

**Decision:** keep `cache.enabled: false` in YAML; enable per-request via `enable_cache` or eval CLI.
Threshold **0.92** — balance recall vs false hits; smoke evidence sufficient for Sprint 28.

**Known limitation:** on cache hit, API `latency_ms` reflects stored LLM latency from payload, not lookup time — `paraphrase_hit_avg_latency_ms` can look worse than miss; use `hit_rate` and token metrics for eval.

## Review

### Completed

- {{TBD}}

### Not Completed

- {{TBD}}

### Changed Decisions

- Exact cache skipped; semantic-only (Phase 13 planning 2026-08-28)

### Technical Debt

- Full `cache_paraphrase_v0.yaml` eval (36 calls) not run in Sprint 28
- Cache-hit latency metric uses stored LLM latency, not lookup time
- Redis linear scan; no Qdrant index for cache entries (max_entries 500)

## Retrospective

### What Went Well

- {{TBD}}

### What Was Difficult

- {{TBD}}

### What We Will Change

- {{TBD}}

### Backlog Updates

- Добавить:
  - {{TBD}}
- Перенести:
  - {{TBD}}

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** `{{COMPLETION_DATE}}`
