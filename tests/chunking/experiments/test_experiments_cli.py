from __future__ import annotations

from pathlib import Path

from rag_based_on_obsidian.chunking.experiments.experiments_cli import main


def test_cli_dry_run_discovers_corpus_without_tracking(tmp_path: Path, capsys) -> None:
    vault = tmp_path / "vault"
    (vault / "DLS1").mkdir(parents=True)
    (vault / "DLS1" / "note.md").write_text("# Heading\n\nbody", encoding="utf-8")
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        """name: test-policy
chunking_version: test-v1
chunk_size: 256
chunk_overlap: 0
separators: ["\\n\\n", "\\n", " "]
""",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--vault-root",
            str(vault),
            "--allowed-directory",
            "DLS1",
            "--policy",
            str(policy),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Discovered source trees: 1" in output
    assert str(policy) in output
