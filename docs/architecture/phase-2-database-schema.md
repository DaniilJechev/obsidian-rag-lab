# Phase 2 Database Schema Contract

Статус: `design-approved`

Документ описывает schema contract для Phase 2. Он не создаёт таблицы
самостоятельно: реализация будет выполнена через SQLAlchemy Core и Alembic
migrations в Sprint 4.

## Общие решения

- PostgreSQL — source of truth для metadata и состояния pipeline.
- Первый полный ingestion охватывает `DLS1 + DLS2`.
- Исходный `obsidianNotes` остаётся read-only.
- Пути хранятся только как относительные значения.
- `TIMESTAMPTZ` используется для времени.
- `JSONB` используется для структурированных полей, а форма JSON проверяется
  JSON Schema на Python-слое и integration tests.
- Wikilinks хранятся в отдельной таблице `note_links`, а не списком ID внутри
  `notes`.

## Таблица `notes`

Одна строка соответствует одной обнаруженной заметке.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `note_id` | `BIGINT` identity | `PRIMARY KEY` | Внутренний стабильный ID |
| `relative_path` | `TEXT` | `NOT NULL`, `UNIQUE` | Путь вроде `DLS2/RAG.md` |
| `source_directory` | `TEXT` | `NOT NULL` | `DLS1` или `DLS2` |
| `title` | `TEXT` | `NOT NULL` | Заголовок с filename fallback |
| `content_hash` | `TEXT` | `NOT NULL` | SHA-256 raw content для idempotency |
| `file_size_bytes` | `BIGINT` | `NOT NULL`, `>= 0` | Размер файла в байтах |
| `character_count` | `INTEGER` | `NOT NULL`, `>= 0` | Количество символов |
| `word_count` | `INTEGER` | `NOT NULL`, `>= 0` | Количество слов |
| `language_statistics` | `JSONB` | `NOT NULL`, default `{}` | Языковые counts/ratios |
| `parse_status` | `TEXT` | `NOT NULL`, controlled values | Результат Markdown parser |
| `anomalies` | `JSONB` | `NOT NULL`, default `[]` | Проверенные anomalies |
| `source_mtime` | `TIMESTAMPTZ` | nullable | Время изменения исходного файла |
| `parser_version` | `TEXT` | `NOT NULL` | Версия parser |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание строки в БД |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Последнее обновление строки |

`note_id` не получает отдельный `UNIQUE`: `PRIMARY KEY` уже означает
`UNIQUE + NOT NULL`.

`source_mtime` не заменяет `content_hash`: timestamp может измениться без
изменения содержимого. Hash является основным признаком content identity.

`created_at`, `updated_at` и `source_mtime` имеют разные смыслы:

```text
source_mtime → изменение Markdown-файла
created_at    → первая запись note в PostgreSQL
updated_at    → последнее изменение строки note в PostgreSQL
```

## JSONB contracts

### `language_statistics`

Минимальный shape:

```json
{
  "russian": 59980,
  "english": 13196,
  "mixed_or_other": 180,
  "unknown": 0,
  "total_classified": 73356
}
```

Все count-поля — integer `>= 0`. Ratios, если сохраняются, должны быть
числами `>= 0` и `<= 1`. Необязательные категории могут отсутствовать, если
они равны нулю и это согласовано с serializer contract.

### `anomalies`

Shape — массив строковых anomaly codes:

```json
[
  "empty_document",
  "no_text_after_structure"
]
```

Отсутствие anomalies означает проверенный пустой массив `[]`, а не неизвестное
значение `NULL`.

JSON Schema-файлы и Python validation будут добавлены рядом с реализацией
database contract; PostgreSQL хранит validated payload как `JSONB`.

## Таблица `note_links`

Одна строка соответствует одной wikilink-связи из source note.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `link_id` | `BIGINT` identity | `PRIMARY KEY` | ID связи |
| `source_note_id` | `BIGINT` | `NOT NULL`, FK → `notes` | Откуда идёт ссылка |
| `target_note_id` | `BIGINT` | nullable, FK → `notes` | Разрешённая target note |
| `target_reference` | `TEXT` | `NOT NULL` | Raw target из wikilink |
| `display_text` | `TEXT` | nullable | Явный alias/display text |
| `link_type` | `TEXT` | `NOT NULL` | Тип связи |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Время записи строки связи в БД |

Ограничения и поведение:

