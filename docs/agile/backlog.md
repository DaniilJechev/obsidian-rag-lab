# Product Backlog — Obsidian RAG

## Что такое backlog

Backlog — живой упорядоченный список будущей работы над проектом.

Он отвечает на вопросы:

- что ещё нужно сделать;
- зачем это нужно;
- насколько задача приоритетна;
- к какой фазе roadmap она относится;
- готова ли задача для включения в sprint.

Backlog не является жёстким расписанием. Приоритеты и формулировки могут меняться после экспериментов, review и retrospective.

## Правила работы

1. Новые идеи сначала добавляются в backlog, а не включаются в текущий sprint молча.
2. Перед началом sprint из backlog выбирается ограниченный scope.
3. Каждая задача должна иметь понятный результат и критерий готовности.
4. Большие задачи нужно делить на меньшие задачи или отдельные sprint.
5. После sprint backlog обновляется:
   - выполненные задачи отмечаются;
   - незавершённые задачи переносятся;
   - новые идеи добавляются;
   - приоритеты пересматриваются.
6. Backlog не заменяет `sprint-template.md`: backlog хранит будущую работу, а sprint-документ описывает конкретный рабочий цикл.

## Приоритеты

- **P0 — обязательно:** блокирует следующий этап или Definition of Done.
- **P1 — высокий:** важный результат текущего roadmap.
- **P2 — средний:** полезное улучшение или учебное сравнение.
- **P3 — низкий:** optional, portfolio или дополнительный эксперимент.

## Статусы

- `idea` — идея зафиксирована, но ещё не проработана.
- `ready` — задача понятна и может попасть в sprint.
- `in-progress` — задача входит в текущий sprint.
- `blocked` — есть внешний или технический блокер.
- `done` — Definition of Done задачи выполнен.
- `deferred` — сознательно отложена.

## Backlog задач

