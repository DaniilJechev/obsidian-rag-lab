# Sprint 1 — Safe Corpus Discovery

> Статус: `planned`
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

- [ ] `CORPUS-001` — реализовать безопасное обнаружение Markdown-файлов только в `DLS1/` и `DLS2/`.
- [ ] Зафиксировать контракт результата discovery и детерминированный порядок файлов.
- [ ] Добавить тесты для разрешённых, запрещённых и пограничных путей.

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

- [ ] Discovery принимает только `DLS1` и `DLS2`.
- [ ] Файлы вне allowlist отклоняются.
- [ ] Path traversal и похожие пограничные пути не обходят allowlist.
- [ ] Результат поиска детерминирован и содержит только `.md`-файлы.
- [ ] Discovery не создаёт, не изменяет, не перемещает и не удаляет файлы в vault.
- [ ] Негативные сценарии покрыты тестами.

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
- CI: `not run`

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

- Sprint DoD ещё не прошёл формальный аудит.
- Ветка ещё не опубликована на GitHub.
- Pull Request ещё не создан.

### Changed Decisions

- На Windows symlink-тест требует запуска PowerShell с повышенными правами;
  в обычном терминале он может быть skipped.

### Technical Debt

- После DoD-аудита нужны push ветки, Pull Request, review/CI, merge и closeout.

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
