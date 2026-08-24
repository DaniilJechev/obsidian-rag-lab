# Sprint 22 — RAGAS harness and gpt-4o-mini baseline

> Статус: `planned`
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
пишет MLflow-run с версиями index/LLM/prompt/gold, и владелец размечает
малый human sample 1–5. Модель generate: `openai/gpt-4o-mini`.

## Why

Phase 9 даёт `POST /generate` и цитаты. Без RAGAS-линейки нельзя честно
сравнивать модели (Sprint 23) и нельзя сказать, галлюцинирует ли ответ
относительно packed context. Human sample нужен, потому что LLM-as-judge
сам по себе смещён (judge v1 = та же mini).

Phase 10 закрывается только после merge **обоих** спринтов 22 и 23.
Этот спринт даёт harness и baseline; bake-off в него не входит.

## Scope

- [ ] Контракт: вопрос → packed contexts + answer + usage через
      существующий `run_rag_generate`, не новый retriever.
- [ ] Адаптер RAGAS + OpenRouter. `uv add ragas` — только вручную
      владельцем. Предпочтительно без отдельного `openai` SDK; иначе
      тонкий OpenAI-compatible клиент на `https://openrouter.ai/api/v1`.
- [ ] Метрики: Faithfulness, Answer Relevancy, Context Precision,
      Context Recall. Context Precision/Recall v1: чанк релевантен, если
      `source_path` ∈ gold `relevant_notes` (note-level proxy; эталонного
      ответа в gold нет).
- [ ] CLI `rag-cli ragas run` + YAML в `configs/eval/`. Live subset
      **15/50**; полный набор — флаг YAML.
- [ ] MLflow: теги `phase=10`, `sprint=22`, `task=MLOPS-001`; параметры
      index/LLM/prompt/gold versions.
- [ ] Human-шаблон `evals/human/` на ~10 вопросов; баллы только после
      разметки владельца (не выдумывать).
- [ ] Тесты с моками OpenRouter/RAGAS; CI без `OPENROUTER_API_KEY`.
- [ ] Live subset владельцем (VPN): RAGAS + tokens/latency записаны
      числами из реального прогона.

## Out of Scope

- Bake-off 2–3 моделей (Sprint 23 / `MLOPS-002`).
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

- [ ] Моки считают четыре метрики без сети OpenRouter.
- [ ] Live subset записан (RAGAS + tokens/latency) числами из реального
      прогона; метрики не выдуманы.
- [ ] MLflow-run с версиями index/LLM/prompt/gold и тегами фазы/спринта.
- [ ] Human-шаблон в репозитории; scores — если владелец успеет
      разметить, иначе carry-over в Sprint 23, не фиктивные баллы.
- [ ] CI зелёный без `OPENROUTER_API_KEY`.
- [ ] Vault не изменён; секреты не в git.

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

## Validation Evidence

### Commands

```text
(ожидается после реализации)
```

### Test and Lint Results

- Tests: не запускались (planning-only commit)
- Lint: не запускался (Python/toml в этом commit нет)
- CI: нет

### Metrics

Live RAGAS / tokens / latency — только после реального прогона.

## Review

### Completed

- Планирование Sprint 22 зафиксировано.

### Not Completed

- Реализация RAGAS harness, live subset, human scores.

### Changed Decisions

- Phase 10 = два спринта: 22 harness/baseline, 23 bake-off.

### Technical Debt

- Нет (реализация не начата).

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** —
