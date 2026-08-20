# План: RAG для Obsidian vault

**Цель:** production-like pet RAG по vault (v1 — allowlist `ML_NLP/DLS1/` + `ML_NLP/DLS2/`), с покрытием большинства скиллов из [[ML main skills]].  
**Корпус (ориентир):** DLS1+DLS2 внутри `obsidianNotes/ML_NLP/`; `ML_NLP/NLP/` вне allowlist.  
**Легенда стека:** **основной** / *замена* / *(опционально)*.  
`seaborn` — только лёгкая визуализация, не ядро (см. пометку в ML main skills).

### Актуальное состояние (2026-08-20)

Нумерация фаз **ниже в этом snapshot** — историческая копия vault-плана.
Живой порядок — Cursor roadmap
(`.cursor/plans/rag_pipeline_roadmap_7c0acd14.plan.md`) и `docs/agile/`.

- **На `main`:** фазы 0–5 живого roadmap закрыты. PostgreSQL — source of
  truth для `notes`/`chunks`. Retrieval default: Qdrant named vectors
  `dense` + `bm25`, Python RRF, CLI `rag-cli search dense|bm25|hybrid`.
- **Phase 6 (pgvector comparison):** закрыта как **branch-only**. Код на
  `sprint/16-pgvector-dense-experiment` (`bd39d20`), в `main` не влит.
  Live dense top-k совпал с Qdrant; BM25/hybrid в Postgres не делали.
  Дальше с pgvector не работаем.
- **Следующее на `main`:** живая **Phase 7** gold eval (note-level nDCG/MRR),
  не FastAPI. Спринты: 17 (`eval_items` + gold + harness), 18 (live baseline
  dense/bm25/hybrid в MLflow).
- **Корпус:** `obsidianNotes/ML_NLP/DLS1/` и `obsidianNotes/ML_NLP/DLS2/`.
  `OBSIDIAN_VAULT_ROOT` = `obsidianNotes/ML_NLP`. `ML_NLP/NLP/` не в allowlist.
- **Живой порядок после generate:** Phase 9 OpenRouter generate → **Phase 10 RAGAS**
  (generation baseline) → Phase 11 LangGraph → 12 rerank → 13 cache → 14 cloud →
  15 paid embeddings → 16 vLLM. RAGAS специально стоит сразу после первого
  generate, чтобы LangGraph/cache/rerank мерялись «до/после», а не на глаз.
  Исторические заголовки «Фаза 9 LangGraph» / «Фаза 12 Eval» ниже — нумерация
  vault-оригинала, не живого roadmap.
- Sprint-док: `docs/agile/sprint-16-pgvector-dense-experiment.md`.

---

## Легенда взаимозамен

Не делать deep сразу в обе стороны:

| Пара | Правило |
|---|---|
| `Qdrant` vs `pgvectors` | Qdrant — deep на `main`; pgvector — comparison на ветке Sprint 16, не merge |
| `XGBoost` vs `catboost` | достаточно одного |
| облачный `LLM` vs `vLLM` | сначала API, потом self-host backend |
| `LangChain` vs свой pipeline | LangChain-first splitters/adapters; собственные contracts, persistence и experiment logic остаются прозрачными |

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
| 1.1 | Allowlist: v1 = `ML_NLP/DLS1/` + `ML_NLP/DLS2/` |
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

**Цель:** LangChain-first recursive structural chunking под retrieval units
для заметок Obsidian с сохранением heading context, offsets и versioned metadata.

