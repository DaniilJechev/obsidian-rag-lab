# Sprint 3 — Corpus Inventory and EDA

> Статус: `planned`
>
> Ветка: `sprint/3-corpus-inventory-eda`
>
> Связанная фаза roadmap: `Фаза 1`

## Sprint Goal

Получить воспроизводимый inventory корпуса и EDA-отчёт, который описывает
размер, качество и распределения заметок перед проектированием chunking и
хранилища.

## Why

Нельзя надёжно выбрать chunk size, overlap и стратегию хранения, не понимая
реальные распределения данных. В этом sprint используется временный
`corpus_inventory.json`; PostgreSQL относится к следующей фазе и здесь не
требуется.

## Scope

- [ ] `CORPUS-003` — подготовить corpus inventory и EDA.
- [ ] Посчитать количество файлов, слова, токены, размеры и длины заметок.
- [ ] Выявить пустые файлы, parser warnings и потенциальные дубли.
- [ ] Сохранить итоговый inventory в `artifacts/corpus_inventory.json`.
- [ ] Подготовить воспроизводимый EDA-отчёт или notebook.
- [ ] Подготовить рекомендации для chunking и Phase 2.

## Out of Scope

- PostgreSQL schema, migrations и постоянное data layer.
- Chunking и сравнение chunk sizes.
- Embeddings, Qdrant, BM25 и retrieval.
- Изменение или удаление пустых/мусорных файлов в read-only vault.

## Expected Artifacts

- `artifacts/corpus_inventory.json` — временный JSON inventory с реальными результатами.
- `notebooks/` или `src/` — воспроизводимый EDA notebook/script.
- EDA-отчёт с таблицами и минимальными визуализациями.
- Обновлённый execution log и validation evidence.

## Acceptance Criteria

- [ ] `corpus_inventory.json` создаётся воспроизводимо из parser/discovery output.
- [ ] JSON содержит версию inventory и параметры запуска.
- [ ] Статистика включает файлы, размеры, слова, токены и длины заметок.
- [ ] Пустые файлы, warnings и потенциальные дубли явно учитываются.
- [ ] Исходные файлы vault не изменяются и не удаляются.
- [ ] EDA-выводы объясняют влияние распределений на будущий chunking.
- [ ] Артефакт не требует PostgreSQL.

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

14–22 часа разработки, EDA и анализа.

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
| Corpus files | not measured | Будет измерено после реализации |

## Review

### Completed

- Sprint scope согласован.
- Временный artifact выбран: `artifacts/corpus_inventory.json`.

### Not Completed

- Implementation не начата.

### Changed Decisions

- PostgreSQL исключён из Sprint 3; permanent storage планируется в Phase 2.

### Technical Debt

- JSON inventory будет заменён или дополнен production data layer после проектирования Phase 2.

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
