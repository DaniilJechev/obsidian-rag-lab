# Sprint 7 — LangChain Documents and SectionTree

> Статус: `planned`
>
> Ветка реализации: `sprint/7-langchain-documents-section-tree`
>
> Связанная фаза roadmap: `Фаза 3`
>
> Зависимость: Phase 1 Markdown parser и Sprint 6 `note → chunks` handoff

## Sprint Goal

Определить и протестировать структурный контракт `parsed Markdown → typed blocks
→ SectionTree → LangChain Document`, который сохраняет смысловую структуру
заметки, metadata и character offsets до следующего спринта.

## Why

Recursive splitter не должен получать бесформенную строку, если исходная заметка
уже содержит headings, code blocks, списки, таблицы и wikilinks. `SectionTree`
будет промежуточной структурой между существующим parser и LangChain:

- parser отвечает за извлечение фактов из Markdown;
- `SectionTree` отвечает за иерархию секций и границы;
- LangChain `Document` становится runtime-контрактом для splitter pipeline;
- persistence остаётся собственным прозрачным контрактом проекта.

Так мы используем LangChain с самого начала, но не отдаём framework-у
ответственность за versioning, offsets, PostgreSQL и экспериментальную
воспроизводимость.

## Scope

- [ ] Описать typed block contract для heading, paragraph, code, list, table,
  wikilink и pre-heading text.
- [ ] Построить `SectionTree` с `direct_body`, children, heading metadata,
  `section_path`, section level/type и character offsets исходного Markdown.
- [ ] Определить поведение для pre-heading text, пустых headings, вложенных
  headings, code/list/table blocks и повторяющихся headings.
- [ ] Определить metadata propagation contract для LangChain
  `Document(page_content, metadata)`.
- [ ] Создать `ChunkingPolicy` и typed YAML config validation без запуска
  production chunking.
- [ ] Проверить, что heading context, note identity, source hash, parser version,
  section metadata и offsets не теряются при преобразовании в Documents.
- [ ] Добавить unit tests для нормальных, коротких и pathological Markdown notes.
- [ ] Подготовить базовый MLflow run для sectionization/config evidence, если
  локальная MLflow инфраструктура уже доступна.

## Out of Scope

- Recursive chunk generation и выбор финального chunk size — Sprint 8 и 9.
- Embeddings, Qdrant, BM25/RRF и retrieval evaluation — последующие фазы.
- Raw Markdown persistence в `notes`.
- Удаление или изменение файлов в `obsidianNotes`.
- LangGraph nodes, state и graph orchestration — Phase 10.
- Semantic splitting, требующий embeddings.

## Expected Artifacts

- `src/rag_based_on_obsidian/chunking/` — SectionTree, typed blocks,
  LangChain Document adapter и policy contracts.
- `configs/chunking/*.yaml` — валидируемые YAML-конфигурации политики.
- `tests/test_chunking_section_tree.py` — unit tests структуры и offsets.
- `tests/test_chunking_documents.py` — tests metadata propagation.
- `docs/architecture/phase-3-chunking.md` — описание структурного контракта.
- `artifacts/chunking/sectionization/` — только реально созданные reports или
  MLflow artifacts; пустые/выдуманные результаты не фиксируются.

## Acceptance Criteria

- [ ] Для каждой поддерживаемой block type определены поля и инварианты.
- [ ] `SectionTree` детерминированно восстанавливает hierarchy, section path и
  offsets исходного документа.
- [ ] Pre-heading text и пустые headings имеют явное, протестированное поведение.
- [ ] LangChain `Document` сохраняет согласованный metadata contract.
- [ ] YAML policy validation отклоняет неизвестные или некорректные значения.
- [ ] Unit tests покрывают code/list/table boundaries и не требуют записи в vault.
- [ ] MLflow/config evidence создаётся только при успешном фактическом запуске.

## Definition of Done

- [ ] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Contracts и ограничения записаны в этот sprint-документ или архитектурную документацию.
- [ ] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-13 | Sprint document created from approved Phase 3 plan | Sprint 7 scope defined; implementation not started |

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

Метрики sectionization будут определены до первого baseline run; фактические
значения нельзя заранее выдумывать.

## Review

### Completed

- Sprint scope, boundaries, contracts и acceptance criteria сформулированы.

### Not Completed

- Implementation, tests, MLflow run и CI evidence ещё не выполнялись.

### Changed Decisions

- LangChain используется с начала Phase 3, а не после отдельного custom splitter.

### Technical Debt

- Нужно выбрать точную реализацию Markdown block extraction поверх существующего parser.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** `не завершён`
