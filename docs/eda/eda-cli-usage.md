# EDA CLI — инструкция по запуску

## Назначение

EDA-модуль читает готовый inventory корпуса и создаёт:

- отдельные PNG-файлы для информативных распределений;
- тематический Markdown-отчёт со стандартными относительными image links,
  совместимыми с Cursor Markdown Preview и Obsidian;
- список duplicate-файлов в консоли и Markdown-отчёте.

Входной artifact:

```text
artifacts/corpus_inventory.json
```

Папка `artifacts/` является локальной generated-папкой: она не индексируется
Cursor и не должна автоматически попадать в Git.

## Запуск со стандартными путями

Если inventory уже создан manual-тестом, достаточно выполнить:

```powershell
uv run python -m rag_based_on_obsidian.corpus.eda
```

Скрипт использует defaults:

```text
input:  artifacts/corpus_inventory.json
output: artifacts/eda/
report: artifacts/eda/corpus_eda.md
```

Результат:

```text
artifacts/
└── eda/
    ├── document_file_size_distribution.png
    ├── document_word_count_distribution.png
    ├── document_size_vs_word_count.png
    ├── document_heading_section_length_by_level.png
    ├── paragraph_length_distribution.png
    ├── paragraph_length_by_heading_level.png
    ├── directory_comparison_file_size.png
    └── corpus_eda.md
```

В консоли появятся summary и duplicate-группы:

```text
=== Duplicate files ===
Group 1 — hash abc123...
  - DLS1/example.md
  - DLS2/example-copy.md
EDA figures directory: artifacts\eda\
EDA report: artifacts\eda\corpus_eda.md
```

Числа и пути в примере условные. Реальные значения берутся из
`corpus_inventory.json`.

## Запуск с пользовательскими путями

Defaults можно переопределить:

```powershell
uv run python -m rag_based_on_obsidian.corpus.eda `
  --input artifacts/other_inventory.json `
  --output artifacts/custom/ `
  --report artifacts/custom/report.md
```

Одной строкой:

```powershell
uv run python -m rag_based_on_obsidian.corpus.eda --input artifacts/other_inventory.json --output artifacts/custom --report artifacts/custom/report.md
```

Аргументы:

- `--input` — путь к JSON inventory;
- `--output` — каталог для PNG-файлов;
- `--report` — путь к Markdown-отчёту.

Если аргумент не указан, используется его стандартный путь.

## Что означает `uv run python -m`

Команда выполняется так:

```text
PowerShell
  ↓
uv run
  ↓
Python из project environment
  ↓
-m rag_based_on_obsidian.corpus.eda
  ↓
main()
  ↓
argparse разбирает --input, --output и --report
```

`--input`, `--output` и `--report` не являются аргументами функции `main`
напрямую. Они находятся в командной строке, затем `argparse` превращает их в
поля:

```python
arguments.input
arguments.output
arguments.report
```

## Markdown-отчёт

`corpus_eda.md` содержит стандартные относительные Markdown image links,
которые отображаются в Cursor Markdown Preview:

```markdown
![Document Word Count Distribution](document_word_count_distribution.png)
```

В отчёте также находятся summary и полный список файлов в duplicate-группах.
График показывает общую картину, а Markdown и консоль сохраняют конкретные
пути, которые неудобно размещать внутри диаграммы.

## Графики и chunking-метрики

Отчёт может содержать отдельные графики:

1. распределение размеров файлов;
2. распределение количества слов;
3. связь размера файла и количества слов;
4. длины heading-секций по уровням и views;
5. распределение длин paragraph blocks;
6. длины paragraphs по heading level;
7. сравнение размеров файлов DLS1/DLS2.

Уровни, которых нет в inventory, не попадают в таблицы и графики. Уровень с
пустыми блоками сохраняется и отображается через `empty-rate`.

Для paragraph blocks в Markdown приводятся count, empty-rate, mean/median,
min/max, p25/p75/p90/p95, standard deviation, tokens, token/word ratio,
characters/bytes, RU/EN counts and ratios, а также counts структурных
признаков: wikilinks, image embeds, code, lists и blockquotes.

Для графиков используются `matplotlib.pyplot` и `seaborn`. Эти зависимости
должны быть установлены в dev environment перед запуском EDA:

```powershell
uv add --dev matplotlib seaborn
```

Команда `uv add` изменяет `pyproject.toml`, `uv.lock` и окружение проекта,
поэтому она запускается пользователем вручную.

## Полный порядок запуска

Сначала создать inventory на реальном read-only vault:

```powershell
uv run pytest tests/manual/test_real_vault_inventory.py -q -s -m manual
```

Затем создать PNG и Markdown EDA:

```powershell
uv run python -m rag_based_on_obsidian.corpus.eda
```

Manual-тест читает `DLS1` и `DLS2`, записывает только проектный artifact
`artifacts/corpus_inventory.json` и сравнивает fingerprints исходных файлов до
и после обработки. Строка `Vault modified: no` означает, что исходные заметки
не были изменены. Во время обработки отображается progress bar по файлам,
если установлен `tqdm`; без него inventory сохраняет работоспособность, но
обрабатывает файлы без индикатора.

## Progress bar

Для стабильного progress bar добавь `tqdm` вручную:

```powershell
uv add tqdm
```

После этого manual inventory test покажет примерно:

```text
Building corpus inventory: 100%|##########| 230/230 [00:01<00:00, 180 file/s]
```

`show_progress=False` используется в unit-тестах, чтобы тестовый вывод был
детерминированным и не содержал динамической строки progress bar.
