# Sprint 2 — Markdown Parsing

> Статус: `planned`
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
| — | Sprint запланирован | Реализация ещё не начата |

## Validation Evidence

### Commands

```text
Будут добавлены после реализации.
```

### Test and Lint Results

- Tests: `not run`
- Lint: `not run`
- CI: `not run`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Parsed Markdown files | not measured | Будет измерено после реализации |

## Review

### Completed

- Sprint scope согласован.

### Not Completed

- Implementation не начата.

### Changed Decisions

- Нет.

### Technical Debt

- Нет.

## Retrospective

Будет заполнена после выполнения спринта.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.

**Итоговый статус:** `planned`

**Дата завершения:** —
