# Recommendations for Phase 2 and Chunking

Документ подготовлен по результатам Sprint 3 Corpus Inventory и EDA.
Он разделяет наблюдаемые факты, инженерные рекомендации и гипотезы, которые
нужно проверить controlled experiments. Финальный `chunk_size` здесь не
выбирается.

Источник данных:

- `artifacts/corpus_inventory.json`;
- `artifacts/eda/corpus_eda.md`;
- корпус: `DLS1/` + `DLS2/`;
- реальный запуск: `230` документов, `230` parsed, `0` failed;
- read-only verification: `Vault modified: no`.

## 1. Наблюдаемые факты

### Документы

| Metric | Value |
|---|---:|
| Documents | 230 |
| Mean file size | 4313.79 bytes |
| Median file size | 3496 bytes |
| Median words | 272 |
| P95 words | 789.50 |
| Maximum words | 1512 |
| Duplicate groups | 1 |
| Duplicate documents | 3 |
| Empty documents | 3 |

### Paragraph blocks

| Metric | Value |
|---|---:|
| Total blocks | 3331 |
| Median words | 17 |
| Mean words | 21.16 |
| P90 words | 44 |
| P95 words | 54 |
| Maximum words | 194 |
| Empty rate | 1.62% |

По уровням:

| Level | Blocks | Median words | Mean words | P95 words | Empty rate |
|---|---:|---:|---:|---:|---:|
| `pre-heading` | 298 | 24 | 28.93 | 67.15 | 0.67% |
| `H1` | 7 | 0 | 0 | 0 | 100.00% |
| `H2` | 254 | 19 | 22.60 | 54 | 3.94% |
| `H3` | 2362 | 17 | 20.60 | 52 | 1.23% |
| `H4` | 410 | 15 | 18.22 | 45 | 1.46% |
| `all_levels` | 3331 | 17 | 21.16 | 54 | 1.62% |

## 2. Chunking recommendations

### 2.1 Использовать heading-aware boundaries

Рекомендуемый структурный путь:

```text
document
  -> heading section
    -> paragraph blocks
```

Heading нужно сохранять как metadata и boundary, но не превращать всю
`full_span`-секцию в один chunk: `full_span` включает дочерние headings и может
быть значительно длиннее собственного `direct_body`.

Минимальные metadata будущего chunk:

```text
note_id
chunk_index
heading_level
heading_title
section_path
section_type
```

### 2.2 Использовать paragraph blocks как базовые units

Медиана paragraph равна `17` словам, поэтому каждый paragraph нельзя
автоматически делать отдельным retrieval chunk: это приведёт к большому числу
слишком коротких chunks.

Начальная гипотеза:

```text
короткие соседние paragraphs -> объединять
длинные paragraphs -> дополнительно split-ить
heading metadata -> сохранять у объединённого chunk
```

Это гипотеза, а не окончательная стратегия. Её нужно проверить на eval-наборе.

### 2.3 Сравнить candidate sizes, а не выбрать один заранее

Roadmap Phase 3 предлагает controlled comparison:

```text
256 / 512 / 1024 model tokens
```

Для каждого варианта нужно сравнить минимум:

- количество chunks;
- median/p95 chunk length;
- долю слишком коротких chunks;
- долю chunks, пересекающих heading boundary;
- retrieval recall;
- precision/MRR или nDCG;
- latency и storage size.

Текущий `token_count` — word-level baseline. Он не заменяет tokenizer будущей
embedding/LLM-модели, поэтому точные model-token limits пока не фиксируем.

### 2.4 Не создавать chunks из пустых headings

`H1` имеет `100% empty-rate` в текущем inventory. Такой heading следует:

- сохранять как structural metadata;
- использовать как ancestor/boundary;
- не индексировать как самостоятельный text chunk.

Уровни, которых нет в документе, не должны создавать фиктивные chunks.

### 2.5 Учесть glossary до первого heading

Текущая EDA видит glossary как `pre-heading`, но не выделяет его семантически.
Для chunking нужен будущий `section_type`:

```text
glossary
```

Предлагаемая политика для экспериментов:

| Glossary size | Candidate policy |
|---|---|
| Small | Объединить с первым содержательным chunk |
| Medium | Отдельный glossary chunk и metadata link |
| Large | Разбить на chunks по группам терминов |

