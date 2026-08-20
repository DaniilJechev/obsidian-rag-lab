# Phase 7 — Retrieval metrics (note-level)

Статус: `planned`. Этот документ фиксирует **что** меряем в живой Phase 7
и **как** это считается. Числа появляются только после реального eval-запуска
и пишутся в MLflow, не сюда заранее.

Generation-метрики RAGAS (Faithfulness, Answer Relevancy, Context
Precision/Recall) — **живая Phase 10**, сразу после OpenRouter generate.
Phase 7 оценивает только retrieval.

## Зачем отдельный gold eval

Hybrid search на `main` уже возвращает top-k chunks. Это доказывает, что
pipeline **технически** работает. Это **не** доказывает, что он находит
правильные заметки по учебным вопросам.

Без gold set любые следующие фазы (rerank, cache, другой chunk size,
другая embedding-модель) сравниваются «на глаз». nDCG/MRR дают одну шкалу
«до/после» на фиксированном наборе вопросов.

## Гранулярность: note-level, не chunk-level

Gold помечает **заметки**, не чанки.

Почему так на v1:

- атомарные заметки vault уже roughly одного факта; чанк внутри заметки
  часто тоже релевантен, если релевантна заметка;
- человеку проще проверить «эта заметка отвечает на вопрос», чем
  размечать offset/chunk_index;
- chunking_version ещё может смениться; note identity (`relative_path` /
  `note_id`) стабильнее.

Как из chunk-ранжирования получить note-ранжирование:

1. Retrieval как сейчас возвращает упорядоченный список chunks.
2. Для каждой chunk берём `note_id` / `source_path`.
3. Первое появление заметки в этом списке становится её рангом.
   Повторные чанки той же заметки **не** получают второй ранг.
4. Метрики считаются по этому списку уникальных notes.

`relevant_chunk_ids` в `eval_items` оставляем пустым `[]` в Phase 7.
Колонку не удаляем: chunk-level можно добавить позже отдельным
`dataset_version`, не ломая schema.

Бинарная релевантность: заметка либо в gold, либо нет. Не ставим graded
0/1/2 на v1 — это ускоряет разметку и упрощает nDCG (ideal DCG тогда
считается по `|gold ∩ top-k|` позициям с gain 1).

Нельзя помечать «весь top-20 = relevant». Gold пишет ассистент, владелец
проверяет и может вычеркнуть/добавить notes.

## Какие метрики считаем

Рекомендуемый набор для каждого вопроса и затем macro-average по набору:

| Метрика | k | Роль |
|---|---|---|
| **nDCG@k** | 5 и 10 | Главная ranking-метрика: штрафует, если нужная заметка низко |
| **MRR@k** | 10 | Насколько высоко **первая** релевантная заметка |
| **Recall@k** | 5 и 10 | Доля gold-заметок, попавших в top-k notes |
| **Hit@k** | 10 | 1, если хотя бы одна gold-заметка в top-k; иначе 0 |

k=5 — «то, что почти наверняка уйдёт в контекст LLM».
k=10 — чуть шире, чтобы видеть, что система «почти нашла», но не влезла
в короткий контекст.

### nDCG@k — Normalized Discounted Cumulative Gain

Интуиция: чем выше в выдаче стоит релевантный документ, тем лучше.
Нижние позиции дешевеют логарифмическим дисконтом.

Для бинарной релевантности \(rel_i \in \{0,1\}\):

\[
DCG@k = \sum_{i=1}^{k} \frac{rel_i}{\log_2(i+1)}
\]

- \(i\) — 1-based ранг заметки после collapse chunks→notes.
- \(rel_i = 1\), если эта заметка есть в gold этого вопроса.
- \(\log_2(i+1)\) — дисконт: 1-е место не штрафуется (\(log_2 2 = 1\)),
  2-е уже слабее, 10-е ещё слабее.

Ideal DCG (IDCG) — тот же сумматор, но по идеальному ранжированию:
все релевантные заметки стоят наверху. Для бинарных меток это просто
DCG по \(\min(|gold|, k)\) единицам на позициях \(1..m\).

\[
nDCG@k = \frac{DCG@k}{IDCG@k}
\]

Диапазон \([0, 1]\). Если gold пустой — вопрос невалиден, в среднее не
идёт. Если IDCG=0 по той же причине — не делим на ноль, отбрасываем item.

