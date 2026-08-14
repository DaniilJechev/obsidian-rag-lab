# Phase 3 — Chunking Architecture

Статус документа: `Sprint 7 implementation evidence`

## Цель Phase 3

Получить воспроизводимые structural chunks для заметок `DLS1` и `DLS2`,
сохраняя heading context, character offsets, происхождение секции и версии
pipeline. Phase 3 подготавливает данные для embeddings в Phase 4.

Phase 3 разделена на три последовательных sprint-а:

1. Sprint 7: `ParsedDocument → typed blocks → SectionTree → LangChain Document`.
2. Sprint 8: recursive structural splitting и versioned chunk persistence.
3. Sprint 9: controlled YAML-driven experiments и выбор baseline.

В Phase 3 не входят embeddings, Qdrant, BM25/RRF, retrieval evaluation,
FastAPI, LLM и LangGraph.

## Sprint 7 structural contract

### Typed blocks

Markdown представляется последовательностью immutable domain records:

```text
tuple[MarkdownBlock, ...]
```

Текущие block types:

- `heading`;
- `paragraph`;
- `code`;
- `list`;
- `table`;
- `pre_heading`.

Каждый `MarkdownBlock` содержит `block_id`, `block_type`, исходный `text`,
character offsets `[start_offset, end_offset)` и metadata. Wikilinks являются
metadata/source references, а не отдельными runtime Documents.

### SectionTree

`SectionTree` строится из parsed Markdown и содержит synthetic root и
`SectionNode`-ы. Узел хранит:

- `section_id`;
- `section_type`;
- `title` и `display_title`;
- `level`;
- `section_path`;
- `direct_body`;
- ordered `blocks`;
- `start_offset` и `end_offset`;
- `parent_section_id`;
- `previous_sibling_id` и `next_sibling_id`;
- `children`;
- source metadata.

Offsets — Python character coordinates с полуинтервалом:

```text
raw_text[start_offset:end_offset]
```

должен указывать на соответствующий исходный фрагмент.

Особые случаи:

- текст до первого heading получает `section_type = "pre_heading"`;
- heading без текста получает `title = None`,
  `is_empty_heading = true` и `display_title = "(empty heading)"`;
- технический marker пустой секции в `section_path` — `__empty_heading__`.

### LangChain Document

Одна секция становится одним `langchain_core.documents.Document`.

- heading включается в `page_content`, чтобы передать embedding/splitter
  тематический контекст;
- frontmatter остаётся в `metadata`;
- wikilinks остаются в `metadata`;
- metadata содержит section identity, path, offsets, note identity,
  content hash и parser version;
- соседние секции и notes автоматически не подмешиваются.

Преобразование выполняет adapter `section_to_document`. LangChain отвечает за
runtime-контракт Document, но не за offsets, versioning или persistence.

## ChunkingPolicy

`ChunkingPolicy` — Pydantic-контракт будущего splitter pipeline. Он валидирует:

- непустое имя policy;
- положительный `chunk_size`;
- неотрицательный `chunk_overlap`;
- `chunk_overlap < chunk_size`;
- непустой список separators;
- отсутствие пустых separators;
- правила сохранения heading/code/list/table context.

Предполагаемый поток конфигурации:

```text
YAML file
    ↓
yaml.safe_load()
    ↓
ChunkingPolicy
    ↓
validated splitter run
```

## MLflow boundary

Sprint 7 использует MLflow для sectionization evidence:

- параметры schema/parser;
- structural metrics;
- JSON/CSV artifacts;
- run identity.

Sprint 7 не выбирает chunk size и не считает retrieval quality. Сравнение
`256/512/1024`, overlap policies и baseline selection относятся к Sprint 9.

## Version policy для следующих sprint-ов

Sprint 8 должен сохранять происхождение каждого chunk:

- `note_id`;
- `chunk_index`;
- section metadata;
- `start_offset` и `end_offset`;
- `parser_version`;
- `source_content_hash`;
- `chunking_version`.

В рамках одной версии ожидается identity:

```text
(note_id, chunking_version, chunk_index)
```

Старая chunking version не удаляется автоматически. Active version выбирается
явно, чтобы сохранить audit history и возможность сравнения/rollback.

## Boundaries

Structural boundaries являются предпочтительными:

- headings не должны терять context;
- code blocks, lists и tables не следует разрывать без необходимости;
- overlap применяется только для oversized text sections;
- deterministic input + parser version + policy должны давать
  сопоставимый output.

Semantic splitting, embeddings и retrieval-based selection появятся после
появления embedding/evaluation слоя.

## Sprint 7 evidence

Реализованы:

- `chunking/blocks.py`;
- `chunking/section_tree.py`;
- `chunking/documents.py`;
- `chunking/policy.py`;
- `chunking/tracking.py`;
- focused tests для SectionTree, Documents, Policy и MLflow tracking.

Локальная validation:

```text
uv run ruff check .
All checks passed

uv run pytest -q
51 passed, 1 skipped, 14 deselected
```

Тесты не изменяют read-only vault. Generated MLflow tracking data остаётся
локальным артефактом и не должен добавляться в Git.