```text
source_note_id → FOREIGN KEY notes(note_id) ON DELETE CASCADE
target_note_id → FOREIGN KEY notes(note_id) ON DELETE SET NULL
UNIQUE(source_note_id, target_reference, link_type)
```

Эти три ограничения читаются так:

```text
source_note_id → FOREIGN KEY notes(note_id) ON DELETE CASCADE
```

`source_note_id` — заметка, из текста которой вышла ссылка. Она обязательна и
должна существовать в `notes`. Если source note удалить из базы, её link rows
удаляются автоматически: связи без источника не имеют смысла.

```text
target_note_id → FOREIGN KEY notes(note_id) ON DELETE SET NULL
```

`target_note_id` — разрешённая заметка, на которую указывает ссылка. Она может
быть `NULL`, если target пока не найден. Если известную target note удалить,
сама link row сохраняется вместе с `target_reference`, но `target_note_id`
становится `NULL`. Так мы не теряем исходную ссылку и можем разрешить её позже.

```text
UNIQUE(source_note_id, target_reference, link_type)
```

Одна и та же связь одного типа из одной source note не может быть записана
дважды. Например, две одинаковые строки с `source_note_id = 1`,
`target_reference = "BERT"` и `link_type = "wikilink"` будут считаться
дубликатом. Но ссылки `"BERT"` и `"BERT#Attention"` могут существовать
одновременно, потому что это разные `target_reference`.

`target_note_id` nullable намеренно. Ссылка может быть unresolved, вести за
пределы allowlist или встретиться до того, как target note записана в БД.
`target_reference` сохраняет исходное значение и никогда не теряется из-за
неудачного resolution.

Поток сохранения двухфазный:

```text
parse  → сохранить source_note_id + target_reference
resolve → заполнить target_note_id, если target найден
```

В Sprint 4 не реализуются graph traversal, graph embeddings и graph-enhanced
retrieval.

### Почему `display_text` nullable

У wikilink может не быть отдельного display alias:

```text
[[BERT]]
```

В этом случае `target_reference = "BERT"`, а отдельного display text нет,
поэтому `display_text = NULL` корректно означает «alias не задан». Для ссылки:

```text
[[BERT|энкодер BERT]]
```

будет сохранено:

```text
target_reference = "BERT"
display_text = "энкодер BERT"
```

Не нужно автоматически записывать `target_reference` в `display_text`: тогда
мы потеряем различие между отсутствующим alias и явно указанным alias.

### Возможные `link_type`

Для Sprint 4 фиксируем небольшой контролируемый набор:

```text
wikilink
wikilink_heading
wikilink_block
markdown_link
```

- `wikilink` — обычный `[[Note]]`;
- `wikilink_heading` — ссылка с heading subpath, например `[[Note#Section]]`;
- `wikilink_block` — ссылка на block reference, например `[[Note#^block-id]]`;
- `markdown_link` — обычная Markdown-ссылка, если parser решит считать её
  связью между notes.

Image embeds не являются `note_links`: их следует хранить отдельным типом
структурных/media references, потому что target может быть изображением, а не
заметкой. В первой реализации можно начать только с `wikilink`, а остальные
типы оставить допустимыми для будущих parser outputs.

### Что означает `created_at` у связи

`created_at` — это время, когда строка связи была записана в PostgreSQL:

```text
parser извлёк link
    → ingestion/resolution записал note_links row
    → created_at = время этой записи
```

Это не время создания ссылки автором в Obsidian: такого надёжного timestamp в
Markdown обычно нет. Если связь будет удалена и затем обнаружена снова, новая
строка может получить новый `created_at`. Историю появления/исчезновения
связей, если она понадобится, добавим отдельным versioned ingestion contract.

## Таблица `ingestion_runs`

Одна строка — один запуск ingestion pipeline для заданного corpus scope.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `run_id` | `BIGINT` identity | `PRIMARY KEY` | ID запуска |
| `started_at` | `TIMESTAMPTZ` | `NOT NULL` | Начало запуска |
| `finished_at` | `TIMESTAMPTZ` | nullable | Завершение; NULL у незаконченного run |
| `status` | `TEXT` | `NOT NULL` | `running`, `completed`, `failed`, `partial` |
| `corpus_scope` | `TEXT` | `NOT NULL` | Например `DLS1+DLS2` |
| `documents_total` | `INTEGER` | `NOT NULL`, default `0`, `>= 0` | Найдено документов |
| `documents_succeeded` | `INTEGER` | `NOT NULL`, default `0`, `>= 0` | Успешно обработано |
| `documents_failed` | `INTEGER` | `NOT NULL`, default `0`, `>= 0` | Ошибки обработки |
| `documents_skipped` | `INTEGER` | `NOT NULL`, default `0`, `>= 0` | Пропущено по idempotency |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание run row |

