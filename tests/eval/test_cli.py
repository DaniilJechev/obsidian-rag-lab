import json
from pathlib import Path

from rag_based_on_obsidian.eval import cli


def test_eval_score_prints_synthetic_harness_metrics(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gold = tmp_path / "gold.yaml"
    gold.write_text(
        """dataset_version: phase7-note-level-v0-draft
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
    rankings = tmp_path / "rankings.json"
    rankings.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "q001",
                        "ranked_paths": ["DLS1/Dropout.md", "DLS2/other.md"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    logged: dict[str, object] = {}

    def fake_log(**kwargs: object) -> str:
        logged.update(kwargs)
        return "eval-run"

    monkeypatch.setattr(cli, "log_eval_harness_run", fake_log)

    exit_code = cli.main(
        [
            "score",
            "--gold",
            str(gold),
            "--rankings",
            str(rankings),
            "--log-mlflow",
        ]
    )

    assert exit_code == 0
    assert logged["run_kind"] == "synthetic_harness"
    assert logged["dataset_version"] == "phase7-note-level-v0-draft"
