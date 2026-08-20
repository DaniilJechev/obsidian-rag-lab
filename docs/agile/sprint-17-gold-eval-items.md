# Sprint 17 — Gold Eval Items and Metric Harness

> Статус: `in-progress`
>
> Ветка: `sprint/17-gold-eval-items`
>
> Связанная фаза roadmap: `Фаза 7`
>
> Backlog: `EVAL-001`, частично `EVAL-002` (формулы и тесты; live baseline — Sprint 18)
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

- [ ] `EVAL-001` — согласовать с владельцем черновик 50 вопросов
  (`evals/gold/phase7_note_level_v0.yaml`) и поправить labels после review.
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

- [ ] 50 вопросов покрывают оба каталога DLS1 и DLS2; labels note-level.
- [ ] Владелец просмотрел gold; `dataset_version` draft не называется `v1`,
  пока review не закрыт.
- [x] `eval_items` описывается миграцией; loader готов (нужен `alembic upgrade` на локальной БД).
- [x] Метрики совпадают с эталонными фикстурами (ручной расчёт ranking).
- [x] Пустой gold / IDCG=0 не даёт NaN.
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

- `OBSIDIAN_VAULT_ROOT` должен указывать на `obsidianNotes/ML_NLP`, иначе
  discovery не увидит DLS1/DLS2 после переноса папок.
- Loader не резолвит `note_id`, пока notes в Postgres не соответствуют
  текущим `relative_path`. Если ingestion делался со старого корня vault,
  нужен повторный read-only ingest **после** правки `.env` (это не merge
  pgvector и не FastAPI).
- Черновик gold составлен по названиям/содержимому заметок, не по live
  top-20. После CLI-прогонов labels могут измениться.

## Estimate

12–18 часов разработки + время на review gold владельцем.

## Proposed branch

`sprint/17-gold-eval-items` (этот skill/commit ветку не создаёт).

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-20 | Planning | Документ создан |
| 2026-08-20 | Implementation | Schema, metrics, YAML loader, MLflow harness, CLI `eval`; gold review владельца ещё открыт |
| 2026-08-20 | Gold rewrite | Удалён q008; у каждого вопроса 3 заметки; добавлен q051; `v1` не заморожен |

## Validation Evidence

### Commands

```text
uv run ruff check .
uv run pytest -q
```

### Test and Lint Results

- Tests: `uv run pytest -q` — 120 passed, 1 skipped, 18 deselected
- Lint: `uv run ruff check src/ tests/` — All checks passed
- CI: не запускался до push ветки

### Metrics

Числа corpus eval появятся только в Sprint 18 после live run.

## Review

### Completed

- Планирование Phase 7: note-level, `eval_items`, 50 вопросов, без FastAPI.

### Not Completed

- Review gold владельцем и заморозка `v1`.
- `alembic upgrade` + `rag-cli eval load-gold` на локальном Postgres.

### Changed Decisions

- Gold хранится в `eval_items`, не только YAML.
- Разметка note-level, не chunk-level.

### Technical Debt

- CLI top-20 как помощник разметки ещё не встроен в eval runner.

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

**Дата завершения:**
