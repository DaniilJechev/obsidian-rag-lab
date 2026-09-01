import json
from pathlib import Path
from typing import Self

from rag_based_on_obsidian.eval import cli
from rag_based_on_obsidian.eval.contracts import (
    DatasetMetrics,
    LiveGoldItem,
    QuestionMetrics,
)
from rag_based_on_obsidian.eval.retrieval.live_session import LiveSessionInfo
from rag_based_on_obsidian.retrieval.contracts import RetrievalMethod
from rag_based_on_obsidian.retrieval.settings import RetrievalConfig


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
            "--top-k",
            "10",
            "--log-mlflow",
        ]
    )

    assert exit_code == 0
    assert logged["run_kind"] == "synthetic_harness"
    assert logged["dataset_version"] == "phase7-note-level-v0-draft"


class _FakeEngine:
    def begin(self) -> Self:
        return self

    def __enter__(self) -> object:
        return object()

    def __exit__(self, *_args: object) -> None:
        return None

    def dispose(self) -> None:
        return None


class _FakeSession:
    def __init__(self, **kwargs: object) -> None:
        method = kwargs["method"]
        assert isinstance(method, RetrievalMethod)
        self.info = LiveSessionInfo(
            method=method,
            collection_name="notes__v2__e5__rev__384",
            chunking_version="sprint9-policy-512-v2",
            top_k=int(kwargs.get("top_k", 10)),
            candidate_k=int(kwargs.get("candidate_k", 20)),
            rrf_k=int(kwargs.get("rrf_k", 60)),
            model_name="e5",
            model_revision="rev",
            device="cpu",
            dimension=384,
            normalized=True,
            max_length=512,
            batch_size=8,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def search(self, query: str) -> list[object]:
        return []


def _stub_live_cli(
    monkeypatch, *, method: RetrievalMethod
) -> tuple[dict[str, object], dict[str, object]]:
    item = LiveGoldItem(
        item_id="q001",
        eval_item_id=1,
        question="What is dropout?",
        relevant_note_ids=(10,),
        relevant_note_paths=("DLS1/Dropout.md",),
        dataset_version="phase7-note-level-v1",
    )
    summary = DatasetMetrics(
        question_count=1,
        scored_count=1,
        skipped_count=0,
        k=5,
        ndcg=0.5,
        mrr=1.0,
        recall=1.0,
        hit=1.0,
    )
    logged: dict[str, object] = {}
    monkeypatch.setattr(cli, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(cli, "load_database_url", lambda: "postgresql://example")
    monkeypatch.setattr(
        cli,
        "load_gold_yaml",
        lambda _path: ("phase7-note-level-v1", ()),
    )
    monkeypatch.setattr(
        cli,
        "load_retrieval_config",
        lambda _path: RetrievalConfig(
            name="test",
            chunking_version="sprint9-policy-512-v2",
            top_k=5,
            candidate_k=20,
        ),
    )
    monkeypatch.setattr(cli, "create_engine", lambda _url: _FakeEngine())
    monkeypatch.setattr(cli, "load_eval_items", lambda *_args: (object(),))
    monkeypatch.setattr(cli, "load_note_path_index", lambda _conn: {})
    monkeypatch.setattr(cli, "bind_live_gold_items", lambda *_args: (item,))
    session_kwargs: dict[str, object] = {}

    def fake_session(**kwargs: object) -> _FakeSession:
        session_kwargs.update(kwargs)
        return _FakeSession(**kwargs)

    monkeypatch.setattr(cli, "open_live_session", fake_session)
    monkeypatch.setattr(
        cli,
        "run_live_eval",
        lambda _items, _retrieve, **_kwargs: (
            [QuestionMetrics(item_id="q001", skipped=False, k=5)],
            [{"item_id": "q001"}],
        ),
    )
    monkeypatch.setattr(cli, "macro_average", lambda _results, **_kwargs: summary)
    monkeypatch.setattr(
        cli,
        "log_eval_harness_run",
        lambda **kwargs: logged.update(kwargs) or "live-run",
    )
    return logged, session_kwargs


def test_eval_run_cli_prints_live_metrics_without_mlflow(monkeypatch, capsys) -> None:
    logged, _session = _stub_live_cli(monkeypatch, method=RetrievalMethod.DENSE)

    exit_code = cli.main(
        ["run", "--method", "dense", "--top-k", "5", "--no-log-mlflow"]
    )

    assert exit_code == 0
    assert logged == {}
    output = capsys.readouterr().out
    assert '"run_kind": "live"' in output
    assert '"retrieval_method": "dense"' in output
    assert '"ndcg_at_5": 0.5' in output
    assert '"mrr_at_5": 1.0' in output


def test_eval_run_cli_logs_live_mlflow(monkeypatch, capsys) -> None:
    logged, session = _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(["run", "--method", "hybrid", "--top-k", "5"])

    assert exit_code == 0
    assert session["top_k"] == 5
    assert session["candidate_k"] == 10
    assert session["rrf_k"] == 60
    assert logged["run_kind"] == "live"
    assert logged["run_name"] == "eval-live-hybrid-disable_rerank"
    assert logged["experiment_name"] == "phase-12-rerank-retrieval-eval"
    assert logged["extra_tags"]["retrieval_method"] == "hybrid"
    assert logged["extra_tags"]["rerank_label"] == "disable_rerank"
    assert logged["extra_params"]["enable_rerank"] is False
    assert logged["extra_params"]["rrf_k"] == 60
    assert logged["extra_metrics"]["rrf_k"] == 60.0
    assert '"mlflow_run_id": "live-run"' in capsys.readouterr().out


def test_eval_run_cli_enable_rerank_logs_enable_label(monkeypatch) -> None:
    logged, session = _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "hybrid",
            "--top-k",
            "5",
            "--candidate-k",
            "20",
            "--enable-rerank",
        ]
    )

    assert exit_code == 0
    assert session["enable_rerank"] is True
    assert logged["run_name"] == "eval-live-hybrid-enable_rerank"
    assert logged["experiment_name"] == "phase-12-rerank-retrieval-eval"
    assert logged["extra_tags"]["rerank_label"] == "enable_rerank"
    assert logged["extra_params"]["enable_rerank"] is True