Инварианты:

```text
finished_at IS NULL  → status = running
finished_at IS NOT NULL → status != running
documents_succeeded + documents_failed + documents_skipped
    <= documents_total
```

## Таблица `index_versions`

Одна строка — согласованный набор версий pipeline-компонентов.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `index_version_id` | `BIGINT` identity | `PRIMARY KEY` | ID версии |
| `parser_version` | `TEXT` | `NOT NULL` | Версия parser |
| `chunking_version` | `TEXT` | `NOT NULL` | `planned` до Phase 3 |
| `embedding_model` | `TEXT` | nullable | Модель будущих embeddings |
| `embedding_version` | `TEXT` | nullable | Версия embedding model |
| `embedding_parameters` | `JSONB` | `NOT NULL`, default `{}` | Параметры модели |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание version row |

Одинаковый набор компонентов должен иметь один version record. В Sprint 4
достаточно зафиксировать contract и unique identity constraint; выбор
embedding model остаётся будущим решением.

## Таблица `ingestion_states`

Одна строка — результат обработки конкретной note в конкретном run.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `state_id` | `BIGINT` identity | `PRIMARY KEY` | ID результата |
| `note_id` | `BIGINT` | `NOT NULL`, FK → `notes` | Обрабатываемая note |
| `run_id` | `BIGINT` | `NOT NULL`, FK → `ingestion_runs` | Запуск |
| `index_version_id` | `BIGINT` | `NOT NULL`, FK → `index_versions` | Версии компонентов |
| `content_hash` | `TEXT` | `NOT NULL` | Hash на момент обработки |
| `parser_version` | `TEXT` | `NOT NULL` | Фактически применённый parser |
| `status` | `TEXT` | `NOT NULL` | `discovered`, `parsed`, `failed`, `stale` |
| `error_type` | `TEXT` | nullable | Классификация ошибки |
| `error_message` | `TEXT` | nullable | Диагностика ошибки |
| `processed_at` | `TIMESTAMPTZ` | nullable | Завершение обработки note |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание state row |

`ingestion_states` — историческая таблица результатов, поэтому у одной note
может быть много state rows в разных runs. Для текущего состояния используется
последний актуальный результат, а не перезапись истории.

Минимальное ограничение:

```text
UNIQUE(note_id, run_id)
```

Оно запрещает обработать одну note дважды внутри одного run.

## Таблица `chunks`

Одна строка — будущий retrieval chunk, принадлежащий note.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `chunk_id` | `BIGINT` identity | `PRIMARY KEY` | ID chunk |
| `note_id` | `BIGINT` | `NOT NULL`, FK → `notes` | Parent note |
| `chunk_index` | `INTEGER` | `NOT NULL`, `>= 0` | Порядок внутри note |
| `text` | `TEXT` | `NOT NULL` | Текст chunk |
| `section_title` | `TEXT` | nullable | Заголовок секции |
| `section_level` | `SMALLINT` | nullable, `1..6` | H1–H6 |
| `section_path` | `JSONB` | `NOT NULL`, default `[]` | Путь по headings |
| `section_type` | `TEXT` | `NOT NULL` | `pre_heading`, `heading_body`, etc. |
| `start_offset` | `INTEGER` | nullable, `>= 0` | Offset в source view |
| `end_offset` | `INTEGER` | nullable, `>= 0` | Конец source span |
| `word_count` | `INTEGER` | `NOT NULL`, `>= 0` | Word count |
| `token_count` | `INTEGER` | `NOT NULL`, `>= 0` | Baseline/model token count |
| `chunking_version` | `TEXT` | `NOT NULL` | Версия splitter |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание chunk row |

Ограничение для versioned chunks:

```text
UNIQUE(note_id, chunking_version, chunk_index)
```

Генерация chunks относится к Phase 3; в Sprint 4 создаётся только schema
contract и relationship `notes → chunks`.

## Будущие operational/evaluation таблицы

Эти таблицы описываются сейчас как расширяемый contract, но их полноценная
логика не входит в Sprint 4.

### `eval_items`

