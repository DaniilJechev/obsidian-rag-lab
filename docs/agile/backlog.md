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
| CORPUS-001 | P0 | ready | 1 | Безопасно обнаружить Markdown-файлы только в DLS1/DLS2 | Allowlist работает, запрещённые пути отклоняются, vault не изменяется |
| CORPUS-002 | P1 | ready | 1 | Распарсить Markdown-структуру | Извлекаются текст, headings, frontmatter и wikilinks |
| CORPUS-003 | P1 | ready | 1 | Подготовить corpus inventory и EDA | Реальные числа файлов, размеров, слов, токенов и дублей сохранены |
| DATA-001 | P1 | idea | 2 | Спроектировать PostgreSQL schema | Таблицы notes, chunks, ingestion runs, eval, logs и cache описаны миграциями |
| DATA-002 | P1 | idea | 2 | Реализовать idempotent ingestion state | Content hash, index version, retries и failure accounting работают |
| CHUNK-001 | P1 | idea | 3 | Реализовать heading-aware chunking | Чанки сохраняют note/section metadata и покрыты тестами |
| CHUNK-002 | P2 | idea | 3 | Сравнить размеры chunk 256/512/1024 | Эксперимент воспроизводим, результаты записаны |
| EMB-001 | P1 | idea | 4 | Подключить бесплатную локальную embedding-модель на CPU | `EmbeddingProvider` возвращает vectors нужной размерности |
| EMB-002 | P2 | idea | 4 | Сравнить batching и ограниченную concurrency | Throughput, latency и ошибки измерены |
| RET-001 | P1 | idea | 5 | Создать Qdrant collection и dense retrieval | Search, payload и metadata filters работают |
| RET-002 | P1 | idea | 5 | Добавить BM25 и RRF hybrid retrieval | Dense и lexical результаты объединяются воспроизводимо |
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

Фаза 0 формально завершена. Следующая работа относится к Фазе 1, но ещё не
является автоматически созданным sprint:

1. Применить `sprint-planning`.
2. Проверить зависимости и размер scope для `CORPUS-001`, `CORPUS-002`,
   `CORPUS-003`.
3. Согласовать Sprint 1, GitHub Milestone и Issues.
4. Создать sprint branch только после подтверждения scope.
