from __future__ import annotations

from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import rag_based_on_obsidian.chunking.experiments.mlflow_tracking as tracking_module
from rag_based_on_obsidian.chunking.experiments import (
    ExperimentConfig,
    load_experiment_config,
    run_experiment,
    write_experiment_artifacts,
)
from rag_based_on_obsidian.chunking.policy import ChunkingPolicy
from rag_based_on_obsidian.chunking.section_tree import SectionTree, build_section_tree
from rag_based_on_obsidian.corpus.discovery_entities import DiscoveredFile
from rag_based_on_obsidian.corpus.markdown_parser import parse_markdown_file


def _fixture_source(tmp_path: Path) -> tuple[SectionTree, str]:
    source = "# Heading\n\none two three four five six seven eight nine ten\n"
    path = tmp_path / "note.md"
    path.write_text(source, encoding="utf-8")
    parsed = parse_markdown_file(
        DiscoveredFile(
            absolute_path=path,
            relative_path=PurePosixPath("DLS1/note.md"),
        )
    )
    tree = build_section_tree(
        parsed,
        note_id=7,
        source_content_hash="source-hash",
        parser_version="parser-v1",
    )
    return tree, source


def _config(tmp_path: Path) -> ExperimentConfig:
    path = tmp_path / "policy.yaml"
    path.write_text(
        """name: test-policy
chunking_version: sprint9-test-v1
chunk_size: 5
chunk_overlap: 0
separators: [" "]
include_heading_context: true
preserve_code_blocks: true
preserve_list_blocks: true
preserve_table_blocks: true
""",
        encoding="utf-8",
    )
    return load_experiment_config(path)


def test_load_experiment_config_preserves_version_and_hash(tmp_path: Path) -> None:
    config = _config(tmp_path)

    assert config.chunking_version == "sprint9-test-v1"
    assert len(config.config_sha256) == 64


def test_run_experiment_is_deterministic_and_collects_contract_metrics(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    tree, source = _fixture_source(tmp_path)

    first = run_experiment(config, ((tree, source),))
    second = run_experiment(config, ((tree, source),))

    assert first.chunks == second.chunks
    assert first.metrics["chunks_total"] > 1
    assert first.metrics["short_chunk_threshold_tokens"] == 1
    assert first.metrics["mean_token_length"] > 0
    assert "short_chunk_rate_below_25pct" in first.metrics
    assert first.metrics["boundary_violation_count"] == 0
    assert first.metrics["metadata_completeness"] == 1.0
    assert first.metrics["storage_bytes"] > 0


def test_write_experiment_artifacts_creates_reviewable_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    tree, source = _fixture_source(tmp_path)
    result = run_experiment(config, ((tree, source),))
    artifact_dir = write_experiment_artifacts(result, tmp_path / "artifacts")

    assert artifact_dir == tmp_path / "artifacts" / "test-policy"
    for filename in (
        "policy.yaml",
        "summary.json",
        "metrics.csv",
        "report.md",
    ):
        assert (artifact_dir / filename).is_file()


def test_log_experiment_to_mlflow_logs_run_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, object]] = []

    class FakeRun:
        info = SimpleNamespace(run_id="run-123")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    fake_mlflow = SimpleNamespace(
        set_tracking_uri=lambda uri: calls.append(("tracking_uri", uri)),
        set_experiment=lambda name: calls.append(("experiment", name)),
        start_run=lambda run_name: (
            calls.append(("run", run_name)) or FakeRun()
        ),
        log_params=lambda params: calls.append(("params", params)),
        set_tags=lambda tags: calls.append(("tags", tags)),
        log_metrics=lambda metrics: calls.append(("metrics", metrics)),
        log_artifacts=lambda path: calls.append(("artifacts", path)),
    )
    monkeypatch.setattr(tracking_module, "mlflow", fake_mlflow)

    policy = ChunkingPolicy(
        name="test",
        chunking_version="test-v1",
        chunk_size=100,
        chunk_overlap=0,
        separators=("\n\n", "\n", " "),
    )
    config = ExperimentConfig(
        policy=policy,
        config_path=tmp_path / "policy.yaml",
        config_sha256="hash",
    )
    tree, source = _fixture_source(tmp_path)
    result = run_experiment(config, ((tree, source),))

    run_id = tracking_module.log_experiment_to_mlflow(
        result,
        tmp_path / "artifacts",
    )

    assert run_id == "run-123"
    assert any(name == "tracking_uri" for name, _ in calls)
    assert ("experiment", "sprint-9-chunking-experiments") in calls
    assert any(name == "params" for name, _ in calls)
    assert any(name == "metrics" for name, _ in calls)
    assert any(name == "artifacts" for name, _ in calls)