Одна строка — один вопрос в gold evaluation set.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `eval_item_id` | `BIGINT` identity | `PRIMARY KEY` | ID вопроса |
| `question` | `TEXT` | `NOT NULL` | Текст вопроса |
| `corpus_scope` | `TEXT` | `NOT NULL` | На каком корпусе размечено |
| `relevant_note_ids` | `JSONB` | `NOT NULL`, default `[]` | Relevant notes |
| `relevant_chunk_ids` | `JSONB` | `NOT NULL`, default `[]` | Relevant chunks |
| `dataset_version` | `TEXT` | `NOT NULL` | Версия набора |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание item |

### `query_logs`

Одна строка — один пользовательский/retrieval query.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `query_id` | `BIGINT` identity | `PRIMARY KEY` | ID query |
| `question` | `TEXT` | `NOT NULL` | Исходный запрос пользователя |
| `prompt_text` | `TEXT` | nullable | Итоговый prompt, отправленный LLM |
| `response_text` | `TEXT` | nullable | Финальный текст ответа LLM |
| `retrieval_version` | `TEXT` | `NOT NULL` | Версия retrieval pipeline |
| `latency_ms` | `INTEGER` | nullable, `>= 0` | Latency |
| `result_count` | `INTEGER` | `NOT NULL`, default `0`, `>= 0` | Число результатов |
| `status` | `TEXT` | `NOT NULL` | `success` или `failed` |
| `error_type` | `TEXT` | nullable | Ошибка |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Время query |

`question` — исходный запрос пользователя. `prompt_text` — уже собранный
контекстный prompt после retrieval, переданный генеративной модели. Это не
одно и то же: prompt может содержать system instructions, найденные chunks,
citations и question.

`response_text` nullable, потому что retrieval или LLM могут завершиться
ошибкой до создания ответа. `prompt_text` также nullable, если ошибка произошла
до этапа сборки prompt.

Prompt и response могут содержать чувствительные данные или большой объём
текста. До полноценной реализации `query_logs` нужно отдельно определить
redaction, retention, доступ и максимальный размер логируемых значений.

### `model_metadata`

Одна строка — описание модели или tokenizer baseline.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `model_id` | `BIGINT` identity | `PRIMARY KEY` | ID модели |
| `provider` | `TEXT` | `NOT NULL` | `local`, `openrouter`, etc. |
| `model_name` | `TEXT` | `NOT NULL` | Имя модели |
| `model_version` | `TEXT` | nullable | Версия |
| `model_type` | `TEXT` | `NOT NULL` | `embedding`, `llm`, `tokenizer` |
| `dimension` | `INTEGER` | nullable, `> 0` | Vector dimension |
| `parameters` | `JSONB` | `NOT NULL`, default `{}` | Дополнительные параметры |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание metadata |

### `cache`

Одна строка — значение кэша с версией вычисляющего pipeline.

| Поле | PostgreSQL type | Ограничения | Назначение |
|---|---|---|---|
| `cache_key` | `TEXT` | `PRIMARY KEY` | Детерминированный ключ |
| `cache_type` | `TEXT` | `NOT NULL` | `exact`, `semantic`, etc. |
| `value` | `JSONB` | `NOT NULL` | Cached result |
| `pipeline_version` | `TEXT` | `NOT NULL` | Версия вычисления |
| `expires_at` | `TIMESTAMPTZ` | nullable | TTL; NULL означает без TTL |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL`, default `now()` | Создание cache row |

## Scope clarification

В Sprint 4 реализуются migrations и schema для:

```text
notes
note_links
ingestion_runs
ingestion_states
index_versions
chunks
```

`eval_items`, `query_logs`, `model_metadata` и `cache` пока являются
расширяемыми contracts: их поля зафиксированы для совместимости, но
полноценная operational/evaluation logic переносится в последующие фазы.

## Связи

```text
notes
  ├──< ingestion_states >── ingestion_runs
  ├──< ingestion_states >── index_versions
  ├──< chunks
  └──< note_links >── notes
```

## Что проверяем в Sprint 4

- migrations создают schema на пустом PostgreSQL;
- повторный `alembic upgrade head` безопасен;
- duplicate `relative_path` отклоняется;
- invalid foreign keys отклоняются;
- `note_links` поддерживает resolved и unresolved links;
- JSONB payloads проходят JSON Schema validation;
- `notes → chunks` relationship готов для Phase 3;
- `obsidianNotes` не изменяется.
