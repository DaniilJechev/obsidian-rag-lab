# Sprint 23 — RAGAS runtime + OpenRouter model bake-off

> Статус: `planned`
>
> Ветка: `sprint/23-openrouter-model-bakeoff` (создаётся только при старте
> реализации, после merge Sprint 22)
>
> Связанная фаза roadmap: `Фаза 10`
>
> Backlog: `MLOPS-002`
>
> GitHub: [Issue #59](https://github.com/DaniilJechev/obsidian-rag-lab/issues/59),
> [Milestone Phase 10](https://github.com/DaniilJechev/obsidian-rag-lab/milestone/10)

## Sprint Goal

Сначала починить runtime пакета `ragas` и считать Faithfulness / Answer
Relevancy **протоколом фреймворка**, не нашим JSON-судьёй. Затем на том
же gold subset, том же k и **замороженном ragas-judge** сравнить 2–3
generate-модели по RAGAS + tokens/latency/cost. Не «на глаз».

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
сначала чинит runtime ragas, потом гоняет bake-off уже на нём.

Phase 10 закрывается после merge **этого** спринта (оба Issue на
Milestone 10 закрыты).

## Scope

Порядок обязательный: **сначала ragas runtime, потом bake-off**. Иначе
таблица смешает два судьи.

### A — внедрение ragas framework

- [ ] `import ragas` проходит в нашем venv/CI без Google Vertex.
      Предпочтительный путь: bump `ragas`, если вышла версия с lazy
      Vertex-import ([issue #2745](https://github.com/vibrantlabsai/ragas/issues/2745)).
      Не ставить `langchain-google-vertexai` «чтобы импорт завёлся» —
      мы Vertex не зовём, а 0.4.3 всё равно импортирует старый путь.
      Даунгрейд всего LangChain стека до 0.2/0.3 **не** делать: проект
      уже на `langchain-core>=1.5.4` (chunking).
- [ ] `OpenRouterJsonJudge` заменить реализацией `GenerationJudge`,
      которая гоняет **ragas Faithfulness** и **ragas Answer Relevancy**
      на packed contexts из `/generate`. LLM судьи — OpenRouter
      (pin отдельным `judge_model`, как сейчас).
- [ ] Для Answer Relevancy нужен embedder: default — уже стоящий
      local `multilingual-e5-small`, не OpenAI embeddings. Иначе bake-off
      платит за эмбеддинги судейских вопросов.
- [ ] Context Precision / Recall **оставить note-level proxy**
      (`source_path` ∈ gold `relevant_notes`). В gold нет reference
      answer, ragas Context Recall из коробки считать нечем.
- [ ] CI по-прежнему без live `evaluate()` и без `OPENROUTER_API_KEY`:
      моки/контракт судьи. Импорт ragas в тестах допустим только если
      он стабильно зелёный в Linux CI.
- [ ] В MLflow явно тегировать `judge_backend=ragas` и `judge_scale=0-1`
      (Sprint 22 JSON-судья — целые 0–5; числа **не** класть в одну таблицу
      без пересчёта). Native ragas 0–1 не рескейлить в 0–5.

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
- [ ] Повтор human не обязателен; если Sprint 22 не добил sample —
      добить здесь. Human остаётся 0–5; ragas-числа 0–1 — в notes явно
      написать, что шкалы разные.
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
- Рабочий `import ragas` + `GenerationJudge` на метриках пакета.
- Правки YAML/матрицы моделей.
- Таблица RAGAS + usage в Validation Evidence после live.

## Acceptance Criteria

- [ ] `import ragas` не падает; live считает Faithfulness / Answer
      Relevancy через пакет, не через `_JUDGE_SYSTEM` JSON.
- [ ] Context P/R по-прежнему note-level proxy; это записано в report.
- [ ] ≥2 generate-модели прогнаны на одном subset, одном gold version,
      одном k, одном ragas-judge.
- [ ] Таблица RAGAS + tokens/latency/cost; числа только из реальных runs.
- [ ] Контроль mini — ragas-прогон Sprint 23, не JSON-цифры Sprint 22.
- [ ] CI по-прежнему без live ключа.
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

## Validation Evidence

### Commands

```text
(ожидается после реализации; не раньше merge Sprint 22)
```

### Test and Lint Results

- Tests: не запускались
- Lint: не запускался
- CI: нет

### Metrics

Bake-off таблица — только после реальных runs.

## Review

### Completed

- Планирование Sprint 23 зафиксировано.

### Not Completed

- Починить `import ragas`; wiring Faithfulness / Answer Relevancy.
- Выбор 1–2 моделей кроме mini; live bake-off на ragas-judge.

### Changed Decisions

- Bake-off вынесен из Sprint 22 в отдельный Sprint 23 / `MLOPS-002`.
- Sprint 23 больше не «тот же JSON-judge, что 22»: сначала пакет ragas,
  контроль mini переснимается. Шкала ragas native 0–1, не целые 0–5 Sprint 22.

### Technical Debt

- Нет (реализация не начата).

## Retrospective

Заполняется при closeout.

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `planned`

**Дата завершения:** —