def test_eval_run_cli_rejects_enable_rerank_for_dense(monkeypatch, capsys) -> None:
    _stub_live_cli(monkeypatch, method=RetrievalMethod.DENSE)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "dense",
            "--top-k",
            "5",
            "--enable-rerank",
            "--no-log-mlflow",
        ]
    )

    assert exit_code == 2
    assert "--enable-rerank requires --method hybrid" in capsys.readouterr().err


def test_eval_run_cli_keeps_explicit_candidate_k(monkeypatch) -> None:
    _logged, session = _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "hybrid",
            "--top-k",
            "5",
            "--candidate-k",
            "20",
            "--no-log-mlflow",
        ]
    )

    assert exit_code == 0
    assert session["candidate_k"] == 20
    assert session["top_k"] == 5


def test_eval_run_cli_keeps_explicit_rrf_k(monkeypatch) -> None:
    logged, session = _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "hybrid",
            "--top-k",
            "5",
            "--rrf-k",
            "30",
        ]
    )

    assert exit_code == 0
    assert session["rrf_k"] == 30
    assert logged["extra_params"]["rrf_k"] == 30
    assert logged["extra_metrics"]["rrf_k"] == 30.0


def test_eval_run_cli_rejects_non_positive_rrf_k(monkeypatch, capsys) -> None:
    _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "hybrid",
            "--top-k",
            "5",
            "--rrf-k",
            "0",
            "--no-log-mlflow",
        ]
    )

    assert exit_code == 2
    assert "--rrf-k must be positive" in capsys.readouterr().err


def test_eval_run_cli_rejects_candidate_k_below_top_k(monkeypatch, capsys) -> None:
    _stub_live_cli(monkeypatch, method=RetrievalMethod.HYBRID)

    exit_code = cli.main(
        [
            "run",
            "--method",
            "hybrid",
            "--top-k",
            "5",
            "--candidate-k",
            "3",
            "--no-log-mlflow",
        ]
    )

    assert exit_code == 2
    assert "--candidate-k must be >= --top-k" in capsys.readouterr().err


def test_eval_run_cli_requires_top_k(capsys) -> None:
    try:
        cli.main(["run", "--method", "bm25"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--top-k must be required")
    assert "--top-k" in capsys.readouterr().err
