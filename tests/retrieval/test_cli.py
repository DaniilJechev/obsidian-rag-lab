from argparse import Namespace

from rag_based_on_obsidian.retrieval import cli
from rag_based_on_obsidian.retrieval.mlflow_tracking import SEARCH_EXPERIMENT_NAME
from rag_based_on_obsidian.retrieval.progress import SearchProgress


def test_search_cli_runs_hybrid_only_when_requested(
    monkeypatch,
) -> None:
    called: list[str] = []

    def fake_dense(*_args: object) -> tuple[list[object], float, str, tuple[str, str, str, int]]:
        called.append("dense")
        return [], 0.1, "collection", ("model", "rev", "cpu", 384)

    def fake_bm25(*_args: object) -> tuple[list[object], float]:
        called.append("bm25")
        return [], 0.1

    def fake_hybrid(*_args: object) -> tuple[list[object], float, str, tuple[str, str, str, int]]:
        called.append("hybrid")
        return [], 0.1, "collection", ("model", "rev", "cpu", 384)

    monkeypatch.setattr(cli, "_run_dense", fake_dense)
    monkeypatch.setattr(cli, "_run_bm25", fake_bm25)
    monkeypatch.setattr(cli, "_run_hybrid", fake_hybrid)
    monkeypatch.setattr(cli, "_record_search_run", lambda **_kwargs: None)
    monkeypatch.setattr(cli, "_print_results", lambda *_args, **_kwargs: None)

    assert cli.main(["dense", "--query", "nDCG"]) == 0
    assert called == ["dense"]

    called.clear()
    assert cli.main(["hybrid", "--query", "nDCG"]) == 0
    assert called == ["hybrid"]


def test_search_cli_rejects_unknown_operation(monkeypatch, capsys) -> None:
    class FakeParser:
        def parse_args(self, _argv: object = None) -> Namespace:
            return Namespace(operation="rrf")

    monkeypatch.setattr(cli, "build_parser", lambda: FakeParser())
    assert cli.main([]) == 2
    captured = capsys.readouterr()
    assert "explicit operation" in captured.err


def test_search_progress_records_stage_durations() -> None:
    progress = SearchProgress()
    progress.mark("load_config", top_k=5)
    progress.mark("dense_search")
    assert "load_config" in progress.stage_seconds
    assert "dense_search" in progress.stage_seconds
    assert progress.total_seconds >= 0.0


def test_search_experiment_name_is_searching() -> None:
    assert SEARCH_EXPERIMENT_NAME == "searching"
