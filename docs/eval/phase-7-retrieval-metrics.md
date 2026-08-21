# Phase 7 — Retrieval metrics (note-level)

Статус: `completed` (Sprint 17 gold + Sprint 18 live baseline). Каноническая
таблица — `docs/agile/sprint-18-retrieval-eval-baseline.md`. Следующая живая
фаза retrieval quality — rerank (Phase 12 / `ML-001`); generate/RAGAS —
Phase 9–10. FastAPI — Phase 8.

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

Рекомендуемый набор для каждого вопроса и затем macro-average по набору.
Все метрики **бинарные** и считаются после collapse chunks→notes. LLM-as-judge
не используется.

| Метрика | k | Роль |
|---|---|---|
| **nDCG@k** | `--top-k` | Главная ranking-метрика: штрафует, если нужная заметка низко |
| **MRR@k** | `--top-k` | Насколько высоко **первая** релевантная заметка |
| **Precision@k** | `--top-k` | Доля top-k, которая попала в gold (вспомогательная: gold короткий) |
| **Recall@k** | `--top-k` | Доля gold-заметок, попавших в top-k notes |
| **F1@k** | `--top-k` | Гармоническое среднее Precision и Recall |
| **Hit@k** | `--top-k` | 1, если хотя бы одна gold-заметка в top-k; иначе 0 |
| **MAP@k** | `--top-k` | Mean Average Precision (TREC: AP / \|gold\|) |
| **R-Precision** | \|gold\| | Precision на ранге, равном числу релевантных заметок |

Cutoff **не зашит** в код: один `k` приходит из CLI (`--top-k`) и идёт и в
retrieval, и в метрики. Сравнивать dense / bm25 / hybrid можно только на
одинаковом k. Типичные выборы: 5 («почти наверняка уйдёт в контекст LLM»)
или 10 (чуть шире, видно «почти нашли»). Это решение запуска, не константа
пакета.

Главные числа для сравнения методов на выбранном k: **nDCG, MAP, MRR, Recall**.
Precision@k на коротком gold (2–3 заметки при большом k) искусственно прижат —
его логируем, но не объявляем «победителем» по нему одному.

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

Реализацию пишем сами, не sklearn как единственный источник истины:
так проще объяснить формулу в тестах с фиктивным ranking.

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

Precision@k на коротком gold (2–3 релевантные заметки при k=10)
искусственно мал. Его считаем и логируем как вспомогательный, baseline
сравниваем в первую очередь по nDCG/MAP/MRR/Recall.

### Precision@k, F1@k, MAP@k, R-Precision

\[
Precision@k = \frac{|gold \cap predicted_k|}{k}
\]

\[
F1@k = \frac{2 \cdot P@k \cdot R@k}{P@k + R@k}
\]

(если \(P+R=0\), F1 = 0).

Average Precision@k (TREC): на каждой позиции, где в top-k стоит
релевантная заметка, берём Precision@этой_позиции и усредняем по
**всем** gold-заметкам вопроса, даже если часть не вошла в k:

\[
AP@k = \frac{1}{|gold|} \sum_{i \le k,\, d_i \in gold} Precision@i
\]

MAP@k — среднее AP@k по вопросам.

R-Precision = Precision@\(R\), где \(R = |gold|\). Для наших вопросов
это Precision@2 или @3: насколько плотно релевантные заметки стоят в
самом верху, без раздувания знаменателя до 10.

Реализацию пишем сами, не sklearn: так проще объяснить формулу в тестах
с фиктивным ranking.

## Что не мерим в Phase 7

- RAGAS / Faithfulness / Answer Relevancy — нет generate, это Phase 10.
- Latency, tokens, cost — можно логировать operational рядом, но это не
  quality-метрика retrieval.
- LLM-as-judge вместо человека — запрещён как единственный gold.

## Протокол запуска и MLflow

Каждый eval-прогон (dense, bm25, hybrid, позже rerank) — **отдельный**
MLflow run в одном experiment `phase-7-retrieval-eval`.

Команда Sprint 18 (записанный baseline — `--top-k 5`):

```text
uv run rag-cli eval load-gold
uv run rag-cli eval run --method dense --top-k 5
uv run rag-cli eval run --method bm25 --top-k 5
uv run rag-cli eval run --method hybrid --top-k 5
```