До реализации glossary detection это остаётся deferred item.

### 2.6 Сохранить wikilinks как graph metadata

Wikilinks не следует автоматически добавлять в text каждого chunk: это может
раздуть контекст и внести нерелевантный текст. На первом варианте сохранять:

```text
linked_note_ids
linked_note_titles
```

как metadata или graph hint. 1-hop соседние заметки можно сравнить отдельной
абляцией в Phase 3/Phase 5.

### 2.7 Отдельно обрабатывать структурные блоки

Paragraph blocks содержат списки, изображения и code blocks. Поэтому будущий
splitter должен сохранять признаки:

```text
has_code
has_image
has_wikilink
has_list
has_blockquote
```

Code-heavy blocks не следует безусловно разрывать посередине. Image-only blocks
нужно либо связывать с caption/context, либо обрабатывать отдельным типом.

## 3. Recommendations for Phase 2

Phase 2 — PostgreSQL как source of truth для metadata, ingestion state, eval,
logs и cache. Vector store и embeddings не являются частью текущего Sprint 3.

### 3.1 Таблица `notes`

Предусмотреть поля:

```text
note_id
relative_path
source_directory
title
content_hash
file_size_bytes
character_count
word_count
language_statistics
parse_status
anomalies
source_mtime
parser_version
ingested_at
```

`content_hash` нужен для idempotent ingestion: неизменившиеся notes не должны
переобрабатываться без причины.

### 3.2 Таблица `chunks`

Даже если chunking реализуется в Phase 3, schema Phase 2 должна предусмотреть:

```text
chunk_id
note_id
chunk_index
text
section_title
section_level
section_path
section_type
start_offset
end_offset
word_count
token_count
chunking_version
```

Полный text heading spans сейчас не сохраняется в inventory; chunking contract
должен получать его из parser output или отдельного section-record слоя.

### 3.3 Ingestion state

Нужна идемпотентная state-модель:

```text
note_id
content_hash
parser_version
chunking_version
embedding_version
status
error_type
processed_at
```

Кандидаты на `status`:

```text
discovered
parsed
chunked
embedded
failed
stale
```

### 3.4 Versioned index

`index_version` должен учитывать как минимум:

```text
parser_version
chunking_version
embedding_model_version
embedding_parameters
```

Иначе после изменения splitter или embedding model можно смешать
несовместимые chunks/embeddings.

### 3.5 Metadata filters

Из EDA и roadmap следуют следующие candidate filters:

```text
folder
lecture
tags
heading_level
section_type
language
```

Возможные значения `section_type`:

```text
pre_heading
glossary
heading_body
paragraph
code
list
```

`glossary` пока является будущим типом, а не уже реализованным inventory
признаком.

## 4. Corpus scope decision

Текущая EDA выполнена для `DLS1 + DLS2`, хотя roadmap Phase 1 описывает
первоначальный v1 как `DLS2` с возможным выбранным DLS1.

Рекомендуемая политика:

```text
EDA: DLS1 + DLS2
RAG v1 ingestion: сначала DLS2
DLS1: comparative/additional corpus
```

Это снижает начальную сложность retrieval evaluation, сохраняя DLS1 для
сравнения и будущего расширения. Это решение нужно подтвердить перед началом
Phase 2/Phase 3.

## 5. Deferred items

Следующие задачи не являются завершёнными результатами Sprint 3:

- glossary detection и отдельная glossary policy;
- tokenizer конкретной embedding-модели;
- tokenizer конечной LLM;
- сохранение полного текста heading spans в chunking contract;
- controlled experiments для `256/512/1024`;
- eval-набор query → relevant chunks;
- retrieval metrics;
- финальный `chunk_size` и overlap;
- PostgreSQL schema implementation и migration.

## 6. Recommended next sequence

1. Выполнить `sprint-dod-check` с учётом этого документа.
2. Подтвердить corpus scope: DLS2-only для RAG v1 или DLS1+DLS2.
3. В Phase 2 спроектировать PostgreSQL schema и ingestion state.
4. В Phase 3 реализовать несколько chunking candidates.
5. Создать небольшой gold/eval set.
6. Сравнить chunk sizes, overlap и glossary policies по retrieval metrics.

До controlled evaluation нельзя объявлять конкретный chunk size production
решением.
