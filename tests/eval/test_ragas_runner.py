import asyncio
from pathlib import Path

import httpx

from rag_based_on_obsidian.eval.contracts import GoldItem
from rag_based_on_obsidian.eval.ragas_contracts import RagasItemMetrics
from rag_based_on_obsidian.eval.ragas_runner import (
    _macro_average,
    _skip_reason_summary,
    run_ragas_eval,
    select_gold_slice,
)
from rag_based_on_obsidian.eval.ragas_settings import load_ragas_config
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod


def _gold(*ids: str) -> tuple[GoldItem, ...]:
    return tuple(
        GoldItem(
            item_id=item_id,
            question=f"question {item_id}",
            corpus_scope="DLS1+DLS2",
            relevant_note_paths=("DLS1/A.md", "DLS1/B.md"),
            dataset_version="phase7_GT_note_level_v0",
            source_directory="DLS1",
        )
        for item_id in ids
    )


def _write_config(path: Path) -> None:
    path.write_text(
        """name: test
gold_path: gold.yaml
dataset_version: v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 2
full_set: false
concurrency: 5
generate_model: openai/gpt-4o-mini
judge_model: openai/gpt-4o-mini
""",
        encoding="utf-8",
    )


def test_select_gold_slice_takes_yaml_prefix(tmp_path: Path) -> None:
    config_path = tmp_path / "ragas.yaml"
    _write_config(config_path)
    config = load_ragas_config(config_path)
    selected = select_gold_slice(_gold("q001", "q002", "q003"), config)
    assert [item.item_id for item in selected] == ["q001", "q002"]


def test_run_ragas_eval_scores_mocked_generate_and_judge() -> None:
    config = load_ragas_config(Path("configs/eval/ragas.yaml"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/generate"
        return httpx.Response(
            200,
            json={
                "query": "question q001",
                "method": "hybrid",
                "top_k": 5,
                "answer": "Dropout disables neurons.",
                "citations": [{"chunk_id": 1, "note_path": "DLS1/A.md"}],
                "contexts": [
                    {
                        "chunk_id": 1,
                        "note_path": "DLS1/A.md",
                        "text": "Dropout randomly drops units.",
                    },
                    {
                        "chunk_id": 2,
                        "note_path": "DLS1/B.md",
                        "text": "Regularization.",
                    },
                ],
                "confidence": 0.9,
                "refused": False,
                "refusal_reason": None,
                "model": "openai/gpt-4o-mini",
                "latency_ms": 11,
                "usage": {"prompt_tokens": 8, "generated_tokens": 3},
            },
        )

    class _FakeJudge:
        async def score(self, **_kwargs: object) -> tuple[int, int]:
            return 4, 3

    async def _run() -> tuple:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_ragas_eval(
                _gold("q001"),
                config,
                _FakeJudge(),
                client=client,
            )

    summary, artifacts = asyncio.run(_run())
    assert summary.scored_count == 1
    assert summary.skipped_count == 0
    assert summary.faithfulness == 4
    assert summary.answer_relevancy == 3
    assert summary.context_precision == 1.0
    assert summary.context_recall == 1.0
    assert summary.notes_processed == 2
    assert summary.total_prompt_tokens == 8
    assert summary.mean_prompt_tokens == 8.0
    assert summary.median_prompt_tokens == 8.0
    assert summary.total_generated_tokens == 3
    assert summary.mean_generated_tokens == 3.0
    assert summary.median_generated_tokens == 3.0
    assert artifacts[0]["item_id"] == "q001"
    assert artifacts[0]["answer"] == "Dropout disables neurons."
    assert artifacts[0]["contexts"] == [
        {
            "chunk_id": 1,
            "note_path": "DLS1/A.md",
            "text": "Dropout randomly drops units.",
        },
        {
            "chunk_id": 2,
            "note_path": "DLS1/B.md",
            "text": "Regularization.",
        },
    ]
    assert RetrievalMethod.HYBRID is config.method


def test_run_ragas_eval_skips_refused_generate() -> None:
    config = load_ragas_config(Path("configs/eval/ragas.yaml"))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "query": "question q001",
                "method": "hybrid",
                "top_k": 5,
                "answer": None,
                "citations": [],
                "contexts": [],
                "confidence": 0.0,
                "refused": True,
                "refusal_reason": "no retrieved context",
                "model": None,
                "latency_ms": None,
                "usage": None,
            },
        )

    class _BoomJudge:
        async def score(self, **_kwargs: object) -> tuple[float, float]:
            raise AssertionError("judge must not run on refuse")

    async def _run() -> tuple:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_ragas_eval(
                _gold("q001"),
                config,
                _BoomJudge(),
                client=client,
            )

    summary, artifacts = asyncio.run(_run())
    assert summary.scored_count == 0
    assert summary.skipped_count == 1
    assert summary.refused_count == 1
    assert artifacts[0]["skip_reason"] == "no retrieved context"


def test_run_ragas_eval_skips_http_error() -> None:
    config = load_ragas_config(Path("configs/eval/ragas.yaml"))

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "openrouter is unreachable"})

    class _UnusedJudge:
        async def score(self, **_kwargs: object) -> tuple[float, float]:
            raise AssertionError("unused")

    async def _run() -> tuple:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await run_ragas_eval(
                _gold("q001"),
                config,
                _UnusedJudge(),
                client=client,
            )

    summary, _artifacts = asyncio.run(_run())
    assert summary.scored_count == 0
    assert summary.skipped_count == 1


def test_macro_average_counts_unique_notes_and_token_quantiles() -> None:
    summary = _macro_average(
        [
            RagasItemMetrics(
                item_id="q001",
                skipped=False,
                faithfulness=1.0,
                answer_relevancy=1.0,
                context_precision=1.0,
                context_recall=1.0,
                prompt_tokens=10,
                generated_tokens=2,
                packed_note_paths=("DLS1/A.md",),
            ),
            RagasItemMetrics(
                item_id="q002",
                skipped=False,
                faithfulness=1.0,
                answer_relevancy=1.0,
                context_precision=1.0,
                context_recall=1.0,
                prompt_tokens=30,
                generated_tokens=10,
                packed_note_paths=("DLS1/A.md", "DLS1/B.md"),
            ),
            RagasItemMetrics(
                item_id="q003",
                skipped=False,
                faithfulness=1.0,
                answer_relevancy=1.0,
                context_precision=1.0,
                context_recall=1.0,
                prompt_tokens=20,
                generated_tokens=4,
                packed_note_paths=("DLS1/C.md",),
            ),
        ]
    )
    assert summary.notes_processed == 3
    assert summary.total_prompt_tokens == 60
    assert summary.mean_prompt_tokens == 20.0
    assert summary.median_prompt_tokens == 20.0
    assert summary.total_generated_tokens == 16
    assert summary.mean_generated_tokens == 16 / 3
    assert summary.median_generated_tokens == 4.0


def test_skip_reason_summary_counts_top_reasons() -> None:
    summary = _skip_reason_summary(
        [
            RagasItemMetrics(
                item_id="q001",
                skipped=True,
                skip_reason="generate API failed (503): openrouter rejected the API key",
            ),
            RagasItemMetrics(
                item_id="q002",
                skipped=True,
                skip_reason="generate API failed (503): openrouter rejected the API key",
            ),
            RagasItemMetrics(
                item_id="q003",
                skipped=True,
                skip_reason="generate API failed (503): retrieval backend failed",
            ),
            RagasItemMetrics(item_id="q004", skipped=False, faithfulness=4),
        ]
    )
    assert "openrouter rejected the API key×2" in summary
    assert "retrieval backend failed×1" in summary
