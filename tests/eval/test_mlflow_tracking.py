from rag_based_on_obsidian.eval import mlflow_tracking
from rag_based_on_obsidian.eval.contracts import DatasetMetrics


class _FakeRun:
    def __init__(self) -> None:
        self.info = type("Info", (), {"run_id": "eval-run"})()

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_log_eval_harness_run_writes_note_level_tags(monkeypatch) -> None:
    logged: dict[str, object] = {}
    monkeypatch.setattr(mlflow_tracking, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(
        mlflow_tracking.os,
        "environ",
        {"MLFLOW_TRACKING_URI": "http://127.0.0.1:5000"},
    )
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "set_tracking_uri",
        lambda uri: logged.setdefault("uri", uri),
    )
    monkeypatch.setattr(mlflow_tracking, "_configure_eval_experiment", lambda: None)
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "start_run",
        lambda **_kwargs: _FakeRun(),
    )
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "log_params",
        lambda params: logged.setdefault("params", params),
    )
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "set_tags",
        lambda tags: logged.setdefault("tags", tags),
    )
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "log_metrics",
        lambda metrics: logged.setdefault("metrics", metrics),
    )

    metrics = DatasetMetrics(
        question_count=2,
        scored_count=2,
        skipped_count=0,
        ndcg_at_5=0.5,
        ndcg_at_10=0.6,
        mrr_at_10=0.7,
        recall_at_5=0.8,
        recall_at_10=0.9,
        hit_at_10=1.0,
    )
    run_id = mlflow_tracking.log_eval_harness_run(
        dataset_version="phase7-note-level-v0-draft",
        run_kind="synthetic_harness",
        metrics=metrics,
        duration_seconds=0.2,
    )

    assert run_id == "eval-run"
    assert logged["params"]["run_kind"] == "synthetic_harness"
    assert logged["params"]["label_granularity"] == "note"
    assert logged["tags"]["phase"] == "7"
    assert logged["tags"]["sprint"] == "17"
    assert logged["tags"]["experiment_type"] == "eval"
    assert logged["metrics"]["ndcg_at_10"] == 0.6


def test_log_eval_harness_run_rejects_live_kind() -> None:
    metrics = DatasetMetrics(
        question_count=0,
        scored_count=0,
        skipped_count=0,
        ndcg_at_5=None,
        ndcg_at_10=None,
        mrr_at_10=None,
        recall_at_5=None,
        recall_at_10=None,
        hit_at_10=None,
    )
    try:
        mlflow_tracking.log_eval_harness_run(
            dataset_version="x",
            run_kind="live",
            metrics=metrics,
            duration_seconds=0.0,
        )
    except ValueError as exc:
        assert "live" in str(exc)
    else:
        raise AssertionError("live run_kind must be rejected in Sprint 17")
