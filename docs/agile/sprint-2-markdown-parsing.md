# Sprint 2 — Markdown Parsing

> Статус: `completed`
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

- [x] `CORPUS-002` — распарсить Markdown-структуру.
- [x] Извлечь raw text, frontmatter, headings, wikilinks и image links.
- [x] Сохранить path, filename и folder; ошибки parsing не скрывать.
- [x] Добавить fixtures и тесты для обычных, пустых и частично повреждённых заметок.

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

- [x] Parser обрабатывает Markdown-файлы из discovery layer.
- [x] Frontmatter извлекается без потери raw text.
- [x] Headings и wikilinks сохраняются структурированно.
- [x] Image links распознаются отдельно от wikilinks.
- [x] Ошибки parsing не скрываются.
- [x] Parser не изменяет исходные файлы.
- [x] Тесты покрывают основные и пограничные форматы.

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

12–18 часов разработки и обучения.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-10 | Утверждён parser contract и разделение discovery/content entities | Созданы immutable `markdown_entities.py` и `ParsedDocument` |
| 2026-08-10 | Реализован полный parser slice | Добавлено извлечение raw text, YAML frontmatter, headings, wikilinks и image links |
| 2026-08-10 | Добавлены parser integration tests | Parser-specific suite: 5 passed |
| 2026-08-10 | Выполнен manual read-only smoke-check на реальном vault | 230 файлов обнаружено и 230 распарсено; vault не изменён |

## Validation Evidence

### Commands

```text
uv run ruff check --fix .
uv run ruff check .
uv run pytest tests/test_markdown_parser.py -q --basetemp .pytest-tmp
uv run pytest -q --basetemp .pytest-tmp
uv run pytest tests/manual/test_real_vault_parser.py -q -s -m manual
uv run pytest tests/manual/test_real_vault_edge_cases.py -q -s -m manual
```

### Test and Lint Results

- Tests: parser-specific `5 passed`; full suite `19 passed, 1 skipped`;
- manual smoke-check `1 passed`; edge-case scan `1 passed`
- Lint: `passed` (`All checks passed!`)
- CI: `SUCCESS` в PR #6; GitHub Actions run `31413452964`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Parser-specific tests | 5 passed | `tests/test_markdown_parser.py` |
| Full test suite | 19 passed, 1 skipped | Existing discovery tests plus parser tests |
| Discovered Markdown files | 230 | Manual read-only smoke-check of `DLS1` and `DLS2` |
| Parsed Markdown files | 230 | Manual read-only smoke-check |
| Files with frontmatter | 0 | Manual read-only smoke-check |
| Files with headings | 187 | Manual read-only smoke-check |
| Files with wikilinks | 83 | Manual read-only smoke-check |
| Files with image links | 44 | Manual read-only smoke-check |
| Empty files | 3 | Manual read-only smoke-check |
| Vault modified | no | Size and `mtime_ns` fingerprints matched before/after |
| Wikilinks with heading targets | 0 files, 0 matches | Manual edge-case scan |
| Wikilinks with block targets | 0 files, 0 matches | Manual edge-case scan |
| Markdown links | 1 file, 7 matches | Manual edge-case scan; not part of current contract |
| Inline-code wikilinks | 11 files, 15 matches | Accepted as real wikilinks for this corpus |
| Callouts | 0 files, 0 matches | Manual edge-case scan |
| Long fenced code openers | 0 files, 0 matches | Manual edge-case scan |
| Unicode content | 225 files | Manual edge-case scan |
| CRLF line endings | 0 files | Manual edge-case scan |

## Review

### Completed

- Sprint scope согласован.
- Parser entities и `ParsedDocument` созданы в `src/rag_based_on_obsidian/corpus/markdown_entities.py`.
- Parser реализован в `src/rag_based_on_obsidian/corpus/markdown_parser.py`.
- Добавлена зависимость `PyYAML` для YAML frontmatter.
- Тесты parser добавлены в `tests/test_markdown_parser.py`.
- Проверено сохранение raw text, provenance и read-only поведения на fixtures.
- Manual parser smoke-check выполнен через `tests/manual/test_real_vault_parser.py`;
  прочитано 230 файлов из allowlist без записи в vault.
- Manual edge-case scan выполнен через `tests/manual/test_real_vault_edge_cases.py`.
- Inline-code wikilinks признаны корректными wikilinks для текущего корпуса;
  parser изменять для их исключения не требуется.

### Not Completed

- Новых незавершённых задач текущего scope нет.
- Отдельный ingestion/diagnostic report остаётся техническим долгом и перенесён
  за пределы текущего sprint.

### Changed Decisions

- `warnings` не включены в `ParsedDocument`; ошибки frontmatter не скрываются и
  представлены исключениями.
- Frontmatter является optional: при его отсутствии возвращается пустой mapping.

### Technical Debt

- Smoke-check подтвердил базовую совместимость с реальным корпусом, но не
  является исчерпывающей проверкой всех Obsidian edge cases.
- Parser пока не формирует отдельный ingestion/diagnostic report.

## Retrospective

### Что прошло хорошо

- Parser contract был выделен в отдельные immutable entities.
- Реализован полный базовый parsing scope без изменения read-only vault.
- Локальные тесты, Ruff и GitHub Actions CI прошли.
- Manual smoke-check обработал 230 файлов реального корпуса.
- Edge-case scan помог явно зафиксировать решение по inline-code wikilinks.

### Что было сложным

- Потребовалась отдельная проверка поведения parser на реальном vault.
- Windows cleanup временной pytest-директории сначала завершился
  `PermissionError`; повторный запуск с проектной `--basetemp` прошёл успешно.
- Первоначальное требование `warnings` было уточнено: warnings не входят в
  `ParsedDocument`, а parsing errors остаются observable через exceptions.

### Что изменить в следующем sprint

- Сразу использовать отдельную временную директорию для pytest на Windows.
- Для inventory заранее определить контракт статистики, версию артефакта и
  параметры запуска.
- Сохранять реальные execution evidence до открытия closeout PR.

## Completion

- [x] Definition of Done проверен.
- [x] Review проведён.
- [x] Retrospective заполнена.
- [x] Implementation PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён.

**Итоговый статус:** `completed`

**Дата завершения:** 2026-08-10
