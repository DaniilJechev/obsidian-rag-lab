# План: RAG для Obsidian vault

**Цель:** production-like pet RAG по vault (v1 — allowlist `DLS2/`), с покрытием большинства скиллов из [[ML main skills]].  
**Корпус (ориентир):** ~608 md / ~250k tokens overall; v1 ≈ `DLS2/` (~48k+ words) — достаточно для eval и абляций.  
**Легенда стека:** **основной** / *замена* / *(опционально)*.  
`seaborn` — только лёгкая визуализация, не ядро (см. пометку в ML main skills).

---

## Легенда взаимозамен

Не делать deep сразу в обе стороны:

| Пара | Правило |
|---|---|
| `Qdrant` vs `pgvectors` | один — deep в pet, второй — comparison |
| `XGBoost` vs `catboost` | достаточно одного |
| облачный `LLM` vs `vLLM` | сначала API, потом self-host backend |
| `LangChain` vs свой pipeline | свой код ок, но LangChain лучше закрыть практикой на фазах 3/8 |

---

## Фаза 0 — Каркас проекта и дисциплина

**Цель:** репозиторий, окружение, воспроизводимость.

| Шаг | Что делаешь |
|---|---|
| 0.1 | Структура: `data/`, `src/`, `notebooks/`, `evals/`, `docker/`, `configs/` |
| 0.2 | Git + `.env` (ключи LLM), pre-commit по желанию |
| 0.3 | Локальный запуск через Docker Compose позже; сначала poetry/venv |

**Стек:** `git`, `Python`, `Docker`, `jupyter notebook` / `Google collab` (только EDA), `CI/CD` (скелет workflow: lint/test)

---

## Фаза 1 — Корпус и EDA vault

**Цель:** понять данные до индексации.

| Шаг | Что делаешь |
|---|---|
| 1.1 | Allowlist: v1 = `DLS2/` (± выбранный DLS1 без CV-шума) |
| 1.2 | Парсинг `.md`: frontmatter, wikilinks, картинки-ссылки, заголовки |
| 1.3 | Статистика: #файлов, слов, токенов, длина заметок, дубли |
| 1.4 | Выкинуть пустые/мусор; завести `documents` + `metadata` (path, tags, folder, mtime) |

**Стек:** `Python`, `pandas`, `Numpy`, `jupyter notebook`, `seaborn` *(минимально)*, `ML` (распределения длин → база для chunk size)

**Артефакт:** `corpus.parquet` / таблица в Postgres + отчёт EDA.

---

## Фаза 2 — Схема хранения (БД как источник правды)

**Цель:** не «папка md навсегда», а нормальная data layer.

| Шаг | Что делаешь |
|---|---|
| 2.0 | **Реализовать PostgreSQL schema как фундамент data layer:** описать таблицы, типы, primary/foreign keys, `UNIQUE`/`CHECK` constraints, JSONB-контракты, indexes и связи через SQLAlchemy Core; версионировать изменения и воспроизводимо применять их через Alembic migrations |
| 2.1 | Postgres: `notes`, `chunks`, `embeddings`, `eval_items`, `query_logs`, `cache` |
| 2.2 | Метаданные для фильтров: `folder`, `lecture`, `tags` |
| 2.3 | Версия индекса `index_version` для кеша/инвалидации |

**Стек:** `SQL || PostGreSQL`, `Python`, `Docker` (Postgres в compose)

**Результат шага 2.0:** пустая локальная PostgreSQL database получает
воспроизводимую schema через Alembic, а SQLAlchemy Core metadata, migration
history и integration tests фиксируют её контракт. Этот шаг не реализует
ingestion, query repositories, embeddings или retrieval.

*Позже:* векторы можно держать в Qdrant, метаданные/логи — в Postgres.

---

## Фаза 3 — Chunking

**Цель:** нарезка под атомарные заметки Obsidian.

| Шаг | Что делаешь |
|---|---|
| 3.1 | Recursive / heading-aware splitter (H1/H2 + абзацы) |
| 3.2 | Размеры: 256 / 512 / 1024 + overlap; абляция на eval |
| 3.3 | Сохранять parent note id + section title в metadata |
| 3.4 | Wikilinks: опционально 1-hop соседние заметки как metadata/graph hint |

