from __future__ import annotations

from pathlib import Path

import rag_based_on_obsidian.chunking.experiments.runner as runner_module
from rag_based_on_obsidian.chunking.experiments import (
    build_corpus_inputs,
    run_policy_matrix,
)


def _write_policy(path: Path, name: str, size: int) -> None:
    path.write_text(
        f"""name: {name}
chunking_version: {name}-v1
chunk_size: {size}
chunk_overlap: 0
separators: ["\\n\\n", "\\n", " "]
include_heading_context: true
preserve_code_blocks: true
preserve_list_blocks: true
preserve_table_blocks: true
""",
        encoding="utf-8",
    )


def test_build_corpus_inputs_is_allowlisted_and_deterministic(tmp_path: Path) -> None:
    (tmp_path / "DLS1").mkdir()
    (tmp_path / "DLS2").mkdir()
    (tmp_path / "Private").mkdir()
    (tmp_path / "DLS1" / "b.md").write_text("# B\n\nbody", encoding="utf-8")
    (tmp_path / "DLS1" / "a.md").write_text("# A\n\nbody", encoding="utf-8")
    (tmp_path / "DLS2" / "c.md").write_text("# C\n\nbody", encoding="utf-8")
    (tmp_path / "Private" / "secret.md").write_text("secret", encoding="utf-8")

    inputs = build_corpus_inputs(tmp_path, ("DLS1", "DLS2"))

    assert [item.relative_path for item in inputs] == [
        "DLS1/a.md",
        "DLS1/b.md",
        "DLS2/c.md",
    ]
    assert [item.note_id for item in inputs] == [0, 1, 2]


def test_run_policy_matrix_executes_candidates_in_sorted_order(
    monkeypatch,
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    (vault / "DLS1").mkdir(parents=True)
    source = "# Heading\n\none two three four five six"
    (vault / "DLS1" / "note.md").write_text(source, encoding="utf-8")
    tree_sources = runner_module.corpus_inputs_to_tree_sources(
        build_corpus_inputs(vault, ("DLS1",))
    )
    policy_512 = tmp_path / "policy_512.yaml"
    policy_256 = tmp_path / "policy_256.yaml"
    _write_policy(policy_512, "policy-512", 512)
    _write_policy(policy_256, "policy-256", 256)
    calls: list[str] = []

    monkeypatch.setattr(
        runner_module,
        "log_experiment_to_mlflow",
        lambda result, artifact_dir, **kwargs: (
            calls.append(result.config.policy.name) or f"run-{len(calls)}"
        ),
    )

    results = run_policy_matrix(
        (policy_512, policy_256),
        tree_sources,
        artifact_root=tmp_path / "artifacts",
    )

    assert [item.config.policy.name for item in results] == [
        "policy-256",
        "policy-512",
    ]
    assert calls == ["policy-256", "policy-512"]
    assert (tmp_path / "artifacts" / "matrix_manifest.json").is_file()
