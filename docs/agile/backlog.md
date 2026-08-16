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
| RET-001 | P1 | ready | 5 | Создать Qdrant collection и dense retrieval | Sprint 14: direct batch upsert, versioned collection/payload, idempotency, consistency verification, dense search foundation |
| RET-002 | P1 | ready | 5 | Добавить BM25 и RRF hybrid retrieval | Sprint 15: `LexicalIndex`, BM25, RRF fusion, retrieval contract и synthetic smoke search |
| EVAL-001 | P0 | idea | 7 | Создать gold eval-набор | Вопросы и relevant note/chunk IDs проверены вручную |
| EVAL-002 | P0 | idea | 7 | Реализовать nDCG@k и MRR@k | Метрики считаются тестами на фиксированном наборе |
| API-001 | P1 | idea | 8 | Создать FastAPI retriever service | `/health`, `/ingest`, `/search` имеют контракты и тесты |
| LLM-001 | P1 | idea | 9 | Подключить OpenRouter LLM | Ответы имеют structured output и citations |
| GRAPH-001 | P1 | idea | 10 | Добавить LangGraph workflow | State, nodes, branching, retry и refusal наблюдаемы |
| ML-001 | P2 | idea | 11 | Добавить reranker и сравнить retrieval | nDCG/MRR до и после reranking измерены |
| MLOPS-001 | P2 | idea | 15 | Добавить RAGAS и MLflow tracking | Generation metrics и experiment artifacts сохраняются |
| CLOUD-001 | P2 | idea | 13 | Сравнить local и cloud storage | Latency, cost, reliability и operational effort измерены |
| SERVE-001 | P3 | idea | 16 | Запустить локальную LLM через vLLM | API и vLLM сравнены на одном eval-наборе |
| DEPLOY-001 | P3 | idea | 17 | Подготовить Kubernetes proof of concept | API/Qdrant/worker manifests и health probes описаны |
| OPT-001 | P2 | idea | 19 | Провести общий bottleneck analysis | Latency/resource breakdown и before/after оптимизации записаны |
| AUDIT-001 | P0 | idea | final | Проверить общий DoD и глубину skills | Все пункты DoD и Матрица 8 оценены по evidence |

## Идеи и технический долг

- Добавить отдельный benchmark платных embeddings через OpenRouter.
- Сравнить Qdrant с PostgreSQL + pgvector на одинаковых chunks.
- Добавить cloud-профиль после локального baseline.
- Рассмотреть graph-enhanced retrieval по Obsidian wikilinks.
- Добавить Telegram integration через `asyncio`.
- Проверить необходимость typed configuration loader.
- Документировать ограничения custom Qdrant image с `wget`.

## Текущий фокус

Фазы 1 и 2 завершены; Phase 2 закрыта после Sprint 6 и полного DLS1+DLS2
production-like test drive. Sprint 7, Sprint 8 и structural implementation Sprint 9
завершены. Технический scope Phase 4 завершён в Sprint 10 и Sprint 11;
сравнение embedding-моделей (`EMB-003`) сознательно отложено до
evaluation-ready этапа. Следующая готовая работа относится к Phase 5:

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
   `docs/agile/sprint-14-qdrant-vector-storage.md`).

7. Sprint 15: dense search, BM25, RRF и retrieval contracts
   (`RET-002`; planning document:
   `docs/agile/sprint-15-retrieval-foundation.md`).

Semantic evaluation, gold questions и RAGAS остаются в Phase 7, а OpenRouter
generation — в Phase 9. LangGraph относится к более поздней фазе. Sprint 14 и
Sprint 15 создают только технический vector/retrieval foundation; они не
утверждают качество embeddings или retrieval.
