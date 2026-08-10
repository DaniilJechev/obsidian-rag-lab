# Sprint 2 — Markdown Parsing

> Статус: `in-progress`
>
> Ветка: `sprint/2-markdown-parsing`
>
> Связанная фаза roadmap: `Фаза 1`

## Sprint Goal

Преобразовать найденные Markdown-файлы в детерминированное структурированное
представление с сохранением исходного provenance.

## Why

Parser создаёт data contract между Obsidian vault и будущими chunking,
embedding и citation слоями. Стабильный контракт позволит следующим фазам
работать с данными, не читая Markdown хаотично повторно.

## Scope

- [ ] `CORPUS-002` — распарсить Markdown-структуру.
- [ ] Извлечь raw text, frontmatter, headings, wikilinks и image links.
- [ ] Сохранить path, filename, folder и parser warnings.
- [ ] Добавить fixtures и тесты для обычных, пустых и частично повреждённых заметок.

## Out of Scope

- Corpus inventory, EDA и `corpus_inventory.json`.
- PostgreSQL persistence и migrations.
- Chunking, embeddings, Qdrant и retrieval.
- Изменение исходных заметок.

## Expected Artifacts

- `src/` Markdown parser и внутренние структуры данных.
- `tests/` Markdown fixtures и parser tests.
- Документированный parser contract.
- Обновлённый execution log и validation evidence.

## Acceptance Criteria

- [ ] Parser обрабатывает Markdown-файлы из discovery layer.
- [ ] Frontmatter извлекается без потери raw text.
- [ ] Headings и wikilinks сохраняются структурированно.
- [ ] Image links распознаются отдельно от wikilinks.
- [ ] Ошибки и warnings не скрываются.
- [ ] Parser не изменяет исходные файлы.
- [ ] Тесты покрывают основные и пограничные форматы.

## Definition of Done

- [ ] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит после публикации изменений.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Sprint-документ содержит реальные результаты и ограничения.
- [ ] Пользователь подтвердил завершение спринта.

## Estimate

12–18 часов разработки и обучения.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-10 | Утверждён parser contract и разделение discovery/content entities | Созданы immutable `markdown_entities.py` и `ParsedDocument` |
| 2026-08-10 | Реализован полный parser slice | Добавлено извлечение raw text, YAML frontmatter, headings, wikilinks и image links |
| 2026-08-10 | Добавлены parser integration tests | Parser-specific suite: 5 passed |

## Validation Evidence

### Commands

```text
uv run ruff check --fix .
uv run ruff check .
uv run pytest tests/test_markdown_parser.py -q --basetemp .pytest-tmp
uv run pytest -q --basetemp .pytest-tmp
```

### Test and Lint Results

- Tests: parser-specific `5 passed`; full suite `19 passed, 1 skipped`
- Lint: `passed` (`All checks passed!`)
- CI: `not run`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Parser-specific tests | 5 passed | `tests/test_markdown_parser.py` |
| Full test suite | 19 passed, 1 skipped | Existing discovery tests plus parser tests |

## Review

### Completed

- Sprint scope согласован.
- Parser entities и `ParsedDocument` созданы в `src/rag_based_on_obsidian/corpus/markdown_entities.py`.
- Parser реализован в `src/rag_based_on_obsidian/corpus/markdown_parser.py`.
- Добавлена зависимость `PyYAML` для YAML frontmatter.
- Тесты parser добавлены в `tests/test_markdown_parser.py`.
- Проверено сохранение raw text, provenance и read-only поведения на fixtures.

### Not Completed

- Read-only smoke test на реальном vault ещё не выполнен.
- CI и GitHub review ещё не выполнены.
- Полный DoD Sprint 2 ещё не пройден.

### Changed Decisions

- `warnings` не включены в `ParsedDocument`; ошибки frontmatter не скрываются и
  представлены исключениями.
- Frontmatter является optional: при его отсутствии возвращается пустой mapping.

### Technical Debt

- Реальные Obsidian edge cases ещё не проверены на smoke test.
- Parser пока не формирует отдельный ingestion/diagnostic report.

## Retrospective

Будет заполнена после выполнения спринта.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.

**Итоговый статус:** `in-progress`

**Дата завершения:** —
