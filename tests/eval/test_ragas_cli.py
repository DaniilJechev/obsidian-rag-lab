import json
from pathlib import Path

import yaml

from rag_based_on_obsidian.eval.ragas import ragas_cli
from rag_based_on_obsidian.eval.ragas.ragas_contracts import RagasDatasetMetrics


def test_ragas_cli_run_prints_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    gold = tmp_path / "gold.yaml"
    gold.write_text(
        """dataset_version: phase7_GT_note_level_v0
corpus_scope: DLS1+DLS2
items:
  - id: q001
    question: What is dropout?
    source_directory: DLS1
    relevant_notes:
      - DLS1/Dropout.md
""",
        encoding="utf-8",
    )
    config = tmp_path / "ragas.yaml"
    config.write_text(
        f"""name: test-run
gold_path: "{gold.as_posix()}"
dataset_version: phase7_GT_note_level_v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 1
full_set: false
concurrency: 5
generate_model: openai/gpt-4o-mini
judge_model: openai/gpt-4o-mini
""",
        encoding="utf-8",
    )
    llm = tmp_path / "llm.yaml"
    llm.write_text(
        """name: test
model: openai/gpt-4o-mini
base_url: https://openrouter.ai/api/v1
""",
        encoding="utf-8",
    )

    async def fake_run(*_args: object, **_kwargs: object) -> tuple:
        metrics = RagasDatasetMetrics(
            question_count=1,
            scored_count=1,
            skipped_count=0,
            refused_count=0,
            faithfulness=4.0,
            answer_relevancy=3.0,
            context_precision=1.0,
            context_recall=1.0,
            mean_latency_ms=10.0,
            total_prompt_tokens=4,
            total_generated_tokens=2,
        )
        return metrics, [{"item_id": "q001"}]

    monkeypatch.setattr(ragas_cli, "build_generation_judge", lambda *_a, **_k: object())
    monkeypatch.setattr(ragas_cli, "run_ragas_eval", fake_run)
    logged: dict[str, object] = {}

    def fake_log(**kwargs: object) -> str:
        logged.update(kwargs)
        return "ragas-mlflow"

    monkeypatch.setattr(ragas_cli, "log_ragas_run", fake_log)

    exit_code = ragas_cli.main(
        [
            "run",
            "--config",
            str(config),
            "--llm-config",
            str(llm),
            "--generate-model",
            "google/gemini-3.7-flash",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    stdout = json.loads(captured.out.splitlines()[-1])
    assert stdout["mlflow_run_id"] == "ragas-mlflow"
    assert stdout["generate_model"] == "google/gemini-3.7-flash"
    assert stdout["faithfulness"] == 4.0
    assert stdout["judge_backend"] == "json"
    assert stdout["judge_scale"] == "0-5"
    assert logged["extra_params"]["generate_model"] == "google/gemini-3.7-flash"
    assert logged["extra_tags"]["generate_model"] == "google/gemini-3.7-flash"
    assert (
        logged["run_name"]
        == "ragas-framework-sprint23-generate-google-gemini-3.7-flash"
    )
    assert logged["prompts"]["generate_system"]
    assert "answer" in logged["prompts"]["generate_system"]
    assert logged["prompts"]["evaluation_system"]
    assert "faithfulness" in logged["prompts"]["evaluation_system"]


def test_ragas_cli_writes_human_review_pack(tmp_path: Path, monkeypatch, capsys) -> None:
    gold = tmp_path / "gold.yaml"
    gold.write_text(
        """dataset_version: phase7_GT_note_level_v0
corpus_scope: DLS1+DLS2
items:
  - id: q001
    question: What is dropout?
    source_directory: DLS1
    relevant_notes:
      - DLS1/Dropout.md
""",
        encoding="utf-8",
    )
    sample = tmp_path / "sample.yaml"
    sample.write_text(
        """dataset_version: phase7_GT_note_level_v0
items:
  - id: q001
    faithfulness: null
""",
        encoding="utf-8",
    )
    review = tmp_path / "review.yaml"
    config = tmp_path / "ragas.yaml"
    config.write_text(
        f"""name: test-run
gold_path: "{gold.as_posix()}"
dataset_version: phase7_GT_note_level_v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 1
full_set: false
concurrency: 5
generate_model: openai/gpt-4o-mini
judge_model: openai/gpt-4o-mini
judge_backend: ragas
human_sample_path: "{sample.as_posix()}"
human_review_path: "{review.as_posix()}"
""",
        encoding="utf-8",
    )
    llm = tmp_path / "llm.yaml"
    llm.write_text(
        """name: test
model: openai/gpt-4o-mini
base_url: https://openrouter.ai/api/v1
""",
        encoding="utf-8",
    )

    async def fake_run(*_args: object, **_kwargs: object) -> tuple:
        metrics = RagasDatasetMetrics(
            question_count=1,
            scored_count=1,
            skipped_count=0,
            refused_count=0,
            faithfulness=4.0,
            answer_relevancy=3.0,
            context_precision=1.0,
            context_recall=1.0,
            mean_latency_ms=10.0,
            total_prompt_tokens=4,
            total_generated_tokens=2,
        )
        return metrics, [
            {
                "item_id": "q001",
                "question": "What is dropout?",
                "answer": "Dropout randomly drops units.",
                "refused": False,
                "skip_reason": None,
                "contexts": [
                    {
                        "chunk_id": 1,
                        "note_path": "DLS1/Dropout.md",
                        "text": "Dropout breaks co-adaptation.",
                    }
                ],
                "faithfulness": 4,
                "answer_relevancy": 3,
            }
        ]

    monkeypatch.setattr(ragas_cli, "build_generation_judge", lambda *_a, **_k: object())
    monkeypatch.setattr(ragas_cli, "run_ragas_eval", fake_run)
    monkeypatch.setattr(ragas_cli, "log_ragas_run", lambda **_kwargs: "ragas-mlflow")

    exit_code = ragas_cli.main(
        [
            "run",
            "--config",
            str(config),
            "--llm-config",
            str(llm),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert review.exists()
    payload = yaml.safe_load(review.read_text(encoding="utf-8"))
    assert payload["items"][0]["answer"] == "Dropout randomly drops units."
    assert payload["items"][0]["contexts"][0]["text"] == "Dropout breaks co-adaptation."
    stdout = json.loads(captured.out.splitlines()[-1])
    assert stdout["human_review_path"] == str(review)
    assert stdout["human_review_count"] == 1
    assert stdout["generate_model"] == "openai/gpt-4o-mini"
    assert stdout["judge_backend"] == "ragas"
    assert stdout["judge_scale"] == "0-1"
