# Sprint {{NUMBER}} — {{SHORT_NAME}}

> Статус: `planned`
>
> Ветка: `sprint/{{NUMBER}}-{{SLUG}}`
>
> Связанная фаза roadmap: `Фаза {{PHASE}}`

## Sprint Goal

<!--
Одно короткое утверждение о главном проверяемом результате спринта.
Формулируй результат, а не список действий.
-->

{{GOAL}}

## Why

<!--
Почему этот результат нужен проекту именно сейчас?
Как он связан с текущей фазой и следующими шагами?
-->

{{WHY}}

## Scope

<!--
Что входит в этот спринт.
Каждый пункт должен быть достаточно конкретным, чтобы проверить его выполнение.
-->

- [ ] {{TASK_1}}
- [ ] {{TASK_2}}
- [ ] {{TASK_3}}

## Out of Scope

<!--
Что сознательно не делаем в этом спринте.
Новые идеи добавляем в backlog, а не расширяем scope молча.
-->

- {{OUT_OF_SCOPE_1}}
- {{OUT_OF_SCOPE_2}}

## Expected Artifacts

<!--
Какие файлы, конфигурации, отчёты, тесты или измерения должны появиться.
-->

- `{{ARTIFACT_PATH_1}}` — {{ARTIFACT_DESCRIPTION_1}}
- `{{ARTIFACT_PATH_2}}` — {{ARTIFACT_DESCRIPTION_2}}

## Acceptance Criteria

<!--
Проверяемые условия, по которым владелец проекта принимает результат.
-->

- [ ] {{ACCEPTANCE_CRITERION_1}}
- [ ] {{ACCEPTANCE_CRITERION_2}}
- [ ] {{ACCEPTANCE_CRITERION_3}}

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

## Execution Log

<!--
Кратко фиксируй существенные действия, решения и блокеры по мере работы.
-->

| Дата | Действие / решение | Результат |
|---|---|---|
| {{DATE}} | {{ACTION_OR_DECISION}} | {{RESULT}} |

## Validation Evidence

<!--
Команды, тесты, CI runs, метрики и другие проверяемые свидетельства.
Не записывай выдуманные результаты.
-->

### Commands

```text
{{COMMAND_1}}
{{COMMAND_2}}
```

### Test and Lint Results

- Tests: `{{TEST_RESULT}}`
- Lint: `{{LINT_RESULT}}`
- CI: `{{CI_RESULT}}`

### Metrics

| Metric | Value | Context |
|---|---:|---|
| {{METRIC_NAME}} | {{METRIC_VALUE}} | {{METRIC_CONTEXT}} |

## Review

### Completed

- {{COMPLETED_ITEM_1}}

### Not Completed

- {{NOT_COMPLETED_ITEM_1}}

### Changed Decisions

- {{CHANGED_DECISION_1}}

### Technical Debt

- {{TECHNICAL_DEBT_1}}

## Retrospective

### What Went Well

- {{WENT_WELL_1}}

### What Was Difficult

- {{DIFFICULTY_1}}

### What We Will Change

- {{CHANGE_1}}

### Backlog Updates

- Добавить:
  - {{BACKLOG_ADDITION_1}}
- Перенести:
  - {{BACKLOG_CARRYOVER_1}}
- Изменить приоритет:
  - {{BACKLOG_PRIORITY_CHANGE_1}}

## Completion

- [ ] Definition of Done проверен.
- [ ] Review проведён.
- [ ] Retrospective заполнена.
- [ ] Commit/PR/merge выполнены по согласованному Git workflow.
- [ ] Backlog обновлён.
- [ ] Следующий sprint выбран или запланирован.

**Итоговый статус:** `{{FINAL_STATUS}}`

**Дата завершения:** `{{COMPLETION_DATE}}`

