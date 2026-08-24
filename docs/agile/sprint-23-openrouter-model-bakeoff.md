# Sprint 23 — OpenRouter model bake-off

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

На **том же** gold subset, **том же** judge pin и том же RAGAS-harness
сравнить 2–3 generate-модели по RAGAS + tokens/latency/cost. Не «на глаз».

## Why

Sprint 22 даёт линейку и baseline на `openai/gpt-4o-mini`. Бывший roadmap
9.5 (сравнение моделей) без этой линейки был бы cost/latency и взгляд.
После merge 22 можно честно менять только generate-модель, держа
retrieval, gold, k и judge замороженными.

Phase 10 закрывается после merge **этого** спринта (оба Issue на
Milestone 10 закрыты).

## Scope

- [ ] YAML-список моделей. Рекомендация: `openai/gpt-4o-mini` как
      контроль + 1–2 других id, которые выбираем при старте реализации.
      Не Ox Alpha по умолчанию (stealth/latency).
- [ ] Judge **не** менять между строками bake-off.
- [ ] Одна таблица в этом sprint-доке и MLflow Compare (несколько runs,
      теги `sprint=23`, `task=MLOPS-002`).
- [ ] Повтор human не обязателен; если Sprint 22 не добил sample —
      добить здесь.
- [ ] Регрессия harness только если сломается на второй модели
      (timeout, JSON parse) — точечный фикс, не новый eval-стек.

## Out of Scope

- Новый retriever, смена gold freeze, смена embedding-модели.
- LangGraph, `generation_logs`, Telegram, vLLM.
- Третья модель сверх согласованных 2–3 «потому что интересно».
- Старт кода до merge Sprint 22.
- Реализация на ветке `main`.

## Expected Artifacts

- `docs/agile/sprint-23-openrouter-model-bakeoff.md` — этот документ.
- Правки YAML/матрицы моделей, не новый пакет с нуля.
- Таблица RAGAS + usage в Validation Evidence после live.

## Acceptance Criteria

- [ ] ≥2 модели прогнаны на одном subset, одном gold version, одном k.
- [ ] Таблица RAGAS + tokens/latency/cost; числа только из реальных runs.
- [ ] Контроль mini сопоставим со Sprint 22 (тот же gold / k / judge).
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
- Стоимость судьи × N моделей; Cloudflare DME / VPN как в Sprint 21.
- Judge freeze: смена mini на другую judge-модель между строками
  делает таблицу несравнимой.

## Estimate

8–12 часов, в основном live (сеть × N моделей).

## Proposed branch

`sprint/23-openrouter-model-bakeoff`

## Execution Log

| Дата | Действие / решение | Результат |
|---|---|---|
| 2026-08-24 | Planning | Документ создан вместе со Sprint 22; GitHub Issue [#59](https://github.com/DaniilJechev/obsidian-rag-lab/issues/59); код не начат |

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

- Выбор 1–2 моделей кроме mini; live bake-off.

### Changed Decisions

- Bake-off вынесен из Sprint 22 в отдельный Sprint 23 / `MLOPS-002`.

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