**GitHub tracking:** все три sprint-а относятся к общей milestone
[Phase 3 — LangChain-first Chunking](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/5):
Sprint 7 — [#19](https://github.com/DaniilJechev/obsidian-rag-lab/issues/19),
Sprint 8 — [#20](https://github.com/DaniilJechev/obsidian-rag-lab/issues/20),
Sprint 9 — [#21](https://github.com/DaniilJechev/obsidian-rag-lab/issues/21).

| Шаг | Что делаешь |
|---|---|
| 3.1 | Sprint 7: typed Markdown blocks, `SectionTree`, offsets и LangChain `Document(page_content, metadata)` |
| 3.2 | Sprint 8: LangChain recursive structural splitter, heading в chunk text, selective overlap и versioned PostgreSQL persistence |
| 3.3 | Sprint 9: YAML-driven candidates `256/512/1024`, structural metrics и ранний MLflow tracking |
| 3.4 | Сохранять parent `note_id`, section path, parser/content versions и chunking version; старые chunk versions не удалять автоматически |
| 3.5 | Wikilinks хранить как metadata/graph hint; LangGraph orchestration — живая Phase 11 |

**Стек:** `Python`, `LangChain` (основной splitter/runtime contract), PostgreSQL,
YAML configs, local JSON/CSV/Markdown/PNG artifacts и `MLflow` для tracking
parameters, metrics, configs и artifacts. `LangGraph` в живой Phase 11.

### Phase 3 — Sprint boundaries

**Sprint 7 — LangChain Documents and SectionTree**

- GitHub: [Issue #19](https://github.com/DaniilJechev/obsidian-rag-lab/issues/19)
- typed blocks и SectionTree с `direct_body`, children, section path и offsets;
- pre-heading text, пустые headings, code/list/table blocks и wikilinks metadata;
- `ChunkingPolicy`, typed YAML validation и metadata propagation;
- unit tests и базовый MLflow run для sectionization.

**Sprint 8 — Versioned Recursive Structural Chunks**

- GitHub: [Issue #20](https://github.com/DaniilJechev/obsidian-rag-lab/issues/20)
- LangChain recursive structural splitter поверх section/block Documents;
- heading включается в `text`, metadata сохраняет note/section/offset context;
- overlap только для oversized sections;
- `(note_id, chunking_version, chunk_index)` как version-aware identity;
- старые версии сохраняются для audit/rollback, active version выбирается явно;
- deterministic output, idempotent regeneration и PostgreSQL transaction tests.

**Sprint 9 — Controlled Experiments and MLflow Baseline**

- GitHub: [Issue #21](https://github.com/DaniilJechev/obsidian-rag-lab/issues/21)
- YAML-driven сравнение candidate sizes `256/512/1024`;
- overlap comparison только для больших текстовых секций;
- MLflow parameters, metrics, Git commit, config snapshots и generated artifacts;
- JSON/CSV/Markdown/PNG reports;
- выбор baseline и документированный `chunk → embedding` handoff для Phase 4.

Phase 3 не реализует embeddings, Qdrant, BM25/RRF, retrieval evaluation, LLM,
FastAPI или LangGraph. Semantic splitting остаётся optional experiment после
появления embeddings, а practical LangGraph graph/state orchestration относится
к живой Phase 11 (после RAGAS).

---

## Фаза 4 — Эмбеддинги и векторизация

**Цель:** dense index.

| Шаг | Что делаешь |
|---|---|
| 4.1 | Выбрать embedding-модель (мультиязычная RU/EN, BGE-M3-класс) |
| 4.2 | Батч-эмбеддинг чанков + ретраи; success rate пайплайна |
| 4.3 | A/B двух моделей эмбеддингов на одном gold-сете |

**Стек:** `Python`, `Transformers`, `Pytorch`, `Numpy`, `Docker`; `MLflow` уже
используется с Phase 3 для наследуемого experiment tracking.
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
- Выбранный Phase 5 путь: `Qdrant` named vectors `dense` (cosine/HNSW) +
  `bm25` (sparse IDF, `Qdrant/bm25`) на одном point; Python RRF для hybrid
  fusion. PostgreSQL остаётся source of truth для chunks, но не сканируется
  на query path для lexical search.
- `asyncio` + `asyncio.to_thread` используются в retrieval pipeline для
  параллельного запуска синхронных dense и BM25 веток после query embedding.

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

> В живом roadmap это Phase 9 OpenRouter generate. Сразу после неё — **живая
> Phase 10 RAGAS**, не LangGraph.

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

> В живом roadmap LangGraph — **Phase 11**, после RAGAS baseline (Phase 10).

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
| 12.1 | Gold: в живом roadmap — 50 note-level вопросов DLS1+DLS2 в `eval_items` |
| 12.2 | Retrieval: **nDCG@k**, **MRR@k** |
| 12.3 | Generation: Faithfulness, Answer Relevancy, Context Precision/Recall (`eval of rag(RAGAS)`) |
| 12.4 | Ops: latency p95, tokens/q, cost/q, ingest success rate |
| 12.5 | Таблица абляций в MLFlow |

**Стек:** `eval of rag(RAGAS)`, `Python`, `pandas`, `ML`, `Теория вероятностей`, `MLFlow`, `jupyter notebook`

> Eval лучше **вклинить сразу после первого generate** (не ждать конца всех фаз).
> В живом roadmap это Phase 10 RAGAS сразу после Phase 9 OpenRouter generate;
> retrieval nDCG/MRR — отдельная живая Phase 7, до API и generate.

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

Ниже — **исторические** номера vault-snapshot. Живой порядок (Cursor roadmap):
`… → 7 nDCG/MRR → 8 FastAPI → 9 generate → 10 RAGAS → 11 LangGraph → 12 rerank
→ 13 cache → …`

```text
0 Каркас
→ 1 EDA corpus (DLS2)
→ 2 Postgres schema
→ 3 Chunking
→ 4 Embeddings
→ 5 Hybrid index (Qdrant + BM25 на `main`; pgvector comparison — ветка Sprint 16, не в `main`)
→ 7 FastAPI /search
→ 8 LangChain RAG generate
→ RAGAS / generation eval  ← сразу после generate (живой Phase 10)
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
фазы `1 → 2 → 3 → 4 → 5(Qdrant hybrid) → 7 → 8 → RAGAS сразу после generate → 9 → 10` + Docker + git + FastAPI.  
pgvector не входит в MVP на `main` (Sprint 16 остался на отдельной ветке).

**Отложить:** K8s deep, fine-tune, второй vector DB, оба бустинга сразу, seaborn как навык.

---

## Матрица: skill → фазы

| Skill | Фазы | Роль |
|---|---|---|
| RAG | 8–12, 15 | ядро |
| LangChain | 3, 8 | split/chain/prompts |
| LangGraph | 9–10, 15 в этом snapshot; **живая Phase 11** | агенты/ветки/кеш-хуки |
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
| eval of rag(RAGAS) | 12 в этом snapshot; **живая Phase 10** сразу после generate | quality gen |
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