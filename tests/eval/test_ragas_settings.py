from pathlib import Path

import pytest

from rag_based_on_obsidian.eval.ragas_settings import load_ragas_config


def test_load_ragas_config_reads_subset_and_concurrency(tmp_path: Path) -> None:
    path = tmp_path / "ragas.yaml"
    path.write_text(
        """name: sprint22
gold_path: evals/gold/phase7_GT_note_level_v0.yaml
dataset_version: phase7_GT_note_level_v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 15
full_set: false
concurrency: 5
judge_model: openai/gpt-4o-mini
generate_timeout_seconds: 60
""",
        encoding="utf-8",
    )
    config = load_ragas_config(path)
    assert config.subset_size == 15
    assert config.full_set is False
    assert config.concurrency == 5
    assert config.method.value == "hybrid"
    assert config.api_base_url == "http://127.0.0.1:8000"
    assert config.human_sample_path is None
    assert config.human_review_path is None


def test_load_ragas_config_rejects_concurrency_above_ten(tmp_path: Path) -> None:
    path = tmp_path / "ragas.yaml"
    path.write_text(
        """name: sprint22
gold_path: gold.yaml
dataset_version: v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 15
full_set: false
concurrency: 11
judge_model: openai/gpt-4o-mini
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="concurrency"):
        load_ragas_config(path)


def test_load_ragas_config_rejects_unpaired_human_paths(tmp_path: Path) -> None:
    path = tmp_path / "ragas.yaml"
    path.write_text(
        """name: sprint22
gold_path: gold.yaml
dataset_version: v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 15
full_set: false
concurrency: 5
judge_model: openai/gpt-4o-mini
human_sample_path: evals/human/sprint22_sample.yaml
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be set together"):
        load_ragas_config(path)