| ID | Приоритет | Статус | Фаза | Задача | Definition of Done |
|---|---|---|---|---|---|
| BOOT-001 | P0 | done | 0 | Создать структуру writable-проекта | Базовые каталоги созданы, vault не изменён |
| BOOT-002 | P0 | done | 0 | Настроить `uv`, Python 3.12 и конфигурацию | `.venv`, `pyproject.toml`, `uv.lock`, `.env.example` созданы и проверены |
| BOOT-003 | P0 | done | 0 | Настроить Git, GitHub, `.gitignore`, tests, Ruff и CI | Commit и push выполнены, локальные checks и GitHub Actions проходят |
| BOOT-004 | P0 | done | 0 | Запустить PostgreSQL и Qdrant через Docker Compose | Оба сервиса работают, volumes подключены, healthchecks проходят |
| BOOT-005 | P0 | done | 0 | Завершить формальную проверку Definition of Done Фазы 0 | Локальные checks, Docker healthchecks, CI, Git safety и roadmap snapshot проверены |
| AGILE-001 | P0 | done | 0 | Создать и согласовать sprint workflow | Шаблон sprint создан, правила начала/работы/завершения зафиксированы |
| AGILE-002 | P0 | done | 0 | Создать Cursor skill для commit-процесса | Skill описывает pre-commit checks, secrets safety и post-commit verification |
| AGILE-003 | P1 | done | 0 | Создать Cursor skill для планирования нового sprint | Skill помогает сформулировать goal, scope, DoD, Issues и Milestone |
| AGILE-004 | P1 | done | 0 | Создать Cursor skill для новой Git-ветки | Skill безопасно создаёт sprint branch от актуальной `main` |
| CORPUS-001 | P0 | done | 1 | Безопасно обнаружить Markdown-файлы только в DLS1/DLS2 | Allowlist работает, запрещённые пути отклоняются, vault не изменяется |
| CORPUS-002 | P1 | done | 1 | Распарсить Markdown-структуру | Извлекаются текст, headings, frontmatter и wikilinks |
| CORPUS-003 | P1 | done | 1 | Подготовить corpus inventory и EDA | Реальные числа файлов, размеров, слов, токенов и дублей сохранены |
| DATA-001 | P1 | done | 2 | Спроектировать PostgreSQL schema и migrations | Таблицы notes, ingestion runs/states, versions и chunks contract описаны и создаются Alembic migrations |
| DATA-002 | P1 | done | 2 | Реализовать idempotent ingestion | Repositories, content hash, parser version, failure accounting и new/changed/unchanged/stale logic покрыты unit/PostgreSQL scenarios; CI/Linux confirmation of local Windows pytest cleanup remains an environmental follow-up |
| DATA-003 | P1 | done | 2 | Провести production-like PostgreSQL test drive | Полный DLS1+DLS2 run, consistency checks, rollback/recovery и handoff к Phase 3 подтверждены; CI/PR closeout остаётся отдельным pipeline |
| CHUNK-001 | P1 | done | 3 | Реализовать heading-aware и recursive structural chunking | Versioned chunks сохраняют note/section metadata, headings и offsets; deterministic output, PostgreSQL persistence, migration, CI и owner/assistant review подтверждены в Sprint 8 |
| CHUNK-002 | P2 | done | 3 | Сравнить размеры chunk 256/512/1024 | Structural YAML-driven experiment runner воспроизводим; MLflow parameters, metrics, UI comparison и generated artifacts записаны; provisional versioned `chunk → embedding` handoff документирован. Финальный retrieval baseline переносится в Phase 4/7 после embeddings и gold questions |
| CHUNK-003 | P1 | done | 3 | Спроектировать SectionTree и typed Markdown blocks | Контракт, hierarchy, section paths, offsets и focused tests реализованы; Sprint 7 merged в `main` |
| CHUNK-004 | P1 | done | 3 | Определить LangChain Document и ChunkingPolicy contracts | Document adapter, metadata propagation, strict YAML policy и tests реализованы; Sprint 7 merged в `main` |
| CHUNK-005 | P1 | done | 3 | Добавить YAML validation и sectionization evidence | MLflow sectionization evidence, structural metrics, artifacts и GitHub CI подтверждены |
| EMB-001 | P1 | done | 4 | Создать `EmbeddingProvider` и подключить локальную CPU-модель | Contract, `multilingual-e5-small` CPU provider, pooling, normalization, vector validation, tests и MLflow smoke run `a023f4a528314856b36eafdb9ec5794c` подтверждены в Sprint 10 |
| EMB-002 | P2 | done | 4 | Реализовать batch embedding pipeline | Versioned chunks обрабатываются batches с progress, retries, failure accounting и temporary JSON manifest; Sprint 11 merged in PR [#35](https://github.com/DaniilJechev/obsidian-rag-lab/pull/35), merge commit `60324d7`, CI passed |
| EMB-003 | P1 | deferred | 4 | Сравнить local embedding models и подготовить Qdrant handoff | Отложено до появления evaluation-ready этапа; `multilingual-e5-small` используется как provisional baseline, а Qdrant handoff реализуется отдельно в Phase 5 |
| RET-001 | P1 | done | 5 | Создать Qdrant collection и dense retrieval | Sprint 14 completed: direct batch upsert, versioned collection/payload, idempotency, consistency verification; PR [#39](https://github.com/DaniilJechev/obsidian-rag-lab/pull/39) merged with CI passed |
| RET-002 | P1 | done | 5 | Добавить BM25 и RRF hybrid retrieval | Sprint 15 completed: Qdrant sparse BM25, RRF, retrieval contract и live hybrid smoke; PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41) merged (`46b4234`), CI passed, Issue [#38](https://github.com/DaniilJechev/obsidian-rag-lab/issues/38) closed |
| RET-003 | P2 | done | 5 | Удалить неиспользуемый `rank-bm25` | Dependency removed in PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41); lexical search uses Qdrant sparse `bm25` only |
| PGV-001 | P2 | done | 6 | Учебный dense path на PostgreSQL + pgvector (без merge в `main`) | Sprint 16 completed on `sprint/16-pgvector-dense-experiment` (`bd39d20`); live top-k matched Qdrant dense; implementation not merged; Qdrant remains default |
| EVAL-001 | P0 | done | 7 | Создать gold eval-набор | Sprint 17 completed: 50 note-level вопросов, owner review, `eval_items` loader; PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45) merged (`59188fb`); freeze `phase7_GT_note_level_v0` в Sprint 18 |
| EVAL-002 | P0 | done | 7 | Реализовать nDCG@k и MRR@k | Sprint 18: live `rag-cli eval run`; MLflow Compare dense/bm25/hybrid @5 на 50 вопросах записан в `docs/agile/sprint-18-retrieval-eval-baseline.md`; PR closeout — owner review |
| API-001 | P1 | idea | 8 | Создать FastAPI retriever service | `/health`, `/ingest`, `/search` имеют контракты и тесты |
| LLM-001 | P1 | idea | 9 | Подключить OpenRouter LLM | Ответы имеют structured output и citations |
| GRAPH-001 | P1 | idea | 11 | Добавить LangGraph workflow | State, nodes, branching, retry и refusal наблюдаемы |
| ML-001 | P2 | idea | 12 | Добавить reranker и сравнить retrieval | nDCG/MRR до и после reranking измерены |
| MLOPS-001 | P2 | idea | 10 | Добавить RAGAS и MLflow tracking | Generation metrics и experiment artifacts сохраняются |
| CLOUD-001 | P2 | idea | 13 | Сравнить local и cloud storage | Latency, cost, reliability и operational effort измерены |
| SERVE-001 | P3 | idea | 16 | Запустить локальную LLM через vLLM | API и vLLM сравнены на одном eval-наборе |
| DEPLOY-001 | P3 | idea | 17 | Подготовить Kubernetes proof of concept | API/Qdrant/worker manifests и health probes описаны |
| OPT-001 | P2 | idea | 19 | Провести общий bottleneck analysis | Latency/resource breakdown и before/after оптимизации записаны |
| AUDIT-001 | P0 | idea | final | Проверить общий DoD и глубину skills | Все пункты DoD и Матрица 8 оценены по evidence |

## Идеи и технический долг

