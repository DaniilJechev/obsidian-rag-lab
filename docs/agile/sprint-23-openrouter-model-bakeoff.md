# Sprint 23 — RAGAS runtime + OpenRouter model bake-off

> Статус: `in-progress`
>
> Ветка: `sprint/23-openrouter-model-bakeoff`
>
> Связанная фаза roadmap: `Фаза 10`
>
> Backlog: `MLOPS-002`
>
> GitHub: [Issue #59](https://github.com/DaniilJechev/obsidian-rag-lab/issues/59),
> [Milestone Phase 10](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/10)

## Sprint Goal

Сначала владелец проставляет целые 0–5 в `evals/human/sprint22_sample.yaml`
по pack `sprint22_review.yaml` (carry-over из Sprint 22). Затем **добавить**
runtime пакета `ragas` как второй judge-backend (шкала native 0–1). JSON-судья
`OpenRouterJsonJudge` **не удаляется**: человеческая разметка и калибровка
остаются на целых 0–5. Затем на том же gold subset, том же k и **замороженном
ragas-judge** сравнить 2–3 generate-модели по RAGAS + tokens/latency/cost.
Не «на глаз». Не смешивать 0–5 и 0–1 в одной таблице.

## Why

Sprint 22 даёт HTTP-harness и baseline на `openai/gpt-4o-mini`, но судья
v1 — один JSON-complete с теми же именами осей. Пакет `ragas==0.4.3`
уже в lockfile, однако `import ragas` падает: в `ragas/llms/base.py`
жёсткий импорт `langchain_community.chat_models.vertexai`, а в
`langchain-community==0.4.2` этот модуль убрали (Vertex вынесли в
`langchain-google-vertexai`). Мы Vertex не используем; от этого импорт
ломается у всех.

Пока bake-off идёт на JSON-судье, сравнивать модели дешевле, но слабее
по смыслу Faithfulness (нет claim-decomposition). Поэтому Sprint 23
сначала чинит runtime ragas **рядом** с JSON 0–5, потом гоняет bake-off
уже на ragas 0–1. JSON остаётся кнопкой `judge_backend: json`.

Phase 10 закрывается после merge **этого** спринта (оба Issue на
Milestone 10 закрыты).

## Scope

Порядок обязательный: **human scores → ragas runtime → bake-off**.
Шкала human остаётся 0–5; ragas native 0–1 — не смешивать в одной таблице.

### 0 — human sample (carry-over Sprint 22)

- [x] Владелец заполняет `evals/human/sprint22_sample.yaml` целыми 0–5
      (`faithfulness`, `answer_relevancy`, `overall`) по
      `evals/human/sprint22_review.yaml`. Не копировать пятёрки JSON-судьи.
- [x] Расхождение human vs judge зафиксировать в этом sprint-доке
      (калибровка bias mini-as-judge). Фиктивные баллы не ставить.

### A — внедрение ragas framework

- [x] `import ragas` проходит в нашем venv/CI без Google Vertex.
      Предпочтительный путь: bump `ragas`, если вышла версия с lazy
      Vertex-import ([issue #2745](https://github.com/vibrantlabsai/ragas/issues/2745)).
      Не ставить `langchain-google-vertexai` «чтобы импорт завёлся» —
      мы Vertex не зовём, а 0.4.3 всё равно импортирует старый путь.
      Даунгрейд всего LangChain стека до 0.2/0.3 **не** делать: проект
      уже на `langchain-core>=1.5.4` (chunking). Workaround Sprint 23:
      stub `ChatVertexAI` / `VertexAI` перед `import ragas`
      (`eval/ragas_import.py`).
- [x] **Добавить** (не заменить) `GenerationJudge` на **ragas Faithfulness**
      и **ragas Answer Relevancy** по packed contexts из `/generate`.
      `OpenRouterJsonJudge` остаётся: целые 0–5, тот же контракт
      `judge.score()`. Выбор — `judge_backend: json | ragas` в
      `configs/eval/ragas.yaml`. LLM судьи — OpenRouter
      (pin отдельным `judge_model`, как сейчас).
- [x] Для Answer Relevancy нужен embedder: default — уже стоящий
      local `multilingual-e5-small`, не OpenAI embeddings. Иначе bake-off
      платит за эмбеддинги судейских вопросов.
- [x] Context Precision / Recall **оставить note-level proxy**
      (`source_path` ∈ gold `relevant_notes`). В gold нет reference
      answer, ragas Context Recall из коробки считать нечем.
- [x] CI по-прежнему без live `evaluate()` и без `OPENROUTER_API_KEY`:
      моки/контракт судьи. Импорт ragas в тестах допустим только если
      он стабильно зелёный в Linux CI.
- [x] В MLflow явно тегировать `judge_backend` и `judge_scale`
      (`0-5` для JSON, `0-1` для ragas). Числа **не** класть в одну таблицу
      без пересчёта. Native ragas 0–1 не рескейлить в 0–5.

### B — bake-off generate-моделей

- [ ] YAML-список моделей. Рекомендация: `openai/gpt-4o-mini` как
      контроль + 1–2 других id, которые выбираем при старте реализации.
      Не Ox Alpha по умолчанию (stealth/latency).
- [ ] Контроль mini — **новый** прогон на ragas-judge, не цифры JSON
      из Sprint 22. Те нельзя класть в одну таблицу.
- [ ] Judge **не** менять между строками bake-off (ни модель, ни
      версию ragas, ни embedder).
- [ ] Одна таблица в этом sprint-доке и MLflow Compare (несколько runs,
      теги `sprint=23`, `task=MLOPS-002`).
- [ ] Human 0–5 vs ragas 0–1 не класть в одну таблицу bake-off; калибровку
      human vs JSON-судья Sprint 22 писать отдельно (раздел 0).
- [ ] Регрессия harness только если сломается на второй модели
      (timeout, JSON parse) — точечный фикс, не третий eval-стек.

## Out of Scope

- Новый retriever, смена gold freeze, смена основной embedding-модели
  retrieval (e5 для **retrieval** остаётся; e5 как ragas-embedder —
  in scope).
- Подмена Context P/R на ragas LLM-P/R без reference answers.
- LangGraph, `generation_logs`, Telegram, vLLM.
- Третья модель сверх согласованных 2–3 «потому что интересно».
- Старт кода до merge Sprint 22.
- Реализация на ветке `main`.

## Expected Artifacts

- `docs/agile/sprint-23-openrouter-model-bakeoff.md` — этот документ.
- Заполненный `evals/human/sprint22_sample.yaml` (carry-over Sprint 22).
- Рабочий `import ragas` + второй `GenerationJudge` на метриках пакета
  (JSON 0–5 не удалён).
- Правки YAML/матрицы моделей.
- Таблица RAGAS + usage в Validation Evidence после live.

## Acceptance Criteria

- [x] `import ragas` не падает (тест + Vertex-stub). JSON 0–5 остаётся
      через `judge_backend: json` (human sample).
- [ ] Live `rag-cli ragas run` с `judge_backend: ragas` считает
      Faithfulness / Answer Relevancy через пакет (ещё не гоняли).
- [x] Context P/R по-прежнему note-level proxy; это записано в report.
- [ ] ≥2 generate-модели прогнаны на одном subset, одном gold version,
      одном k, одном ragas-judge.
- [ ] Таблица RAGAS + tokens/latency/cost; числа только из реальных runs.
- [ ] Контроль mini — ragas-прогон Sprint 23, не JSON-цифры Sprint 22.
- [ ] CI по-прежнему без live ключа.
- [x] Human sample Sprint 22 заполнен целыми 0–5; фиктивных баллов нет.
- [ ] Vault не изменён; секреты не в git.

## Definition of Done

- [ ] Все задачи из Scope выполнены или явно перенесены в backlog.
- [ ] Acceptance Criteria проверены.
- [ ] Тесты добавлены или обновлены и проходят.
- [ ] Ruff/lint проходит.
- [ ] CI проходит, если изменения отправлялись в remote.
- [ ] Read-only vault не изменён.
- [ ] Секреты не добавлены в Git.
- [ ] Документация и конфигурация обновлены, если это необходимо.
- [ ] Результаты и ограничения записаны в этот sprint-документ.
- [ ] Пользователь подтвердил завершение спринта.

## Dependencies and risks

- **Жёсткая зависимость:** код стартует только после merge Sprint 22.
  Issue открыт сразу, чтобы быть видимым на Milestone.
- `ragas==0.4.3` + `langchain-community==0.4.2` = import crash. Bump
  ragas может не выйти вовремя (фикс в upstream PR ещё не в релизе).
  Тогда нужен узкий workaround, который **не** даунгрейдит
  `langchain-core` проекта. Решение фиксируем в Execution Log.
- Answer Relevancy в ragas — несколько LLM-вызовов + эмбеддинги; subset
  15 станет заметно дороже/медленнее JSON-судьи. Concurrency держать.
- Стоимость судьи × N моделей; Cloudflare DME / VPN как в Sprint 21.
- Judge freeze: смена mini / версии ragas / embedder между строками
  делает таблицу несравнимой.
- `uv add` / `uv sync` по-прежнему только владелец.

## Estimate

14–20 часов: починка import + wiring ragas, затем live × N моделей.

## Proposed branch

`sprint/23-openrouter-model-bakeoff`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-24 | Planning | Документ создан вместе со Sprint 22; GitHub Issue [#59](https://github.com/DaniilJechev/obsidian-rag-lab/issues/59); код не начат |
| 2026-08-24 | Scope change | В Sprint 23 добавлен runtime ragas (Faithfulness / Answer Relevancy пакетом) **перед** bake-off. JSON-судья Sprint 22 остаётся v1 baseline, в одну таблицу с 23 не смешивать. |
| 2026-08-24 | Carry-over | Human scores 0–5 из Sprint 22 перенесены сюда: сначала разметка `sprint22_sample.yaml`, потом ragas runtime, потом bake-off. |
| 2026-08-25 | Human sample | Owner заполнил 10 id в `sprint22_sample.yaml`. Калибровка vs JSON-судья — в Validation Evidence. |
| 2026-08-25 | Live control mini | `rag-cli ragas run`, generate=`openai/gpt-4o-mini`, judge ragas 0–1. 15/15, skip 0. MLflow `7278da5caefc418382d762a8ed7ec155`. |

## Validation Evidence

### Commands

```text
uv run rag-cli ragas run
```

Контроль generate `openai/gpt-4o-mini`, judge ragas 0–1, subset 15, concurrency 1.
MLflow `7278da5caefc418382d762a8ed7ec155`. Wall ~516 s. JSON Sprint 22 сюда не класть.

### Test and Lint Results

- Tests: `uv run pytest -q --tb=line` → 215 passed, 1 skipped, 18 deselected.
- Lint: `uv run ruff check src/ tests/` → all checks passed.
- Human scores: `evals/human/sprint22_sample.yaml` (не `sprint22_review.yaml`).
  Review Sprint 22 — pack + JSON-судья; sample — owner.
  Live ragas пишет pack в `evals/human/sprint23_review.yaml`, чтобы не
  затереть JSON-pack, по которому уже стоят human 0–5.

### Metrics

JSON-судья Sprint 22 (канон MLflow `4663f6d7…`, 15 вопросов): faithfulness 4.6,
answer_relevancy 4.667. Ниже — только пересечение **тех же 10 id**, human vs
`judge:` в `sprint22_review.yaml`. Шкала целые 0–5. Pearson не считаем: n=10
и потолок пятёрок делают корреляцию бессмысленной.

Сводка (n=10):

| | Human mean | Judge mean | MAE | Exact match |
|---|---:|---:|---:|---:|
| Faithfulness | 4.5 | 4.7 | 0.8 | 5/10 |
| Answer relevancy | 4.9 | 4.7 | 0.4 | 8/10 |
| Overall (human only) | 4.9 | — | — | — |

По вопросам (human − judge):

| id | H F | J F | ΔF | H AR | J AR | ΔAR | H overall |
|---|---:|---:|---:|---:|---:|---:|---:|
| q001 | 4 | 5 | −1 | 5 | 5 | 0 | 5 |
| q002 | 5 | 5 | 0 | 5 | 5 | 0 | 5 |
| q003 | 5 | 5 | 0 | 5 | 5 | 0 | 5 |
| q004 | 4 | 5 | −1 | 5 | 5 | 0 | 5 |
| q005 | 5 | 5 | 0 | 5 | 5 | 0 | 5 |
| q006 | 5 | 2 | +3 | 5 | 2 | +3 | 5 |
| q007 | 5 | 5 | 0 | 4 | 5 | −1 | 5 |
| q009 | 3 | 5 | −2 | 5 | 5 | 0 | 4 |
| q010 | 5 | 5 | 0 | 5 | 5 | 0 | 5 |
| q011 | 4 | 5 | −1 | 5 | 5 | 0 | 5 |

Вывод: **AR почти совпадает** (потолок 5; единственный крупный разъезд —
q006). **F совпадает умеренно**: MAE 0.8 тянут q006 (+3) и q009 (−2), плюс
мелкие −1 на q001/q004/q011. На «лёгких» пересказах (q002, q003, q005, q010)
оба ставят 5.

- **q001:** в pack есть `DLS1/Dropout.md`; ответ с него списан. H F=4
  (не 0): утверждения ответа опираются на контекст. Overall=5.
- **q006:** модель отказалась по NMS и гадает MSE/IoU. Judge 2/2 ловит провал
  retrieval. H 5/5/5 — щедрый «честный отказ»; по протоколу AR должен быть
  низким (вопрос не закрыт).
- **q009:** H F=3 ближе к «учебниковый VAE при слабом pack», чем judge 5.

JSON-mini **не** калиброван как строгий F-судья: на 9/10 id он ставит 5.
Human sample это подтверждает; q006 ещё и расходится с согласованным
определением осей. Для bake-off Sprint 23 это аргумент считать ragas 0–1
**рядом** с JSON 0–5, а не усреднять шкалы и не выкидывать JSON.

Bake-off generate (ragas 0–1, один судья `openai/gpt-4o-mini`, тот же gold/k):

| generate | F | AR | ctx P | ctx R | scored/skip | mean gen ms | duration s | MLflow |
|---|---:|---:|---:|---:|---|---:|---:|---|
| openai/gpt-4o-mini | 0.779 | 0.898 | 0.785 | 0.622 | 15/0 | 4017 | 516 | `7278da5c…` |
| google/gemini-3.7-flash | — | — | — | — | — | — | — | — |

Context P/R — note-level proxy; на одном retriever должны быть близки между строками (меняется только generate). F/AR — native ragas, не Likert 0–5.

## Review

### Completed

- Планирование Sprint 23 зафиксировано.
- Human sample 10×0–5 в `sprint22_sample.yaml`; калибровка vs JSON-судья записана.
- JSON 0–5 сохранён; ragas 0–1 добавлен как `judge_backend: ragas`.
  `import ragas` в тестах проходит через Vertex-stub.

### Not Completed

- Live bake-off вторая generate-модель: `google/gemini-3.7-flash` (нужен `--build` API).

### Changed Decisions

- Bake-off вынесен из Sprint 22 в отдельный Sprint 23 / `MLOPS-002`.
- Sprint 23 **добавляет** пакет ragas (0–1), а не заменяет JSON-судью
  (0–5). Контроль mini на bake-off — новый ragas-прогон, не JSON-цифры
  Sprint 22. Шкалы не класть в одну таблицу без явной метки backend/scale.
- Human scores 0–5 — обязательный carry-over из Sprint 22, не optional.

### Technical Debt

- `ragas==0.4.3` жёстко импортирует удалённый Vertex-модуль
  `langchain_community`. Workaround: stub в `eval/ragas_import.py`, пока
  upstream не выпустит lazy import. Не ставить `langchain-google-vertexai`.
- `from ragas.metrics import faithfulness, answer_relevancy` deprecated
  к v1.0 в пользу `ragas.metrics.collections`. Пока 0.4.3 — оставляем
  старый import; миграция — когда bump ragas.

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `in-progress`

**Дата завершения:** —
