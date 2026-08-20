# Sprint 17 — Gold Eval Items and Metric Harness

> Статус: `completed`
>
> Ветка: `sprint/17-gold-eval-items`
>
> Связанная фаза roadmap: `Фаза 7`
>
> Backlog: `EVAL-001` (done), частично `EVAL-002` (формулы и тесты; live baseline — Sprint 18)
>
> GitHub: [Issue #43](https://github.com/DaniilJechev/obsidian-rag-lab/issues/43),
> [Milestone Phase 7](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/8)

## Sprint Goal

Появиться воспроизводимый note-level gold set из 50 вопросов по
`ML_NLP/DLS1` и `ML_NLP/DLS2`, сохранённый в PostgreSQL `eval_items`, и
детерминированный подсчёт nDCG/MRR/Recall/Hit на фиктивных ranking без
FastAPI.

## Why

На `main` уже есть hybrid retrieval, но нет шкалы качества. Phase 8 FastAPI
сейчас не делаем: сервис не нужен, чтобы посчитать retrieval metrics.
Сначала фиксируем gold и формулы, потом (Sprint 18) гоняем dense/bm25/hybrid
на живом индексе и пишем числа в MLflow.

## Scope

- [x] `EVAL-001` — согласовать с владельцем черновик 50 вопросов
  (`evals/gold/phase7_note_level_v0.yaml`) и поправить labels после review.
  Заморозка `dataset_version=v1` перенесена в Sprint 18.
- [x] Добавить таблицу `eval_items` в SQLAlchemy Core + Alembic (контракт из
  Phase 2 schema: `question`, `corpus_scope`, `relevant_note_ids`,
  `relevant_chunk_ids=[]`, `dataset_version`).
- [x] Loader YAML → `eval_items`: resolve `relative_path` → `note_id`.
- [x] Реализовать note-level collapse (chunk ranking → unique notes) и метрики
  nDCG@5/10, MRR@10, Recall@5/10, Hit@10 с unit-тестами на синтетике.
- [x] Каркас MLflow experiment `phase-7-retrieval-eval` (tags phase/sprint/task,
  `mlflow.note.content`); Sprint 17 может залогировать только synthetic/harness
  smoke, не выдавая его за corpus baseline.
- [x] CLI принимает готовый ranked list notes: `rag-cli eval score --rankings`.

## Out of Scope

- FastAPI / REST — живая Phase 8.
- OpenRouter generate и RAGAS — Phase 9 и 10.
- Live freeze baseline dense vs bm25 vs hybrid — Sprint 18.
- Chunk-level labels и graded relevance.
- Rerank, LangGraph, cache, pgvector.
- Каталог `obsidianNotes/ML_NLP/NLP/` вне allowlist.
- Смена embedding-модели (`EMB-003`).

## Expected Artifacts

- `docs/eval/phase-7-retrieval-metrics.md` — формулы и протокол.
- `evals/gold/phase7_note_level_v0.yaml` — черновик вопросов (git).
- `src/rag_based_on_obsidian/eval/` — metrics, collapse, loader.
- Alembic migration для `eval_items`.
- `tests/eval/` — синтетические nDCG/MRR и loader tests.
- Этот sprint-документ.

## Acceptance Criteria

- [x] 50 вопросов покрывают оба каталога DLS1 и DLS2; labels note-level.
- [x] Владелец просмотрел gold; `dataset_version` остаётся
  `phase7-note-level-v0-draft` (не `v1`) до freeze в Sprint 18.
- [x] `eval_items` описывается миграцией; loader применён локально
  (`alembic upgrade` + `rag-cli eval load-gold`, `items: 50`).
- [x] Метрики совпадают с эталонными фикстурами (ручной расчёт ranking).
- [x] Пустой gold / IDCG=0 не даёт NaN.
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

- `OBSIDIAN_VAULT_ROOT` должен указывать на `obsidianNotes/ML_NLP`, иначе
  discovery не увидит DLS1/DLS2 после переноса папок.
- Loader не резолвит `note_id`, пока notes в Postgres не соответствуют
  текущим `relative_path`. Если ingestion делался со старого корня vault,
  нужен повторный read-only ingest **после** правки `.env` (это не merge
  pgvector и не FastAPI).
- Черновик gold составлен по названиям/содержимому заметок, не по live
  top-20. После CLI-прогонов labels могут измениться; тогда бамп
  `dataset_version`, а не тихая правка `v1`.

## Estimate

12–18 часов разработки + время на review gold владельцем.

## Proposed branch

`sprint/17-gold-eval-items`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-20 | Planning | Документ создан |
| 2026-08-20 | Implementation | Schema, metrics, YAML loader, MLflow harness, CLI `eval` |
| 2026-08-20 | Gold rewrite | Удалён q008; у каждого вопроса 3 заметки; добавлен q051; `v1` не заморожен |
| 2026-08-20 | Local DB | `alembic upgrade` `7a2c4d1e9f30` → `b7e4a91c2d80`; `load-gold` `items: 50` |
| 2026-08-20 | Merge | PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45); CI Lint and test SUCCESS; merge `59188fb` |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
uv run alembic upgrade head
uv run rag-cli eval load-gold
```

### Test and Lint Results

- Tests: `PASS — uv run pytest -q` (`120 passed, 1 skipped, 18 deselected`)
- Lint: `PASS — uv run ruff check .`
- CI: `PASS — GitHub Actions Lint and test` on PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45) (`SUCCESS`, 2026-08-20T17:37:49Z)
- Local load: `PASS — rag-cli eval load-gold` printed `dataset_version=phase7-note-level-v0-draft`, `items: 50`

### Metrics

Числа corpus eval (dense / bm25 / hybrid nDCG/MRR) появятся только в Sprint 18
после live run. Synthetic harness не является baseline.

## Review

### Completed

- Note-level gold: 50 вопросов, 22 DLS1 + 28 DLS2, по 3 заметки.
- `eval_items`, collapse, nDCG/MRR/Recall/Hit, CLI `load-gold` / `score`.
- Owner review implementation PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45) и merge.

### Not Completed

- Заморозка `phase7-note-level-v1` — Sprint 18.
- Live dense/bm25/hybrid baseline — Sprint 18 / `EVAL-002`.

### Changed Decisions

- Gold хранится в `eval_items`, не только YAML.
- Разметка note-level, не chunk-level.
- Draft gold принимается в Sprint 17; `v1` не объявляем до live eval.

### Technical Debt

- `load-gold` печатает `upserted: -1` на multi-row `ON CONFLICT` (PostgreSQL
  rowcount); 50 строк при этом загружаются.
- CLI top-20 как помощник разметки ещё не встроен в eval runner (Sprint 18).

## Retrospective

### What Went Well

- Тонкий IR-слой без LangChain evaluators: формулы читаемые, контракт
  collapse chunks→notes совпадает с gold.
- Owner iteration (убрать q008, минимум 3 заметки) прошла до merge, не после.

### What Was Difficult

- pgAdmin не показывал `eval_items` сразу после Alembic: дерево Tables
  нужно Refresh, это не провал миграции.
- `upserted: -1` выглядит как ошибка загрузки, хотя `items: 50` успешны.

### What We Will Change

- В Sprint 18 писать ranking JSON из живого search и не кормить score
  пустыми шаблонами.
- Freeze `v1` только после первого live прогона, если labels устоят.

### Backlog Updates

- `EVAL-001` → `done`.
- `EVAL-002` остаётся `ready`: формулы уже на `main`, live runner — Sprint 18.
- Не стартовать Phase 8 FastAPI до live baseline.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.
- [x] Следующий sprint выбран или запланирован.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-20`
