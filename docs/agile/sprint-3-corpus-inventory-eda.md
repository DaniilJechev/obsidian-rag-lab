# Sprint 3 — Corpus Inventory and EDA

> Статус: `implementation-complete`
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
- Разрешено собрать статистику несколькими tokenizer baselines; результаты
  каждого tokenizer хранятся отдельно и не смешиваются с `word_count`.

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

### Multi-tokenizer baseline

Inventory может считать token statistics для нескольких tokenizer baselines.
Минимальный набор:

- `regex_word_tokenizer` — контролируемый word-level baseline;
- tokenizer выбранной embedding-модели — после выбора модели для Phase 4;
- tokenizer выбранной LLM/API-модели — после выбора модели генерации.

Для каждого tokenizer обязательно сохраняются:

- стабильное имя baseline;
- тип (`word` или `model`);
- имя и версия библиотеки;
- имя и версия модели, если tokenizer model-based;
- параметры запуска;
- token counts отдельно от других baselines.

В document-level statistics значения не объединяются:

```json
{
  "word_count": 1200,
  "token_counts": {
    "regex_word_tokenizer": 1200,
    "embedding_tokenizer": 1540,
    "llm_tokenizer": 1625
  }
}
```

Если конкретная embedding- или LLM-модель ещё не выбрана, Sprint 3 всё равно
может выполнить word-level baseline и оставить model-based baselines явно
`planned`, а не подставлять выдуманные результаты. Точные tokenizer models и
зависимости выбираются перед их реализацией; их добавление не должно менять
основной inventory contract.

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
- [ ] Для каждого доступного tokenizer baseline token statistics считаются и
  сохраняются отдельно с именем, версией и параметрами.
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
| 2026-08-11 | Inventory baseline | Добавлены document/corpus statistics, duplicate analysis и JSON serialization |
| 2026-08-11 | Real-vault inventory | `230` документов обнаружено и распарсировано; `0` failed; `Vault modified: no` |
| 2026-08-11 | EDA implementation | Отдельные PNG, Markdown report с числовыми таблицами, paragraph/heading distributions и chunking implications |
| 2026-08-11 | Cursor preview support | `.cursorignore` открывает только `artifacts/eda/**`; report использует relative Markdown image links |

## Validation Evidence

### Commands

```powershell
uv run ruff check .
uv run pytest -q -m "not manual" --basetemp .pytest-tmp-eda
uv run pytest tests/manual/test_real_vault_inventory.py -q -s -m manual --basetemp .pytest-tmp-eda
uv run python -m rag_based_on_obsidian.corpus.eda
```

### Test and Lint Results

- Ruff: `All checks passed`
- Non-manual tests: `31 passed, 1 skipped, 3 deselected`
- Manual real-vault inventory: `1 passed`
- Real-vault inventory: `230` discovered, `230` parsed, `0` failed
- Duplicate analysis: `1` group, `3` duplicate documents
- Anomalies: `empty_document: 3`
- Read-only check: `Vault modified: no`
- CI: `Lint and test — pass` в [PR #9](https://github.com/DaniilJechev/obsidian-rag-lab/pull/9)

### Metrics

| Metric | Value | Context |
|---|---:|---|
| Corpus files | 230 | 230 parsed, 0 failed |
| Mean/median file size | 4313.79 / 3496 bytes | all parsed documents |
| Document words | mean 318.92; median 272; p95 789.50 | min 0, max 1512 |
| Paragraph words | mean 21.16; median 17; p95 54 | 3331 paragraph blocks |
| RU/EN words | 59980 / 13196 | 81.77% RU, 17.99% EN; mixed/other 0.24% |
| Duplicate groups/documents | 1 / 3 | SHA-256 content hash groups |
| Empty documents | 3 | 1.30% of 230 documents |

## Review

### Completed

- Inventory contract, single-document statistics и batch orchestration реализованы.
- Duplicate analysis, anomaly accounting и JSON serialization реализованы.
- EDA создаёт отдельные PNG и Markdown report с числовыми таблицами.
- Paragraph blocks анализируются по `pre-heading`, `H1`–`H6` и `all_levels`.
- Отсутствующие heading levels исключаются; пустые уровни сохраняются через `empty-rate`.
- Реальный запуск на DLS1/DLS2 завершён без изменения vault.
- Ruff и non-manual tests проходят.
- Временный artifact выбран: `artifacts/corpus_inventory.json`.
- В scope добавлены heading-level statistics, file-size summary и RU/EN language
  breakdown.

### Not Completed

- Model-based tokenizer baselines не добавлялись: embedding/LLM models для
  следующей фазы ещё не выбраны.

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
- Текущий `token_count` — контролируемый word baseline, а не tokenizer
  конкретной embedding/LLM-модели.
- Glossary до первого heading пока классифицируется как `pre-heading`;
  отдельный `glossary` block остаётся backlog item для chunking slice.
- В inventory сохраняются агрегаты heading statistics и paragraph blocks, но
  не полный текст каждого heading span.

## Retrospective

PNG полезны для визуальных хвостов и выбросов, но Cursor надёжнее анализирует
EDA через Markdown tables. Поэтому `corpus_eda.md` содержит relative image links
и точные numeric tables.

## Completion

- [x] Definition of Done проверен по локальным и remote evidence.
- [x] Review evidence проведён по реальному inventory и EDA report.
- [x] Retrospective заполнена.
- [x] Implementation commit, PR, CI и merge выполнены.
- [x] `CORPUS-003` закрыт в backlog и GitHub Issue #8 закрыт после merge.
- [x] Пользователь подтвердил завершение Sprint 3.

**Итоговый статус:** `completed`

**Дата завершения Sprint:** 2026-08-11