`--top-k` обязателен: это и размер выдачи retriever, и cutoff метрик.
По умолчанию hybrid ищет `candidate_k = 2 * --top-k` (при `--top-k 5` → 10).
`--candidate-k` — ручной override. `rrf_k` всегда из
`configs/retrieval/retrieval.yaml` (сейчас 60), пока не передали `--rrf-k`.
В MLflow `rrf_k` пишется и как param, и как metric. BM25 не грузит e5;
dense/hybrid грузят модель **один раз** на прогон. Postgres `eval_items` —
runtime source of truth; YAML нужен, чтобы приклеить стабильные `q00N` id
к artifact.

Experiment-level tags: `phase=7`, `sprint`, `task`, `experiment_type=eval`.
Experiment description в `mlflow.note.content`.

Run-level обязательно:

- `dataset_version`, `label_granularity=note`;
- retrieval method (`dense` / `bm25` / `hybrid`);
- `chunking_version`, embedding model/revision, collection name;
- `top_k`; `candidate_k` (дефолт `2 * top_k`); `rrf_k` из retrieval YAML
  (param + metric);
- device, batch size, normalization — как в остальных inference runs;
- metrics: `ndcg_at_k`, `mrr_at_k`, `precision_at_k`, `recall_at_k`,
  `f1_at_k`, `hit_at_k`, `map_at_k` (Mean Average Precision; в коде поле
  `average_precision`; `@` в имени нельзя — MLflow его отвергает),
  `r_precision` (cutoff = \|gold\|, не `--top-k`);
- operational: duration, QPS, RAM, если доступны;
- artifact: per-question JSON/CSV (ranks, predicted notes, hits/misses).

Без MLflow run результат не считается воспроизводимым baseline.

## Хранение gold: `eval_items`

Один вопрос — одна строка. Контракт в
`docs/architecture/phase-2-database-schema.md`; таблица создана в Sprint 17
(Alembic `b7e4a91c2d80`).

- `question` — текст;
- `corpus_scope` — `DLS1+DLS2`;
- `relevant_note_ids` — JSONB массив `note_id` после resolve
  `relative_path → notes.note_id`;
- `relevant_chunk_ids` — `[]` на v1;
- `dataset_version` — сейчас `phase7_GT_note_level_v0`
  (`evals/gold/phase7_GT_note_level_v0.yaml`, `configs/eval/eval.yaml`).

YAML в `evals/gold/` — authoring format и git-источник. Postgres —
runtime source of truth для eval runner. `load-gold` сначала удаляет все
строки `eval_items`, затем пишет текущий YAML, чтобы в таблице не копить
старые `dataset_version`.

## Корпус

Allowlist: `obsidianNotes/ML_NLP/DLS1/` и `obsidianNotes/ML_NLP/DLS2/`.
Каталог `obsidianNotes/ML_NLP/NLP/` в gold и discovery **не** входит.

Discovery по-прежнему ждёт прямых детей vault root с именами `DLS1` и
`DLS2`. Значит `OBSIDIAN_VAULT_ROOT` должен указывать на
`obsidianNotes/ML_NLP`, а не на корень vault. Тогда `relative_path`
остаётся `DLS1/...` и `DLS2/...`, как в текущей схеме `notes`.

## Observed Sprint 18 baseline (k=5)

Источник: MLflow Compare владельца, experiment `phase-7-retrieval-eval`,
50 вопросов, `skipped=0`, `top_k=5`, `rrf_k=60`. Порядок колонок:
hybrid / dense / bm25. Полная таблица и оговорки —
`docs/agile/sprint-18-retrieval-eval-baseline.md`.

| Metric @5 | hybrid | dense | bm25 |
|---|---:|---:|---:|
| nDCG | 0.616 | 0.619 | 0.536 |
| MRR | 0.797 | 0.817 | 0.726 |
| MAP | 0.513 | 0.512 | 0.412 |
| Recall | 0.613 | 0.607 | 0.560 |
| Hit | 0.92 | 0.96 | 0.96 |
| duration_s | 10.76 | 11.37 | 1.35 |

Hybrid на этом срезе **не** лучше dense по nDCG/MRR. Hit@5 высокий у всех
трёх (узкий корпус). Следующие фазы сравнивают с этой таблицей только при
том же gold `phase7_GT_note_level_v0` и том же k.
