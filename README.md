# RAG Based on Obsidian

Production-like RAG-пайплайн поверх учебных заметок Obsidian.

## Цель проекта

Совместно построить измеряемую RAG-систему, которая умеет находить релевантный контекст в заметках, генерировать ответы через LLM и возвращать citations на исходные заметки.

Проект одновременно служит учебным полигоном для технологий из `ML main skills.md`: RAG, embeddings, vector search, PostgreSQL, Qdrant, LangChain, LangGraph, FastAPI, evaluation, MLOps и deployment.

## Корпус

Первая версия работает только с:

- `obsidianNotes/ML_NLP/DLS1/`
- `obsidianNotes/ML_NLP/DLS2/`

`OBSIDIAN_VAULT_ROOT` указывает на `obsidianNotes/ML_NLP`, потому что
discovery принимает только прямые дочерние каталоги `DLS1` и `DLS2`.
Каталог `obsidianNotes/ML_NLP/NLP/` в allowlist не входит.

Каталог `obsidianNotes` является read-only. Приложение не должно изменять, перемещать или удалять исходные заметки.

## Roadmap

- [Подробный roadmap проекта](docs/RAG_obsidian_plan_snapshot.md)
- [Рабочий план Cursor](C:\Users\gigachaDick\.cursor\plans\rag_pipeline_roadmap_7c0acd14.plan.md)

Snapshot roadmap хранится в `docs/` как проектная копия. Исходный файл в `obsidianNotes` остаётся источником учебного материала и не редактируется.

## Начальная архитектура

```text
Markdown-файлы DLS1/DLS2
          |
          v
Parser + chunking
          |
          +--> PostgreSQL
          |    metadata, ingestion state, eval, logs, cache
          |
          +--> Local embedding model
                    |
                    v
                 Qdrant
              vector retrieval

User question
          |
          v
FastAPI + LangGraph
          |
          +--> hybrid retrieval: Qdrant + BM25
          |
          +--> LLM через OpenRouter
          |
          v
Ответ с citations
```

## Выбранный порядок технологий

1. Локальные PostgreSQL и Qdrant через Docker Compose.
2. Бесплатная локальная multilingual embedding-модель на CPU.
3. OpenRouter как первый LLM API.
4. Hybrid retrieval: dense search + BM25 + RRF.
5. FastAPI и LangChain.
6. LangGraph, reranking, cache и classic ML.
7. Сравнение Qdrant с `pgvector`.
8. Сравнение local storage с cloud storage.
9. Сравнение бесплатных local embeddings с платными embeddings через OpenRouter.
10. Эксперименты с vLLM на Colab или cloud GPU.
11. Kubernetes как поздняя необязательная deployment-фаза.

## Структура проекта

```text
src/        исходный Python-код
tests/      автоматические тесты
notebooks/  EDA и эксперименты
evals/      eval-вопросы, gold labels и результаты
configs/    конфигурации
docker/     Docker-файлы и Compose-конфигурация
artifacts/  локальные результаты запусков
docs/       проектная документация и roadmap snapshot
```

## Принцип совместной реализации

Проект реализуется в учебном режиме:

1. Сначала объясняется технология и проблема, которую она решает.
2. Затем определяется небольшой проверяемый шаг.
3. Пользователь выполняет посильную часть работы.
4. AI-ассистент помогает skeleton-кодом, подсказками, review и debugging.
5. Результат проверяется тестом, измерением или практической проверкой понимания.
6. Перед переходом к следующей фазе проверяется Definition of Done текущей фазы.

AI-ассистент не должен молча писать весь проект вместо пользователя.

## Метрики

Ключевые метрики будут добавляться после появления baseline:

- retrieval: `nDCG@k`, `MRR@k`;
- generation: Faithfulness, Answer Relevancy, Context Precision/Recall;
- performance: latency p50/p95, throughput;
- efficiency: tokens/query, cost/query;
- reliability: ingestion success rate и error rate.

Числа в README добавляются только по результатам воспроизводимых запусков. До появления экспериментов метрики не выдумываются.

## Текущий статус

Фаза 0 — каркас проекта:

- [x] Создана базовая структура каталогов.
- [x] Roadmap скопирован в `docs/RAG_obsidian_plan_snapshot.md`.
- [x] Создан README.
- [x] Настроены Python environment (`uv`, Python 3.12.12) и конфигурация.
- [x] Инициализирован Git, добавлен `.gitignore` и настроен удалённый GitHub-репозиторий.
- [x] Добавлены базовые тесты, Ruff и GitHub Actions CI.
- [x] Созданы Docker Compose и производный Qdrant image с healthcheck.
- [x] PostgreSQL 16 и Qdrant v1.19.0 запущены локально через Docker Compose.
- [x] Настроены persistent volumes для PostgreSQL и Qdrant.
- [x] PostgreSQL и Qdrant проходят healthcheck.
- [x] Согласован шаблон Agile-спринта и правила sprint workflow.
- [x] Создан и проверен проектный набор skills для sprint planning и Git workflow.
- [x] Проведена финальная проверка Definition of Done Фазы 0:
  - локальные Ruff и pytest проходят;
  - PostgreSQL и Qdrant проходят Docker healthcheck;
  - последний GitHub Actions CI завершился успешно;
  - `.env` не отслеживается Git;
  - roadmap snapshot совпадает с read-only источником.

Фаза 0 формально завершена. Следующий этап — планирование Sprint 1 для Фазы 1
(Safe Corpus Discovery).
