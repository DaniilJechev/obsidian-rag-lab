# Sprint 8 — Versioned Recursive Structural Chunking

> Статус: `implementation-in-progress`
>
> Ветка реализации: `sprint/8-versioned-recursive-chunking`
>
> Связанная фаза roadmap: `Фаза 3`
>
> Зависимость: Sprint 7 — LangChain Documents and SectionTree
>
> Backlog: `CHUNK-001`
>
> GitHub: [Issue #20](https://github.com/DaniilJechev/obsidian-rag-lab/issues/20)
> · [Milestone Phase 3 — LangChain-first Chunking](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/5)

## Sprint Goal

Реализовать детерминированный LangChain recursive structural chunker, который
преобразует SectionTree/Documents в versioned chunks и сохраняет их в
PostgreSQL без потери heading context, offsets и audit history.

## Why

Chunk должен быть не просто отрезком строки. Для будущего retrieval и citations
нужно понимать, из какой note и секции он получен, где находится в исходном
документе и какой версией политики был создан. Versioned persistence позволяет
сравнивать политики, делать rollback и не смешивать chunks разных поколений.

Основной splitter — LangChain. Собственные поля `ChunkRecord`, правила
структурных границ и PostgreSQL version policy остаются явными, чтобы поведение
можно было проверить без framework magic.

## Scope

- [x] Настроить LangChain recursive splitter поверх block-aware Documents из
  Sprint 7.
- [x] Включать heading context в `ChunkRecord.text`, а `section_path` и прочие
  структурные данные хранить в metadata/record fields.
- [x] Сохранять `note_id`, `chunk_index`, section title/level/path/type,
  `start_offset`, `end_offset`, word count и estimated token count.
- [x] Сохранять `parser_version`, `source_content_hash` и `chunking_version`.
- [x] Применять overlap только при вынужденном разбиении oversized text sections.
- [x] По возможности не разрывать code, list и table blocks; малые structural
  blocks защищаются placeholders, oversized blocks всё ещё могут split-иться.
- [x] Реализовать version-aware PostgreSQL persistence с уникальностью
  `(note_id, chunking_version, chunk_index)`.
- [x] Не удалять старые chunk versions; active version выбирать явно.
- [x] Проверить idempotent regeneration, deterministic output, short/large/
  pathological notes и transaction behavior.
- [x] Добавить unit и PostgreSQL/manual tests для persistence и version policy.

## Out of Scope

- Сравнение всех experiment candidates и выбор Phase 4 baseline — Sprint 9.
- Генерация embeddings и запись vectors в Qdrant — Phase 4–5.
- BM25/RRF, retrieval metrics, reranking и LLM.
- Автоматическое удаление старых chunk versions.
- LangGraph orchestration — Phase 10.
- Изменение исходных заметок в `obsidianNotes`.

## Expected Artifacts

- `src/rag_based_on_obsidian/chunking/` — recursive chunker, records и version policy.
- `src/rag_based_on_obsidian/db/` — только необходимые persistence changes и migration.
- `tests/test_chunking_recursive.py` — deterministic и boundary tests.
- `tests/test_chunking_persistence.py` — version/idempotency/transaction tests.
- `alembic/versions/` — migration только если текущая schema не покрывает contract.
- `docs/architecture/phase-3-chunking.md` — `ChunkRecord` и active-version semantics.

## Acceptance Criteria

- [x] Одинаковый input, parser version и chunking policy дают одинаковые chunks и hashes.
- [x] Heading context присутствует в тексте каждого соответствующего chunk.
- [x] Offsets и section metadata указывают на правильное место исходной note.
- [x] Overlap отсутствует у обычных секций и применяется только для oversized sections.
- [x] Code/list/table boundaries обрабатываются согласно policy и покрыты tests
  для малого code block; oversized structural blocks остаются ограничением.
- [x] Повторная генерация не создаёт duplicate rows в той же chunking version.
- [x] Новая chunking version создаёт отдельное поколение и не удаляет старое.
- [x] Active version выбирается явным запросом/контрактом, а не случайным latest row.
- [x] Ошибка persistence не оставляет неконтролируемый partial generation.

## Definition of Done

- [ ] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Migration применима и проверена, если она потребовалась.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-13 | Sprint document created from approved Phase 3 plan | Sprint 8 scope defined; implementation not started |
| 2026-08-14 | Added `ChunkRecord`, LangChain recursive splitter and deterministic counters | Unit contract and heading-context behavior implemented |
| 2026-08-14 | Added PostgreSQL repository and provenance migration | Versioned upsert, atomic replacement and explicit version reads implemented |
| 2026-08-14 | Published implementation PR #24 and completed GitHub Actions CI | CI `Lint and test` passed; independent review remains required |

## Validation Evidence

### Commands

```text
uv run ruff check .
All checks passed!

uv run pytest -q
54 passed, 1 skipped, 15 deselected in 25.43s

uv run pytest tests/test_chunking_persistence.py -m manual -q
1 passed in 1.57s

uv run alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
7a2c4d1e9f30 (head)
```

### Test and Lint Results

- Tests: `54 passed, 1 skipped, 15 deselected`
- Focused chunking tests: `3 passed, 1 deselected`
- Manual PostgreSQL persistence test: `1 passed in 1.57s`
- Lint: `uv run ruff check .` — passed
- Alembic: database is at `7a2c4d1e9f30 (head)`
- CI: GitHub Actions `Lint and test` passed in PR #24

### Metrics

Будут собраны фактические chunk counts, length distributions, duplicate hashes,
metadata completeness и persistence timings. Значения заранее не фиксируются.

## Review

### Completed

- Определены chunk contract, version policy, границы и критерии приёмки.
- Migration `7a2c4d1e9f30` применена к PostgreSQL и подтверждена через
  `uv run alembic current`.
- Реальная manual PostgreSQL persistence-проверка прошла.
- PR [#24](https://github.com/DaniilJechev/obsidian-rag-lab/pull/24) создан;
  required CI прошёл.

### Not Completed

- Малые code/list/table blocks защищаются при recursive split. Отдельный
  semantic strategy для oversized structural blocks остаётся техническим
  долгом и не скрывается policy.

### Changed Decisions

- Старые версии chunks сохраняются для audit/rollback; новая версия не делает destructive replacement.

### Technical Debt

- Точный способ выбора active version потребует согласования с query/retrieval layer.

## Completion

- [ ] Definition of Done проверен.
- [ ] Независимый review проведён; автор PR не может утвердить собственный PR.
- [ ] Retrospective заполнена.
- [x] Commit и push реализации выполнены по согласованному Git workflow.
- [ ] PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `implementation-in-progress`

**Дата завершения:** `не завершён`
