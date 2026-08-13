# Sprint 8 — Versioned Recursive Structural Chunking

> Статус: `planned`
>
> Ветка реализации: `sprint/8-versioned-recursive-chunking`
>
> Связанная фаза roadmap: `Фаза 3`
>
> Зависимость: Sprint 7 — LangChain Documents and SectionTree

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

- [ ] Настроить LangChain recursive splitter поверх block-aware Documents из
  Sprint 7.
- [ ] Включать heading context в `ChunkRecord.text`, а `section_path` и прочие
  структурные данные хранить в metadata/record fields.
- [ ] Сохранять `note_id`, `chunk_index`, section title/level/path/type,
  `start_offset`, `end_offset`, word count и estimated token count.
- [ ] Сохранять `parser_version`, `source_content_hash` и `chunking_version`.
- [ ] Применять overlap только при вынужденном разбиении oversized text sections.
- [ ] По возможности не разрывать code, list и table blocks.
- [ ] Реализовать version-aware PostgreSQL persistence с уникальностью
  `(note_id, chunking_version, chunk_index)`.
- [ ] Не удалять старые chunk versions; active version выбирать явно.
- [ ] Проверить idempotent regeneration, deterministic output, short/large/
  pathological notes и transaction behavior.
- [ ] Добавить unit и PostgreSQL/manual tests для persistence и version policy.

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

- [ ] Одинаковый input, parser version и chunking policy дают одинаковые chunks и hashes.
- [ ] Heading context присутствует в тексте каждого соответствующего chunk.
- [ ] Offsets и section metadata указывают на правильное место исходной note.
- [ ] Overlap отсутствует у обычных секций и применяется только для oversized sections.
- [ ] Code/list/table boundaries обрабатываются согласно policy и покрыты tests.
- [ ] Повторная генерация не создаёт duplicate rows в той же chunking version.
- [ ] Новая chunking version создаёт отдельное поколение и не удаляет старое.
- [ ] Active version выбирается явным запросом/контрактом, а не случайным latest row.
- [ ] Ошибка persistence не оставляет неконтролируемый partial generation.

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

## Validation Evidence

### Commands

```text
Будет заполнено после начала implementation.
```

### Test and Lint Results

- Tests: `не запускались; sprint находится в статусе planned`
- Lint: `не запускался; implementation отсутствует`
- CI: `не запускался`

### Metrics

Будут собраны фактические chunk counts, length distributions, duplicate hashes,
metadata completeness и persistence timings. Значения заранее не фиксируются.

## Review

### Completed

- Определены chunk contract, version policy, границы и критерии приёмки.

### Not Completed

- Chunker, persistence implementation и validation ещё не выполнялись.

### Changed Decisions

- Старые версии chunks сохраняются для audit/rollback; новая версия не делает destructive replacement.

### Technical Debt

- Точный способ выбора active version потребует согласования с query/retrieval layer.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
