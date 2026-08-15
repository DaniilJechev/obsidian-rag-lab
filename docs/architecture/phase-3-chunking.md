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

## Sprint 8 implementation boundary

`chunking/recursive.py` использует `RecursiveCharacterTextSplitter` из
`langchain-text-splitters`. Для обычной секции overlap принудительно равен
нулю; policy overlap включается только для oversized секций. Heading context
добавляется к каждому результирующему chunk, а offset ищется в исходном
`source_text`, а не в нормализованной копии `Document.page_content`.

`chunking/records.py` содержит immutable `ChunkRecord`. Word count и
estimated token count используют детерминированные Unicode-aware proxy
регулярные выражения. Это не tokenizer конкретной LLM: такой tokenizer
появится только после выбора embedding/LLM stack.

`chunking/persistence.py` содержит два намеренно разных действия:

- `upsert_generation()` идемпотентно обновляет конкретные identity keys;
- `replace_generation()` атомарно пересоздаёт одну `(note_id, version)` в
  savepoint и удаляет stale rows только этой версии.

Обе операции сохраняют старые версии, а `list_generation()` требует явный
`chunking_version`; repository не выводит active version через случайный
`latest` row. Migration `7a2c4d1e9f30_add_chunk_provenance.py` добавляет
`parser_version` и `source_content_hash` для аудита regenerated chunks.

Текущая implementation boundary: малые code/list/table blocks защищаются от
separator-based splitting. Oversized structural blocks всё ещё могут
разрезаться; для них отдельная semantic strategy остаётся техническим долгом
Sprint 8 и явно покрывается ограничением policy.

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

## Sprint 9 experiment architecture

Sprint 9 compares independent chunking-policy runs, not model-training epochs.
The primary comparison dimensions are:

- `chunk_size`: `256`, `512`, `1024` estimated tokens;
- overlap policy: no overlap for ordinary sections and selective overlap only
  for oversized text sections;
- optional repeat/iteration when measuring reproducibility.

The planned flow is:

```text
YAML policy
    ↓
validated experiment contract
    ↓
SectionTree → LangChain Documents → ChunkRecord
    ↓
metrics collector + artifact writers
    ↓
MLflow parameters/metrics/artifacts
    ↓
MLflow Tracking Server + UI + Markdown/JSON/CSV artifacts
    ↓
baseline selection → versioned chunk → embedding handoff
```

MLflow Tracking Server is the primary local tracking and comparison interface.
The user will manually start it with SQLite metadata storage and a local
artifact root, open the UI in a browser and verify that candidate runs,
parameters, metrics and artifacts are visible. The experiment CLI connects to
the server through its HTTP tracking URI. JSON/CSV/Markdown files remain
reproducible local artifacts; pyplot and a separate HTML visualization stack
are out of scope. TensorBoard is intentionally out of scope because this sprint
does not train a model or produce epoch-based learning curves.

Minimum experiment metrics:

- chunk count;
- median/p95 estimated-token length;
- short-chunk rate;
- oversized-section and overlap usage;
- boundary violations;
- duplicate hashes;
- metadata completeness;
- storage size and generation latency.

The final baseline must be chosen using multiple declared criteria and must
include a versioned `chunk → embedding` contract for Phase 4. Generated MLflow
tracking data remains local and should not be added to Git.

## Sprint 9 PostgreSQL handoff

The structural experiment stage exposes a provisional, versioned
`chunk → embedding` handoff. `chunking_cli.py --to-pg --policy <policy>` clears
the PostgreSQL `chunks` table and atomically materializes the selected YAML
policy from the allowlisted vault. The command preserves note metadata and
chunk provenance; it does not modify the source vault.

The final retrieval-oriented chunking baseline is intentionally deferred until
Phase 4/7 provides an embedding model, golden questions and retrieval metrics.
