# Sprint 7 — LangChain Documents and SectionTree

> Статус: `completed`
>
> Ветка реализации: `sprint/7-langchain-documents-section-tree`
>
> Связанная фаза roadmap: `Фаза 3`
>
> Зависимость: Phase 1 Markdown parser и Sprint 6 `note → chunks` handoff
>
> Backlog: `CHUNK-003`, `CHUNK-004`, `CHUNK-005`
>
> Оценка: 8–16 часов
>
> GitHub: [Issue #19](https://github.com/DaniilJechev/obsidian-rag-lab/issues/19)
> · [Milestone Phase 3 — LangChain-first Chunking](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/5)

## Sprint Goal

Определить и протестировать структурный контракт `parsed Markdown → typed blocks
→ SectionTree → LangChain Document`, который сохраняет смысловую структуру
заметки, metadata и character offsets до следующего спринта.

## Согласованные архитектурные решения

### Typed Markdown blocks

Markdown представляется как упорядоченная immutable-последовательность
логических блоков:

```text
tuple[MarkdownBlock, ...]
```

Поддерживаемые block types: `heading`, `paragraph`, `code`, `list`, `table`,
`wikilink` metadata и `pre_heading`. Один block соответствует логической
структурной единице, а не отдельной строке. Порядок blocks должен совпадать с
порядком их появления в исходном Markdown.

Typed blocks нужны, чтобы явно сохранить структурные границы, передать
chunker-у правила обработки разных block types и не распознавать одну и ту же
структуру повторно в parser, SectionTree и splitter.

### SectionTree и связи между секциями

SectionTree строится как immutable Python domain model на `dataclass`-ах.
Каждый `SectionNode` содержит:

- `children: tuple[SectionNode, ...]`;
- `parent_section_id: str | None`;
- `previous_sibling_id: str | None`;
- `next_sibling_id: str | None`.

`previous_sibling_id` и `next_sibling_id` соответствуют соответственно
`old_brother` и `young_brother`: это соседние headings того же уровня с тем же
родителем. Связи хранятся через IDs, а не прямые object pointers, чтобы не
создавать циклические ссылки `parent → child → parent` и не усложнять
сериализацию.

Parent определяется стеком открытых headings. При добавлении нового heading
закрываются headings более глубокого уровня; последний child того же parent и
level становится `previous_sibling`, а его `next_sibling_id` обновляется.

### SectionNode state

Для обычной heading-секции:

```text
section_type = "heading"
title = "Chunking"
is_empty_heading = false
display_title = "Chunking"
```

Для пустого heading:

```text
section_type = "heading"
title = null
is_empty_heading = true
display_title = "(empty heading)"
```

Для текста до первого heading:

```text
section_type = "pre_heading"
title = null
is_empty_heading = false
display_title = "(pre-heading)"
```

Машинное состояние (`title`, `section_type`, `is_empty_heading`) отделено от
display label. В `section_path` используется стабильный технический marker
`__empty_heading__`, но он не показывается как пользовательский title.

### LangChain Document

Гранулярность runtime-документа: одна SectionTree section становится одним
LangChain `Document`. `Document` содержит основной текст в `page_content` и
служебные поля в `metadata`.

Heading включается в `page_content`, потому что он передаёт embedding/splitter
тематический контекст:

```text
## Overlap

Overlap применяется только для больших секций.
```

Frontmatter не включается в `page_content` и сохраняется только в metadata.
Wikilinks также не становятся отдельными Documents и сохраняются только в
metadata. Соседние notes в Sprint 7 автоматически не подмешиваются.

### Offsets и note identity

Offsets используют Python character coordinates с полуинтервалом:

```text
start_offset — inclusive
end_offset — exclusive
```

Следовательно, `raw_text[start_offset:end_offset]` должен возвращать исходный
фрагмент. Byte offsets не используются.

Metadata допускает работу до и после persistence:

```text
note_id: int | None
relative_path: str
source_content_hash: str
parser_version: str
```

`note_id` является `int`, если документ получен из PostgreSQL, и `None` в
pure-parser/unit-test сценариях.

### YAML и Pydantic

YAML читается через уже существующий PyYAML, после чего mapping валидируется
Pydantic-моделью `ChunkingPolicy`:

```text
YAML → yaml.safe_load() → dict → Pydantic ChunkingPolicy
```

Pydantic используется для typed validation конфигурации, а Markdown blocks и
SectionTree остаются immutable dataclass domain entities. Валидация должна
проверять положительный `chunk_size`, неотрицательный `chunk_overlap`,
`chunk_overlap < chunk_size`, непустое имя policy и допустимые separators.

### MLflow boundary

MLflow входит в Sprint 7 как обязательный tracking layer для sectionization,
но запускается после реализации SectionTree, LangChain Documents и focused
tests. Sprint 7 логирует структурные metrics и schema/config artifacts; он не
логирует chunk-size или retrieval metrics. Sprint 9 расширяет этот tracking до
сравнения chunking policies и выбора embedding baseline.

## Why

Recursive splitter не должен получать бесформенную строку, если исходная заметка
уже содержит headings, code blocks, списки, таблицы и wikilinks. `SectionTree`
будет промежуточной структурой между существующим parser и LangChain:

- parser отвечает за извлечение фактов из Markdown;
- `SectionTree` отвечает за иерархию секций и границы;
- LangChain `Document` становится runtime-контрактом для splitter pipeline;
- persistence остаётся собственным прозрачным контрактом проекта.

Так мы используем LangChain с самого начала, но не отдаём framework-у
ответственность за versioning, offsets, PostgreSQL и экспериментальную
воспроизводимость.

## Scope

- [ ] Описать typed block contract для heading, paragraph, code, list, table,
  wikilink и pre-heading text.
- [ ] Построить `SectionTree` с `direct_body`, children, heading metadata,
  `section_path`, section level/type и character offsets исходного Markdown.
- [ ] Определить поведение для pre-heading text, пустых headings, вложенных
  headings, code/list/table blocks и повторяющихся headings.
- [ ] Определить metadata propagation contract для LangChain
  `Document(page_content, metadata)`.
- [ ] Создать `ChunkingPolicy` и typed YAML config validation без запуска
  production chunking.
- [ ] Проверить, что heading context, note identity, source hash, parser version,
  section metadata и offsets не теряются при преобразовании в Documents.
- [ ] Добавить unit tests для нормальных, коротких и pathological Markdown notes.
- [ ] Добавить обязательный MLflow run для sectionization/config evidence после
  прохождения focused tests.
- [ ] Логировать MLflow parameters (`parser_version`, `section_tree_version`,
  `block_schema_version`, document granularity, offset unit, corpus scope и Git
  commit), structural metrics и generated artifacts.

## Out of Scope

- Recursive chunk generation и выбор финального chunk size — Sprint 8 и 9.
- Embeddings, Qdrant, BM25/RRF и retrieval evaluation — последующие фазы.
- Raw Markdown persistence в `notes`.
- Удаление или изменение файлов в `obsidianNotes`.
- LangGraph nodes, state и graph orchestration — Phase 10.
- Semantic splitting, требующий embeddings.

## Expected Artifacts

- `src/rag_based_on_obsidian/chunking/` — SectionTree, typed blocks,
  LangChain Document adapter и policy contracts.
- `configs/chunking/*.yaml` — валидируемые YAML-конфигурации политики.
- `tests/test_chunking_section_tree.py` — unit tests структуры и offsets.
- `tests/test_chunking_documents.py` — tests metadata propagation.
- `docs/architecture/phase-3-chunking.md` — описание структурного контракта.
- `src/rag_based_on_obsidian/chunking/tracking.py` — MLflow sectionization
  tracking adapter.
- `artifacts/chunking/sectionization/` — `sectionization_summary.json`,
  `block_type_counts.csv`, config snapshot и другие реально созданные artifacts.

## Acceptance Criteria

- [x] Для каждой поддерживаемой block type определены поля и инварианты.
- [x] `SectionTree` детерминированно восстанавливает hierarchy, section path и
  offsets исходного документа.
- [x] Pre-heading text и пустые headings имеют явное, протестированное поведение.
- [x] LangChain `Document` сохраняет согласованный metadata contract.
- [x] YAML policy validation отклоняет неизвестные или некорректные значения.
- [x] Unit tests покрывают code/list/table boundaries и не требуют записи в vault.
- [x] MLflow run фактически создан после focused tests и содержит parameters,
  structural metrics и artifacts.
- [x] Chunk-size, overlap и retrieval metrics не выдаются за результаты Sprint 7.

## Definition of Done

- [x] Все задачи Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [x] Тесты добавлены или обновлены и проходят.
- [x] Ruff/lint проходит.
- [x] CI проходит, если изменения отправлялись в remote.
- [x] Read-only vault не изменён текущей работой; изменение
  `obsidianNotes/DLS1/Бустинг.md` подтверждено пользователем как намеренное.
- [x] Секреты не добавлены в Git.
- [x] Contracts и ограничения записаны в этот sprint-документ или архитектурную документацию.
- [x] Пользователь подтвердил завершение спринта.

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-13 | Sprint document created from approved Phase 3 plan | Sprint 7 scope defined; implementation not started |
| 2026-08-14 | Implemented SectionTree, LangChain Documents, policy loading and MLflow tracking | Implementation slice completed; focused tests and artifacts added |
| 2026-08-14 | Added `tests/test_chunking_documents.py`, Phase 3 architecture document and YAML policies | Contracts and configuration flow documented |
| 2026-08-14 | Added strict Pydantic policy validation with `extra="forbid"` and regression test | Unknown YAML fields now fail validation |
| 2026-08-14 | Ran local validation after strict policy change | `51 passed, 1 skipped, 14 deselected`; Ruff passed |
| 2026-08-14 | PR #22 merged into `main` | Squash merge `ee7cbc8`; GitHub CI passed |

## Validation Evidence

### Commands

```text
uv run ruff check .
All checks passed

uv run pytest -q
51 passed, 1 skipped, 14 deselected
```

### Test and Lint Results

- Tests: `PASS — 51 passed, 1 skipped, 14 deselected`
- Lint: `PASS — All checks passed`
- CI: `PASS — GitHub Actions PR #22, Lint and test`

### Metrics

Sprint 7 измеряет только sectionization:

```text
documents_processed
sections_total
blocks_total
block_type_counts
max_tree_depth
empty_heading_count
pre_heading_count
invalid_offset_count
metadata_completeness
langchain_documents_total
sectionization_duration_seconds
```

Фактическая MLflow integration evidence проверяется в
`tests/test_chunking_tracking_run.py`: run создаётся через SQLite tracking URI,
логируются parameters и scalar structural metrics, а JSON/CSV artifacts
проверяются в temporary artifact directory. Chunk metrics (`chunk_count`, chunk
length distribution, overlap rate и boundary violations после splitting)
относятся к Sprint 9.

## Review

### Completed

- Sprint scope, boundaries и contracts сформулированы и реализованы.
- SectionTree, LangChain Document adapter, ChunkingPolicy и YAML loader
  покрыты focused tests.
- MLflow sectionization tracking покрыт integration test.

### Not Completed

- Remote CI evidence, Git publication and formal closeout ещё не выполнены.
- Strict YAML validation теперь реализована через Pydantic
  `ConfigDict(extra="forbid")` и покрыта regression test.
- PR #22 прошёл GitHub Actions и merged в `main` squash commit `ee7cbc8`.

### Changed Decisions

- LangChain используется с начала Phase 3, а не после отдельного custom splitter.

### Technical Debt

- Production MLflow tracking server не входит в Sprint 7; используется local
  SQLite/file artifact evidence.
- Изменение `obsidianNotes/DLS1/Бустинг.md` считается разрешённым пользовательским
  изменением и не относится к текущему Sprint 7 implementation scope.

## Retrospective

### What went well

- SectionTree, LangChain Documents and policy validation were implemented as
  separate contracts with focused tests.
- MLflow sectionization tracking was introduced before chunk-size experiments,
  so structural evidence is already reproducible.
- The PR passed GitHub CI before merge.

### What to improve

- Keep sprint evidence synchronized immediately after each validation rerun.
- Define strict configuration behavior before adding candidate YAML policies.
- Separate implementation closeout from post-merge documentation closeout.

### Carried over

- Recursive structural chunk generation and versioned persistence move to Sprint 8.
- Candidate comparison and baseline selection move to Sprint 9.

## Completion

- [x] Definition of Done проверен; local pre-push verdict `READY`.
- [x] Review проведён через PR scope/CI gate; личный review пользователя явно
  разрешён без ожидания.
- [x] Retrospective заполнена.
- [x] Commit/PR/merge выполнены по согласованному Git workflow.
- [x] Backlog обновлён до статуса `done`.
- [x] Следующий sprint выбран и запланирован: Sprint 8.

**Итоговый статус:** `completed`

**Дата завершения:** `2026-08-14`
