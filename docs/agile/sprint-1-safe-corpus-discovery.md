# Sprint 1 — Safe Corpus Discovery

> Статус: `completed`
>
> Ветка: `sprint/1-safe-corpus-discovery`
>
> Связанная фаза roadmap: `Фаза 1`

## Sprint Goal

Создать проверяемый read-only discovery layer, который находит только Markdown-файлы в разрешённых каталогах `obsidianNotes/DLS1/` и `obsidianNotes/DLS2/`.

## Why

Discovery — первая граница безопасности ingestion pipeline. До парсинга нужно
доказать, что система читает только allowlist-пути и не может случайно
изменить или прочитать запрещённые каталоги.

## Scope

- [x] `CORPUS-001` — реализовать безопасное обнаружение Markdown-файлов только в `DLS1/` и `DLS2/`.
- [x] Зафиксировать контракт результата discovery и детерминированный порядок файлов.
- [x] Добавить тесты для разрешённых, запрещённых и пограничных путей.

## Out of Scope

- Markdown parsing, frontmatter, headings и wikilinks.
- Corpus statistics, EDA и `corpus_inventory.json`.
- PostgreSQL, Qdrant, chunking и embeddings.
- Создание GitHub Milestone/Issues в рамках локального sprint-документа.

## Expected Artifacts

- `src/` discovery-модуль — read-only поиск Markdown-файлов.
- `tests/` — unit-тесты allowlist и path boundaries.
- Конфигурационный контракт разрешённых директорий.
- Обновлённый execution log и validation evidence.

## Acceptance Criteria

- [x] Discovery принимает только `DLS1` и `DLS2`.
- [x] Файлы вне allowlist отклоняются.
- [x] Path traversal и похожие пограничные пути не обходят allowlist.
- [x] Результат поиска детерминирован и содержит только `.md`-файлы.
- [x] Discovery не создаёт, не изменяет, не перемещает и не удаляет файлы в vault.
- [x] Негативные сценарии покрыты тестами.

## Definition of Done

- [x] Все задачи Scope выполнены или явно перенесены в backlog.
- [x] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит после публикации изменений.
- [x] Read-only vault не изменён.
- [x] Секреты не добавлены в Git.
- [x] Sprint-документ содержит реальные результаты и ограничения.
- [x] Пользователь подтвердил завершение спринта.

## Estimate

8–12 часов разработки и обучения.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-09 | Реализован discovery layer и добавлены safety tests | Unit-тесты прошли: 15 passed |
| 2026-08-09 | Выполнен smoke test read-only vault | Найдено 230 `.md`-файлов: DLS1 — 100, DLS2 — 130 |

## Validation Evidence

### Commands

```text
uv run pytest -q
uv run ruff check .
uv run python -c "load_config(); discover_markdown_files(...)"
```

### Test and Lint Results

- Tests: `15 passed` (Windows PowerShell с правами администратора; symlink test выполнен)
- Lint: `passed` (`All checks passed!`)
- CI: `pass` — GitHub Actions job `Lint and test`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Discovered Markdown files | 230 | Read-only smoke test реального vault |
| DLS1 Markdown files | 100 | Read-only smoke test реального vault |
| DLS2 Markdown files | 130 | Read-only smoke test реального vault |

## Review

### Completed

- Sprint scope согласован.
- Discovery implementation создана в `src/rag_based_on_obsidian/corpus/discovery.py`.
- `DiscoveredFile` использован как структурированный discovery result.
- Allowlist загружается через `.env` и `AppConfig`.
- Unit и safety tests добавлены.
- Реальный vault проверен без изменения исходных файлов.

### Not Completed

- Локальная рабочая копия ещё не синхронизирована с merge commit в `origin/main`;
  это post-merge рабочее действие, не незавершённая задача Sprint 1.

### Changed Decisions

- На Windows symlink-тест требует запуска PowerShell с повышенными правами;
  в обычном терминале он может быть skipped.

### Technical Debt

- Milestone Sprint 1 имеет `open_issues: 0`, но пока остаётся открытым на GitHub;
  его закрытие вынесено в отдельное административное действие.

## Retrospective

### Что сработало

- Последовательность implementation → tests → lint → evidence → PR позволила
  отделить функциональную работу от административного closeout.
- Read-only smoke test реального vault подтвердил результат discovery: 230 файлов,
  из них 100 в `DLS1` и 130 в `DLS2`.

### Сложности

- На Windows symlink-тест потребовал запуска PowerShell с повышенными правами.
- GitHub CLI в установленной версии не предоставляет отдельную команду
  `gh milestone`, поэтому состояние Milestone проверялось через GitHub API.

### Изменения для следующего спринта

- Перед началом реализации синхронизировать локальную `main` с `origin/main`.
- Для каждого спринта заранее связывать локальный документ, GitHub Milestone и
  атомарную Issue.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.

**Итоговый статус:** `completed`

**Дата завершения:** 2026-08-09