**Стек:** `Python`, `LangChain` (splitters) *или* свой сплиттер; конфиги yaml; эксперименты → `MLFlow`

---

## Фаза 4 — Эмбеддинги и векторизация

**Цель:** dense index.

| Шаг | Что делаешь |
|---|---|
| 4.1 | Выбрать embedding-модель (мультиязычная RU/EN, BGE-M3-класс) |
| 4.2 | Батч-эмбеддинг чанков + ретраи; success rate пайплайна |
| 4.3 | A/B двух моделей эмбеддингов на одном gold-сете |

**Стек:** `Python`, `Transformers`, `Pytorch`, `Numpy`, `Docker`  
GPU/тяжёлое — `Google collab`. Трекинг: `MLFlow`.

---

## Фаза 5 — Vector store + lexical index (hybrid)

**Цель:** dense + BM25 + fusion (паттерн эталона Maly).

| Шаг | Что делаешь |
|---|---|
| 5.1 | Залить векторы в store + HNSW |
| 5.2 | BM25/lexical по тем же чанкам |
| 5.3 | Fusion (RRF) → hybrid top-k |
| 5.4 | Фильтры metadata (только `DLS2`, конкретная лекция) |

**Стек:**
- **Вариант A:** `PostGreSQL` + `pgvectors` + BM25
- **Вариант B:** `Qdrant` + Postgres для метаданных/логов

Также: `Python`, `Docker`, `SQL || PostGreSQL`

---

## Фаза 6 — Classic ML вспомогательный слой

**Цель:** реальные рычаги качества/cost + закрытие ML-скиллов / Reject-собесов.

| Шаг | Что делаешь |
|---|---|
| 6.1 | **Query classifier:** нужен ли retrieval? (chitchat / meta / course-question) |
| 6.2 | **Chunk usefulness model *(опционально)*:** скоринг чанков по фичам |
| 6.3 | Калибровка threshold по precision/recall |
| 6.4 | Бейзлайн фич на pandas/Numpy; модель — деревья |

**Стек:** `ML`, `scikit-learn`, `XGBoost` *или* `catboost`, `Теория вероятностей`, `pandas`, `Numpy`, `jupyter notebook`, `MLFlow`, `seaborn` *(PR-кривые, вторично)*

---

## Фаза 7 — Retriever service API

**Цель:** retrieve как отдельный сервис.

| Шаг | Что делаешь |
|---|---|
| 7.1 | Эндпоинты: `/ingest`, `/search`, `/health` |
| 7.2 | REST-контракты + pydantic-схемы |
| 7.3 | Логи запросов в Postgres |

**Стек:** `fastAPI`, `REST-api`, `Python`, `Docker`, `SQL || PostGreSQL`, `git`

---

## Фаза 8 — RAG chain (генерация)

**Цель:** вопрос → контекст → ответ с цитатами на заметки.

| Шаг | Что делаешь |
|---|---|
| 8.1 | Промпт: роль + контекст + вопрос + «ссылайся на [[note]]» |
| 8.2 | Budgeted context pack (лимит токенов) |
| 8.3 | Structured output (JSON: answer, citations[], confidence) |
| 8.4 | Сначала API LLM; позже — локальная модель |

**Стек:** `RAG`, `LLM`, `LangChain`, `Transformers`, `fastAPI`

---

## Фаза 9 — Agents / оркестрация (LangGraph)

**Цель:** граф с ветками, не один прямой chain.

| Шаг | Узел графа |
|---|---|
| 9.1 | Classify intent (ML-модель или LLM) |
| 9.2 | Rewrite query *(опционально)* |
| 9.3 | Retrieve hybrid |
| 9.4 | Rerank (cross-encoder / LLM-rerank) |
| 9.5 | Generate / refuse if weak context |
| 9.6 | Self-check (короткий verify pass) |
| 9.7 | Cache lookup/write |

**Стек:** `LangGraph`, `LangChain`, `RAG`, `LLM`, `Python`, `fastAPI`

---

## Фаза 10 — Кеш и экономия токенов (−50%+)