- Добавить отдельный benchmark платных embeddings через OpenRouter.
- Сравнить Qdrant с PostgreSQL + pgvector на одинаковых chunks —
  закрыто в `PGV-001` / Sprint 16 как branch-only experiment (`bd39d20`),
  без merge в `main`; follow-up по pgvector не планируется.
- Добавить cloud-профиль после локального baseline.
- Рассмотреть graph-enhanced retrieval по Obsidian wikilinks.
- Добавить Telegram integration через `asyncio`.
- Проверить необходимость typed configuration loader.
- Документировать ограничения custom Qdrant image с `wget`.
- Держать embedding model в долгоживущем процессе: CLI `rag-cli search`
  сейчас каждый раз заново загружает e5, и это доминирует над Qdrant latency.

## Текущий фокус

Фазы 1–5 завершены на `main` (Qdrant dense + sparse BM25 + RRF). Phase 6
(`PGV-001`, Sprint 16) закрыта как branch-only pgvector dense experiment:
implementation на `sprint/16-pgvector-dense-experiment` (`bd39d20`), в `main`
не влита, дальше с pgvector не работаем. Qdrant остаётся единственным
retrieval default. Следующая работа на `main`: **Phase 7 Sprint 18** —
live dense/bm25/hybrid nDCG/MRR в MLflow на frozen gold `phase7-note-level-v1`.
FastAPI — Phase 8, не сейчас.

История завершённых спринтов:

1. Sprint 7: SectionTree, typed blocks, LangChain Documents и policy contracts
   (`CHUNK-003`, `CHUNK-004`, `CHUNK-005`; GitHub [#19](https://github.com/DaniilJechev/obsidian-rag-lab/issues/19)).
2. Sprint 8: LangChain recursive structural chunking и versioned persistence
   (`CHUNK-001`; GitHub [#20](https://github.com/DaniilJechev/obsidian-rag-lab/issues/20))
   — done, PR [#24](https://github.com/DaniilJechev/obsidian-rag-lab/pull/24)
   merged.
3. Sprint 9: YAML-driven comparison размеров `256/512/1024`, MLflow и PostgreSQL
   materialization
   (`CHUNK-002`; GitHub [#21](https://github.com/DaniilJechev/obsidian-rag-lab/issues/21))
   — structural scope done; semantic baseline selection deferred до embeddings и
   gold questions.
4. Sprint 10: local CPU `EmbeddingProvider`, multilingual E5 smoke inference и
   MLflow operational tracking (`EMB-001`; GitHub
   [#28](https://github.com/DaniilJechev/obsidian-rag-lab/issues/28))
   — completed; PR [#31](https://github.com/DaniilJechev/obsidian-rag-lab/pull/31)
   merged.

5. Sprint 11: version-aware batch embeddings, temporary JSON artifacts и MLflow
   operational tracking (`EMB-002`; GitHub
   [#30](https://github.com/DaniilJechev/obsidian-rag-lab/issues/30))
   — completed; PR [#35](https://github.com/DaniilJechev/obsidian-rag-lab/pull/35)
   merged. `EMB-003` deferred; JSON остаётся только историческим временным
   handoff Sprint 11 и будет удалён из runtime в Phase 5.

6. Sprint 14: direct Qdrant vector storage и versioned handoff
   (`RET-001`; planning document:
   `docs/agile/sprint-14-qdrant-vector-storage.md`)
   — completed; PR [#39](https://github.com/DaniilJechev/obsidian-rag-lab/pull/39)
   merged.

7. Sprint 15: dense search, Qdrant sparse BM25, RRF и retrieval contracts
   (`RET-002`, `RET-003`; planning document:
   `docs/agile/sprint-15-retrieval-foundation.md`)
   — completed; PR [#41](https://github.com/DaniilJechev/obsidian-rag-lab/pull/41)
   merged (`46b4234`), CI passed, Issue
   [#38](https://github.com/DaniilJechev/obsidian-rag-lab/issues/38) closed.

8. Sprint 16: учебный PostgreSQL + pgvector dense path
   (`PGV-001`; `docs/agile/sprint-16-pgvector-dense-experiment.md`)
   — completed as branch-only; implementation `bd39d20` on
   `sprint/16-pgvector-dense-experiment`, not merged to `main`.

9. Sprint 17: gold 50 вопросов, `eval_items`, note-level metric harness
   (`EVAL-001`; `docs/agile/sprint-17-gold-eval-items.md`)
   — completed; PR [#45](https://github.com/DaniilJechev/obsidian-rag-lab/pull/45)
   merged (`59188fb`), CI passed; gold freeze in Sprint 18 is
   `phase7_GT_note_level_v0`.

10. Sprint 18: live dense/bm25/hybrid baseline в MLflow
    (`EVAL-002`; `docs/agile/sprint-18-retrieval-eval-baseline.md`;
    GitHub [#44](https://github.com/DaniilJechev/obsidian-rag-lab/issues/44))
    — implementation + observed @5 metrics recorded; owner review/merge PR.

Semantic evaluation и gold questions — Phase 7. RAGAS — живая Phase 10 после
generate. OpenRouter generation — Phase 9. FastAPI — Phase 8, сознательно
после eval. LangGraph — Phase 11. Sprint 16 не заменяет Qdrant.
