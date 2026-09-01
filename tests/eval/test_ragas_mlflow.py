import json

from rag_based_on_obsidian.eval.ragas import ragas_mlflow
from rag_based_on_obsidian.eval.ragas.ragas_contracts import RagasDatasetMetrics


class _FakeRun:
    def __init__(self) -> None:
        self.info = type("Info", (), {"run_id": "ragas-run"})()

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_log_ragas_run_writes_phase_10_tags(monkeypatch) -> None:
    logged: dict[str, object] = {}
    monkeypatch.setattr(ragas_mlflow, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(
        ragas_mlflow.os,
        "environ",
        {"MLFLOW_TRACKING_URI": "http://127.0.0.1:5000"},
    )
    monkeypatch.setattr(
        ragas_mlflow.mlflow,
        "set_tracking_uri",
        lambda uri: logged.setdefault("uri", uri),
    )
    monkeypatch.setattr(ragas_mlflow, "_configure_ragas_experiment", lambda: None)
    def fake_start_run(**kwargs: object) -> _FakeRun:
        logged["start_run_kwargs"] = kwargs
        return _FakeRun()

    monkeypatch.setattr(ragas_mlflow.mlflow, "start_run", fake_start_run)
    monkeypatch.setattr(
        ragas_mlflow.mlflow,
        "log_params",
        lambda params: logged.setdefault("params", params),
    )
    monkeypatch.setattr(
        ragas_mlflow.mlflow,
        "set_tags",
        lambda tags: logged.setdefault("tags", tags),
    )
    monkeypatch.setattr(
        ragas_mlflow.mlflow,
        "log_metrics",
        lambda metrics, step=None: (
            logged.setdefault("metrics", metrics)
            if step is None
            else logged.setdefault("steps", []).append((step, dict(metrics)))
        ),
    )
    monkeypatch.setattr(
        ragas_mlflow.mlflow,
        "log_text",
        lambda text, path: logged.setdefault("texts", []).append((path, text)),
    )
    monkeypatch.setattr(ragas_mlflow, "process_rss_mb", lambda: 64.0)

    metrics = RagasDatasetMetrics(
        question_count=15,
        scored_count=14,
        skipped_count=1,
        refused_count=1,
        faithfulness=3.5,
        answer_relevancy=4.0,
        context_precision=0.5,
        context_recall=0.8,
        mean_latency_ms=1200.0,
        notes_processed=7,
        total_prompt_tokens=100,
        mean_prompt_tokens=10.0,
        median_prompt_tokens=9.0,
        total_generated_tokens=20,
        mean_generated_tokens=2.0,
        median_generated_tokens=2.0,
    )
    run_id = ragas_mlflow.log_ragas_run(
        dataset_version="phase7_GT_note_level_v0",
        metrics=metrics,
        duration_seconds=12.0,
        extra_params={"top_k": 5},
        prompts={
            "generate_system": "GEN_PROMPT",
            "evaluation_system": "EVAL_PROMPT",
        },
        artifact={
            "items": [
                {
                    "item_id": "q001",
                    "question": "ok?",
                    "skipped": False,
                    "faithfulness": 3,
                    "answer_relevancy": 5,
                    "context_precision": 0.5,
                    "context_recall": 1.0,
                },
                {
                    "item_id": "q002",
                    "question": "ok2?",
                    "skipped": False,
                    "faithfulness": 5,
                    "answer_relevancy": 3,
                    "context_precision": 0.5,
                    "context_recall": 0.6,
                },
                {
                    "item_id": "q003",
                    "question": "плохой json?",
                    "skipped": True,
                    "skip_reason": (
                        "generate API failed (503): structured output is not "
                        "valid JSON"
                    ),
                    "raw_generation": '{"answer":"x \\approx 0", "citations":[',
                    "answer": None,
                    "model": None,
                },
            ]
        },
        run_name="ragas-framework-sprint23-generate-openai-gpt-4o-mini",
    )

    assert run_id == "ragas-run"
    assert (
        logged["start_run_kwargs"]["run_name"]
        == "ragas-framework-sprint23-generate-openai-gpt-4o-mini"
    )
    assert logged["tags"]["phase"] == "10"
    assert logged["tags"]["sprint"] == "23"
    assert logged["tags"]["task"] == "MLOPS-002"
    assert logged["metrics"]["faithfulness"] == 3.5
    assert logged["metrics"]["answer_relevancy"] == 4.0
    assert logged["metrics"]["judge_faithfulness"] == 3.5
    assert logged["metrics"]["judge_answer_relevancy"] == 4.0
    assert logged["metrics"]["proxy_context_precision"] == 0.5
    assert logged["metrics"]["proxy_context_recall"] == 0.8
    assert logged["metrics"]["context_recall"] == 0.8
    assert logged["metrics"]["stdev_faithfulness"] == 1.0
    assert logged["metrics"]["stdev_answer_relevancy"] == 1.0
    assert logged["steps"][0][0] == 0
    assert logged["steps"][0][1]["item_answer_relevancy"] == 5.0
    assert logged["metrics"]["notes_processed"] == 7.0
    assert logged["metrics"]["mean_prompt_tokens"] == 10.0
    assert logged["metrics"]["median_prompt_tokens"] == 9.0
    assert logged["metrics"]["mean_generated_tokens"] == 2.0
    assert logged["metrics"]["median_generated_tokens"] == 2.0
    assert logged["params"]["run_kind"] == "ragas_live"
    assert logged["params"]["notes_processed"] == "7"
    assert "prompt_generate_system_sha256" in logged["params"]
    assert "prompt_evaluation_system_sha256" in logged["params"]
    assert ("prompts/generate_system.txt", "GEN_PROMPT") in logged["texts"]
    assert ("prompts/evaluation_system.txt", "EVAL_PROMPT") in logged["texts"]
    text_by_path = {path: text for path, text in logged["texts"]}
    assert "per_question.json" in text_by_path
    assert "failed_generations.json" in text_by_path
    assert "\\u04" not in text_by_path["failed_generations.json"]
    assert "плохой" in text_by_path["failed_generations.json"]
    failed_payload = json.loads(text_by_path["failed_generations.json"])
    assert failed_payload["items"][0]["item_id"] == "q003"
    assert "valid JSON" in failed_payload["items"][0]["skip_reason"]
    assert "\\approx" in failed_payload["items"][0]["raw_generation"]


def test_mlflow_generate_run_name_sanitizes_model_id() -> None:
    assert (
        ragas_mlflow.mlflow_generate_run_name("openai/gpt-4o-mini")
        == "ragas-framework-sprint23-generate-openai-gpt-4o-mini"
    )
    assert (
        ragas_mlflow.mlflow_generate_run_name("google/gemini-3.7-flash")
        == "ragas-framework-sprint23-generate-google-gemini-3.7-flash"
    )