**Цель:** БД + хуки.

| Шаг | Что |
|---|---|
| 10.1 | Exact cache: hash(q, prompt_ver, index_ver) → answer |
| 10.2 | Semantic cache в vector store |
| 10.3 | Session memory + summary + last-K (не тащить чанки в history) |
| 10.4 | Хуки before/after LLM в графе |

**Стек:** `SQL || PostGreSQL`, `Qdrant` *или* `pgvectors`, `LangGraph`, `LLM`, `Python`

---

## Фаза 11 — Reranking и «нейронка для поиска»

**Цель:** второй этап ранжирования.

| Шаг | Что |
|---|---|
| 11.1 | Cross-encoder rerank top-50 → top-5 |
| 11.2 | Сравнить nDCG/MRR до/после |
| 11.3 | *(опционально)* fine-tune reranker/embedding на парах вопрос–чанк |

**Стек:** `Transformers`, `Pytorch`, `Fine-tuning`, `RAG`, `ML`, `MLFlow`

---

## Фаза 12 — Eval (прод-качество)

**Цель:** цифры как у эталона + RAGAS.  
См. также метрики в конце [[ML main skills]].

| Шаг | Что |
|---|---|
| 12.1 | Gold: 40–100 вопросов по DLS2 + релевантные note/chunk ids |
| 12.2 | Retrieval: **nDCG@k**, **MRR@k** |
| 12.3 | Generation: Faithfulness, Answer Relevancy, Context Precision/Recall (`eval of rag(RAGAS)`) |
| 12.4 | Ops: latency p95, tokens/q, cost/q, ingest success rate |
| 12.5 | Таблица абляций в MLFlow |

**Стек:** `eval of rag(RAGAS)`, `Python`, `pandas`, `ML`, `Теория вероятностей`, `MLFlow`, `jupyter notebook`

> Eval лучше **вклинить сразу после первого generate** (не ждать конца всех фаз).

---

## Фаза 13 — Serving LLM (API vs self-host)

**Цель:** закрыть `vLLM` и cost/latency.

| Шаг | Что |
|---|---|
| 13.1 | v1: облачный `LLM` API |
| 13.2 | v2: opensource LLM через `vLLM` (OpenAI-compatible) |
| 13.3 | Router: tiny model на classify/rewrite, bigger на final answer |

**Стек:** `LLM`, `vLLM`, `Docker`, `Transformers`, `Pytorch`, `fastAPI`

---

## Фаза 14 — Fine-tuning (узкий, закрывает skill)

**Цель:** один прикладной тюнинг, не «донаобучить ради галочки».

Варианты (выбрать один):
- embedding/reranker на своих query–chunk
- small classifier intent (если деревья слабые)
- LoRA на маленькой модели под стиль ответов по конспектам

**Стек:** `Fine-tuning`, `Pytorch`, `Transformers`, `MLFlow`, `Google collab`, `ML`, `Теория вероятностей`

---

## Фаза 15 — Продуктовая оболочка

**Цель:** ежедневное использование.

| Шаг | Что |
|---|---|
| 15.1 | Chat API + простой UI или Telegram later |
| 15.2 | Ответ всегда с `[[wikilinks]]` / path цитат |
| 15.3 | Ingest hook: изменение md → reindex note |

**Стек:** `fastAPI`, `REST-api`, `Python`, `Docker`, `SQL || PostGreSQL`, `LangGraph`

---

## Фаза 16 — MLOps / выкладка

**Цель:** «как в проде», даже если pet.

| Шаг | Что |
|---|---|
| 16.1 | Docker images: api, worker-ingest, vector DB, postgres |
| 16.2 | CI/CD: test + build + deploy staging |
| 16.3 | K8s манифесты (kind/k3d или remote) — api + vLLM later |
| 16.4 | MLflow tracking server в compose |
| 16.5 | Healthchecks, логи, базовые метрики |

**Стек:** `Docker`, `CI/CD`, `Kubernetis`, `MLFlow`, `fastAPI`, `git`

---

## Фаза 17 — Портфолио-упаковка

**Цель:** resume-ready.