Зачем нужна, а не только Recall: Recall@10 = 1, если обе нужные заметки
где-то в десятке, даже если они на местах 9 и 10. nDCG это накажет.

Реализацию пишем сами (NumPy), не тащим sklearn как единственный источник
истины: так проще объяснить формулу в тестах с фиктивным ranking.

### MRR@k — Mean Reciprocal Rank

Для одного вопроса:

\[
RR = \begin{cases}
1 / r_{\min}, & \text{если первая релевантная заметка на ранге } r_{\min} \le k \\
0, & \text{иначе}
\end{cases}
\]

MRR — среднее RR по вопросам.

Зачем: типичный RAG-вопрос часто имеет **одну** «главную» атомарную
заметку. MRR отвечает: «как быстро мы нашли хоть что-то полезное?».
Он глухой к второй и третьей релевантной заметке — поэтому рядом всегда
стоит nDCG и Recall.

### Recall@k и Hit@k

\[
Recall@k = \frac{|gold \cap predicted_k|}{|gold|}
\]

Hit@k = 1, если пересечение непусто.

Зачем: диагностика. Если nDCG низкий, а Recall@10 высокий — проблема
ранжирования, не покрытия. Если Recall@10 тоже низкий — система не
достаёт нужные notes даже широким top-k (embedding, lexical, или gold
слишком жёсткий).

Precision@k на v1 **не** делаем главным числом: у вопроса часто 1–3
релевантные заметки, а k=10, поэтому Precision искусственно прижат.
Его можно логировать как вспомогательный, но baseline сравниваем по
nDCG/MRR/Recall.

## Что не мерим в Phase 7

- RAGAS / Faithfulness / Answer Relevancy — нет generate, это Phase 10.
- Latency, tokens, cost — можно логировать operational рядом, но это не
  quality-метрика retrieval.
- LLM-as-judge вместо человека — запрещён как единственный gold.

## Протокол запуска и MLflow

Каждый eval-прогон (dense, bm25, hybrid, позже rerank) — **отдельный**
MLflow run в одном experiment, например `phase-7-retrieval-eval`.

Experiment-level tags: `phase=7`, `sprint`, `task`, `experiment_type=eval`.
Experiment description в `mlflow.note.content`.

Run-level обязательно:

- `dataset_version`, `label_granularity=note`;
- retrieval method (`dense` / `bm25` / `hybrid`);
- `chunking_version`, embedding model/revision, collection name;
- `top_k`, `candidate_k`, `rrf_k` если hybrid;
- device, batch size, normalization — как в остальных inference runs;
- metrics: nDCG@5/10, MRR@10, Recall@5/10, Hit@10;
- operational: duration, QPS, RAM, если доступны;
- artifact: per-question JSON/CSV (ranks, predicted notes, hits/misses).

Без MLflow run результат не считается воспроизводимым baseline.

## Хранение gold: `eval_items`

Один вопрос — одна строка. Контракт уже описан в
`docs/architecture/phase-2-database-schema.md`; таблицы в Alembic ещё нет,
это работа Sprint 17.

- `question` — текст;
- `corpus_scope` — `DLS1+DLS2`;
- `relevant_note_ids` — JSONB массив `note_id` после resolve
  `relative_path → notes.note_id`;
- `relevant_chunk_ids` — `[]` на v1;
- `dataset_version` — например `phase7-note-level-v1` после review.

YAML в `evals/gold/` — authoring format и git-источник. Postgres —
runtime source of truth для eval runner. Не держим два расходящихся
канона: loader идемпотентно upsert-ит по `(dataset_version, question)`
или стабильному `eval_item_id` из YAML.

## Корпус

Allowlist: `obsidianNotes/ML_NLP/DLS1/` и `obsidianNotes/ML_NLP/DLS2/`.
Каталог `obsidianNotes/ML_NLP/NLP/` в gold и discovery **не** входит.

Discovery по-прежнему ждёт прямых детей vault root с именами `DLS1` и
`DLS2`. Значит `OBSIDIAN_VAULT_ROOT` должен указывать на
`obsidianNotes/ML_NLP`, а не на корень vault. Тогда `relative_path`
остаётся `DLS1/...` и `DLS2/...`, как в текущей схеме `notes`.
