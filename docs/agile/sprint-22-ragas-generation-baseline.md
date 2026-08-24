# Sprint 22 — RAGAS harness and gpt-4o-mini baseline

> Статус: `completed`
>
> Ветка: `sprint/22-ragas-generation-baseline`
>
> Связанная фаза roadmap: `Фаза 10`
>
> Backlog: `MLOPS-001`
>
> GitHub: [Issue #58](https://github.com/DaniilJechev/obsidian-rag-lab/issues/58),
> [Milestone Phase 10](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/10)

## Sprint Goal

На фиксированных gold-вопросах generate считает четыре RAGAS-метрики,
пишет MLflow-run с версиями index/LLM/prompt/gold, и в репозитории лежит
human-шаблон на 10 вопросов (шкала целые 0–5, как у JSON-судьи). Заполненные
баллы владельца — carry-over в Sprint 23, не блокер merge. Модель generate:
`openai/gpt-4o-mini`.

## Why

Phase 9 даёт `POST /generate` и цитаты. Без RAGAS-линейки нельзя честно
сравнивать модели (Sprint 23) и нельзя сказать, галлюцинирует ли ответ
относительно packed context. Human sample нужен, потому что LLM-as-judge
сам по себе смещён (judge v1 = та же mini).

Phase 10 закрывается только после merge **обоих** спринтов 22 и 23.
Этот спринт даёт harness и baseline; bake-off в него не входит.

## Scope

- [x] Контракт: вопрос → packed contexts + answer + usage через
      существующий `run_rag_generate` / `POST /generate`, не новый retriever.
      Live-прогон бьёт HTTP API (не второй in-process generate).
- [x] Адаптер судьи на OpenRouter JSON (оси Faithfulness / Answer Relevancy
      как у RAGAS, шкала **целые 0–5**, не доля 0–1). Context Precision/Recall
      остаются в [0, 1] (note-level proxy). Пакет `ragas` 0.4.3 в lockfile есть,
      но `import ragas` сейчас падает (`langchain_community.chat_models.vertexai`);
      live не импортирует ragas. `uv add ragas` уже сделан владельцем.
- [x] Метрики: Faithfulness, Answer Relevancy, Context Precision,
      Context Recall. Context Precision/Recall v1: чанк/заметка релевантна, если
      `source_path` ∈ gold `relevant_notes` (note-level proxy; эталонного
      ответа в gold нет).
- [x] CLI `rag-cli ragas run` + YAML в `configs/eval/ragas.yaml`. Live subset
      **15/50**; полный набор — `--full-set` или `full_set: true`. Plan concurrency
      5; live baseline записан на **concurrency 2** (5 через VPN давал skip).
- [x] MLflow: эксперимент `phase-10-ragas-generation`, теги `phase=10`,
      `sprint=22`, `task=MLOPS-001`.
- [x] Human-шаблон `evals/human/sprint22_sample.yaml` на 10 вопросов, шкала
      целые 0–5. Заполненные баллы владельца перенесены в Sprint 23
      (не выдумывать; pack `sprint22_review.yaml` в gitignore).
- [x] Тесты с моками HTTP/судьи; CI без `OPENROUTER_API_KEY`.
- [x] Live subset владельцем (VPN): RAGAS + tokens/latency записаны
      числами из реального прогона.

## Out of Scope

- Заполненные human scores 0–5 в `sprint22_sample.yaml` (carry-over
  Sprint 23 / `MLOPS-002`; шаблон остаётся артефактом этого спринта).
- Bake-off 2–3 моделей и runtime пакета `ragas` (Sprint 23 / `MLOPS-002`).
- LangGraph, rerank, cache, Telegram, vLLM.
- Таблица `generation_logs`.
- Смена hybrid-default и embedding-модели.
- Правка живого roadmap без отдельного разрешения.
- Реализация на ветке `main`.
- Старт Sprint 23 до merge этого спринта.

## Expected Artifacts

- `docs/agile/sprint-22-ragas-generation-baseline.md` — этот документ.
- Расширение `src/rag_based_on_obsidian/eval/` — RAGAS runner поверх
  существующего generate.
- `configs/eval/ragas.yaml` — subset, модель, judge pin, k.
- `evals/human/sprint22_sample.yaml` — шаблон human sample.
- `tests/eval/` — моки четырёх метрик, без живого ключа.

Gold остаётся `evals/gold/phase7_GT_note_level_v0.yaml`.

## Acceptance Criteria

- [x] Моки считают четыре метрики без сети OpenRouter.
- [x] Live subset записан (RAGAS + tokens/latency) числами из реального
      прогона; метрики не выдуманы. Канон: MLflow `4663f6d7fc804f2eb128cfd5db412300`.
- [x] MLflow-run с версиями index/LLM/prompt/gold и тегами фазы/спринта.
- [x] Human-шаблон в репозитории (`sprint22_sample.yaml`, 10 id, `null`).
      Scores владельца — carry-over Sprint 23, не фиктивные баллы.
- [x] CI зелёный без `OPENROUTER_API_KEY`.
- [x] Vault не изменён; секреты не в git.

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
- [x] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- Нужен `OPENROUTER_API_KEY` в локальном `.env`. CI в сеть не ходит.
- Live OpenRouter с PoP DME может отдавать Cloudflare 403 без VPN
  (урок Sprint 21).
- `uv add ragas` выполняет только владелец; assistant не запускает
  `uv add` / `uv sync`.
- Judge v1 = `openai/gpt-4o-mini` на ответах той же модели → bias
  LLM-as-judge; это ограничение v1, не баг.
- Note-level proxy слабее chunk-GT; для v1 приемлемо.
- Human 10 вопросов может не влезть в этот спринт → carry-over в 23.
- Локально уже может лежать незакоммиченный `ragas>=0.4.3` в
  `pyproject.toml` / `uv.lock` (ручной `uv add` владельца). В planning
  commit это не входит.

## Estimate

12–16 часов разработки + live прогон.

## Proposed branch

`sprint/22-ragas-generation-baseline`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-24 | Planning | Документ создан на `sprint/22-ragas-generation-baseline`; GitHub Issue [#58](https://github.com/DaniilJechev/obsidian-rag-lab/issues/58); реализация не начата |
| 2026-08-24 | Implementation | Harness: `rag-cli ragas run` → `POST /generate` (concurrency 5, subset 15); note-level Context P/R; OpenRouter JSON judge; MLflow experiment `phase-10-ragas-generation`; human template. Live subset ещё не гоняли. `import ragas` в текущем venv падает. |
| 2026-08-24 | Live baseline | VPN + `concurrency: 2`: 15/15 scored, skip 0. MLflow `4663f6d7fc804f2eb128cfd5db412300`. Human sample ещё не размечен. |
| 2026-08-24 | Scope change | Владелец закрывает Sprint 22 без разметки: human scores 0–5 → Sprint 23. Шаблон и review-pack остаются. |
| 2026-08-24 | Merge PR [#60](https://github.com/DaniilJechev/obsidian-rag-lab/pull/60) | `25f924e` в `main`. Issue [#58](https://github.com/DaniilJechev/obsidian-rag-lab/issues/58) closed. Milestone 10 открыт (#59). |

## Validation Evidence

### Commands

```text
uv run rag-cli ragas run
```

Host `configs/eval/ragas.yaml`: `subset_size: 15`, `concurrency: 2`, `method: hybrid`,
`top_k: 5`, judge `openai/gpt-4o-mini`. API: Docker `POST /generate`. VPN on.

Failed earlier (not baseline): skip-all 503 key/403; then 4/15
`openrouter is unreachable` at concurrency 5.

### Test and Lint Results

- Tests: `uv run pytest -q` — **205 passed**, 1 skipped, 18 deselected
  (`not manual`), 1 Starlette/httpx warning, 34.59s, 2026-08-24.
- Lint: `uv run ruff check .` — All checks passed, 2026-08-24.
- CI: PR [#60](https://github.com/DaniilJechev/obsidian-rag-lab/pull/60)
  `Lint and test` SUCCESS, run
  [32777037749](https://github.com/DaniilJechev/obsidian-rag-lab/actions/runs/32777037749).
- Live: не pytest; канон MLflow `4663f6d7fc804f2eb128cfd5db412300`.

### Metrics

Канон Sprint 22, MLflow run `4663f6d7fc804f2eb128cfd5db412300`
(experiment `phase-10-ragas-generation`):

| Метрика | Значение | Шкала |
|---|---|---|
| scored / skipped / refused | 15 / 0 / 0 | из 15 |
| faithfulness | 4.6 | среднее целых 0–5 |
| answer_relevancy | 4.667 | среднее целых 0–5 |
| context_precision | 0.448 | note-level proxy [0, 1] |
| context_recall | 0.444 | note-level proxy [0, 1] |
| mean_latency_ms | 2893 | generate |
| notes_processed | 49 | unique packed notes |
| prompt tokens total / mean / median | 24172 / 1611.5 / 1468 | |
| generated tokens total / mean / median | 2711 / 180.7 / 202 | |
| duration_seconds | 26.37 | wall clock CLI score |
| human_review_count | 10 | review.yaml готов к разметке |

JSON-судья и generate — оба `gpt-4o-mini`; 4.6 / 4.67 близки к потолку.
Context P/R ~0.45: packed notes часто не совпадают с gold `relevant_notes`,
даже когда судья хвалит ответ.

## Review

### Completed

- Harness + live subset 15/15 на concurrency 2.
- MLflow `4663f6d7fc804f2eb128cfd5db412300`.
- Human-шаблон 10 вопросов; scores `null`.
- Implementation merged PR [#60](https://github.com/DaniilJechev/obsidian-rag-lab/pull/60) (`25f924e`).
- Issue [#58](https://github.com/DaniilJechev/obsidian-rag-lab/issues/58) closed.

### Not Completed

- Human scores 0–5 — **перенесены в Sprint 23** / [#59](https://github.com/DaniilJechev/obsidian-rag-lab/issues/59).
- Runtime пакета `ragas` и bake-off — Sprint 23, не этот closeout.

### Changed Decisions

- Phase 10 = два спринта: 22 harness/baseline, 23 bake-off + ragas runtime.
- JSON-судья и human: целые 0–5, не RAGAS-доля 0–1. Context P/R остаются [0, 1].
- Live concurrency 2 вместо plan 5: через VPN пять параллельных `/generate`
  давали `openrouter is unreachable`.
- Human scores 0–5 не блокер merge Sprint 22: шаблон в репо, разметка — Sprint 23.

### Technical Debt

- `import ragas` падает (Vertex import); судья v1 = JSON 0–5, не пакет.
- Judge = та же mini, что generate → риск завышенных F/AR.

## Retrospective

### What Went Well

- Live eval бьёт тот же `POST /generate`, что и продукт; второго in-process generate нет.
- Моки HTTP/судьи дали зелёный CI без `OPENROUTER_API_KEY`.
- Канон 15/15 на concurrency 2 после того, как 5 параллельных вызовов через VPN сыпали skip.

### What Was Difficult

- OpenRouter 403 без VPN неотличим от «отклонён ключ»; skip-all прогон нельзя считать baseline.
- JSON-судья = та же mini, что generate: средние 4.6 / 4.67 при context P/R ~0.45.
- Human-разметка 10 вопросов не влезла в вечер closeout — сознательный carry-over, не фиктивные баллы.

### What We Will Change

- Sprint 23 начинается с human 0–5 по `sprint22_review.yaml`, не с bake-off.
- `import ragas` чинить до сравнения моделей; JSON 0–5 и ragas 0–1 не класть в одну таблицу.
- Для live OpenRouter держать VPN и concurrency ≤2, пока skip не исчезнет.

### Backlog Updates

- Добавить: нет.
- Перенести: заполненные human scores 0–5 → `MLOPS-002` / Sprint 23.
- Изменить приоритет: нет.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён (owner merge PR [#60](https://github.com/DaniilJechev/obsidian-rag-lab/pull/60), `25f924e`; GitHub review records на PR пустые — self-approval запрещён).
- [x] Retrospective заполнена.
- [x] Commit/PR/merge implementation выполнены; этот closeout — отдельный PR.
- [x] Backlog обновлён (`MLOPS-001` → done; human scores → `MLOPS-002`).
- [x] Следующий sprint выбран или запланирован. Sprint 23 / `MLOPS-002` уже в backlog; код после этого closeout.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-24`