| Шаг | Что |
|---|---|
| 17.1 | README: корпус, стек, таблица до/после метрик |
| 17.2 | 2–3 абляции с цифрами |
| 17.3 | Короткое демо (скрипт/видео) |

**Стек:** `git` + всё выше как evidence.

---

## Критический путь (порядок внедрения)

```text
0 Каркас
→ 1 EDA corpus (DLS2)
→ 2 Postgres schema
→ 3 Chunking
→ 4 Embeddings
→ 5 Hybrid index (pgvector ИЛИ Qdrant + BM25)
→ 7 FastAPI /search
→ 8 LangChain RAG generate
→ 12 Eval gold (nDCG/MRR/RAGAS)  ← не откладывать
→ 9 LangGraph orchestration
→ 10 Cache/token budget
→ 11 Rerank
→ 6 Classic ML router/classifier
→ 13 vLLM
→ 14 Fine-tune (один узкий)
→ 15 Product UX
→ 16 Docker/CI/K8s/MLflow
→ 17 Portfolio
```

---

## MVP (если резать scope)

**Обязательный минимум:**  
фазы `1 → 2 → 3 → 4 → 5(pgvector) → 7 → 8 → 12 → 9 → 10` + Docker + git + FastAPI.

**Отложить:** K8s deep, fine-tune, второй vector DB, оба бустинга сразу, seaborn как навык.

---

## Матрица: skill → фазы

| Skill | Фазы | Роль |
|---|---|---|
| RAG | 8–12, 15 | ядро |
| LangChain | 3, 8 | split/chain/prompts |
| LangGraph | 9–10, 15 | агенты/ветки/кеш-хуки |
| LLM | 8–13, 15 | генерация |
| vLLM | 13, 16 | self-host serve |
| Qdrant | 5, 10 | vector DB *(alt к pgvector)* |
| pgvectors | 5, 10 | vector в Postgres *(alt к Qdrant)* |
| Python | все | основа |
| Pytorch | 4, 11, 13, 14 | embed/rerank/train/serve |
| Transformers | 4, 8, 11, 14 | модели/токенизация |
| Fine-tuning | 14 (11) | свой тюнинг |
| fastAPI + REST-api | 7, 15, 16 | сервис |
| SQL \|\| PostGreSQL | 2, 5, 7, 10 | данные/логи/кеш |
| Docker | 0, 2, 5, 13, 16 | упаковка |
| Kubernetis | 16 | оркестрация деплоя |
| CI/CD | 0, 16 | автопроверка/деплой |
| MLFlow | 3–6, 11–14, 16 | эксперименты |
| eval of rag(RAGAS) | 12 | quality gen |
| ML + scikit-learn | 6, 12 | классификаторы, метрики |
| XGBoost / catboost | 6 | *взаимозамена* |
| pandas / Numpy | 1, 6, 12 | EDA/фичи/отчёты |
| Теория вероятностей | 6, 12 | thresholds, метрики, ablations |
| git | 0, 17 | версия |
| jupyter / Colab | 1, 4, 12, 14 | EDA/GPU train |
| seaborn | 1, 12 | *только лёгкие графики* |

---

## Definition of Done (можно в резюме)

- [ ] Корпус DLS2 проиндексирован, ingest success ~100% на стабильном прогоне
- [ ] Hybrid retrieve + ответы с цитатами на заметки (`[[wikilinks]]` / path)
- [ ] Таблица: nDCG@k / MRR@k / RAGAS / latency / tokens до и после 2–3 улучшений
- [ ] FastAPI сервис в Docker; LangGraph с cache/router
- [ ] Один classic ML-классификатор (intent) на XGBoost *или* CatBoost
- [ ] README с цифрами

---

## Связанные заметки

- [[ML main skills]] — скиллы + разбор метрик Maly
- [[ML_ideal candidate_template]] — учебный образец резюме + оценка часов на стек
- Метрики для eval: nDCG@k, MRR@k, Faithfulness, Answer Relevancy, latency, tokens, cost, success rate

---

*Конец плана.*

ИНТЕГРАЦИЯ КАК ЧАТ В ТГ ЧЕРЕЗ ASYNCIO