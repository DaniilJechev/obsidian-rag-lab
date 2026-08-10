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

## Pre-Implementation Gate

Перед началом implementation нужно подтвердить:

- Фаза 1 закрывает discovery и Markdown parsing; Sprint 3 завершает её
  inventory/EDA-часть.
- В backlog существует и остаётся в scope задача `CORPUS-003`.
- Исходный vault остаётся read-only; все артефакты пишутся только в
  `RAG_based_on_obsidian`.
- Inventory будет строиться из существующих discovery/parser contracts, а не
  повторно реализовывать поиск и Markdown parsing.
- PostgreSQL, Qdrant, embeddings и chunking не являются prerequisites этого
  sprint.
- Токенизация для inventory будет baseline-метрикой с явно записанными именем,
  версией и параметрами tokenizer; она не заменяет tokenizer будущей LLM.

## Ordered Implementation Checklist

| Шаг | Что делаем | Результат и проверка |
|---|---|---|
| 1 | Зафиксировать inventory contract и JSON schema | Поля document-level, summary, heading statistics, language, anomalies и duplicates согласованы |
| 2 | Зафиксировать правила подсчёта слов, токенов, RU/EN и heading sections | На synthetic fixtures ожидаемые значения проверяются тестами |
| 3 | Создать inventory domain structures и тестовые fixtures | Есть типизированный контракт и изолированные unit-тесты |
| 4 | Реализовать расчёт статистики одного `ParsedDocument` | Проверяются file size, words, tokens, headings, languages и anomalies |
| 5 | Добавить batch orchestration поверх discovery/parser | Все разрешённые документы обрабатываются детерминированно; ошибки учитываются и не теряют остальные документы |
| 6 | Добавить content hash и duplicate analysis | Группы одинакового содержимого воспроизводимо отражены в inventory |
| 7 | Сериализовать `artifacts/corpus_inventory.json` | JSON содержит `schema_version`, параметры запуска и реальные результаты |
| 8 | Запустить inventory на DLS1/DLS2 и проверить read-only fingerprints | Реальный artifact создан, vault до/после не изменился |
| 9 | Подготовить EDA и рекомендации для chunking/Phase 2 | Выводы опираются на реальные distributions, а не на предположения |
| 10 | Выполнить Ruff, pytest, CI и обновить evidence | Sprint document содержит только наблюдаемые результаты |

Шаги 1–2 должны быть последовательными. После фиксации contract шаг 3 можно
разрабатывать параллельно с подготовкой EDA-шаблона, но batch orchestration,
real-vault run и финальные рекомендации зависят от готового inventory contract.

## Scope

- [ ] `CORPUS-003` — подготовить corpus inventory и EDA.
- [ ] Посчитать количество файлов, слова, токены, размеры и длины заметок.
- [ ] Посчитать среднее количество слов и токенов в секциях каждого уровня
  заголовков `H1`–`H6`, а также отдельно учесть текст до первого заголовка.
- [ ] Посчитать медиану и среднее размера Markdown-файла.
- [ ] Посчитать русские и английские слова и их соотношение.
- [ ] Выявить пустые файлы, parser-related anomalies и потенциальные дубли.
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
- [ ] Статистика включает среднее число слов и токенов по уровням заголовков
  `H1`–`H6` и тексту без заголовка.
- [ ] Статистика включает средний и медианный размер файла.
- [ ] Статистика включает количество русских и английских слов и их соотношение.
- [ ] Пустые файлы, parser-related anomalies и потенциальные дубли явно
  учитываются.
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
| Mean/median file size | not measured | Байты и/или KiB; будет измерено после реализации |
| Mean words/tokens by heading level | not measured | Отдельно для `H1`–`H6` и текста без заголовка |
| Russian/English word counts and ratio | not measured | Будет измерено после реализации |

## Review

### Completed

- Sprint scope согласован.
- Временный artifact выбран: `artifacts/corpus_inventory.json`.
- В scope добавлены heading-level statistics, file-size summary и RU/EN language
  breakdown.

### Not Completed

- Implementation не начата.

### Changed Decisions

- PostgreSQL исключён из Sprint 3; permanent storage планируется в Phase 2.
- Термин `parser warnings` заменён на `parser-related anomalies`, чтобы не
  возвращать поле `warnings` в `ParsedDocument`.

### Что считается parser-related anomaly

В рамках этого sprint anomaly — это наблюдаемое отклонение или проблема
обработки, которую нужно посчитать и объяснить, но не исправлять в read-only
vault. Например:

- ошибка чтения файла;
- malformed или unclosed frontmatter;
- документ, который discovery нашёл, но parser не смог обработать;
- пустой документ;
- отсутствие текста после удаления структурных элементов;
- необычный формат, который parser пропустил или обработал не полностью.

Обычный inline-code wikilink сам по себе anomaly не считается: для текущего
корпуса он уже принят как корректный wikilink.

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
