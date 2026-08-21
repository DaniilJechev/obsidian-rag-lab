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
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "log_dict",
        lambda payload, path: logged.setdefault("artifact", (payload, path)),
    )
    monkeypatch.setattr(mlflow_tracking, "process_rss_mb", lambda: 128.0)

    metrics = DatasetMetrics(
        question_count=2,
        scored_count=2,
        skipped_count=0,
        k=10,
        ndcg=0.6,
        mrr=0.7,
        recall=0.9,
        hit=1.0,
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
    assert logged["tags"]["sprint"] == "18"
    assert logged["tags"]["experiment_type"] == "eval"
    assert logged["metrics"]["ndcg_at_10"] == 0.6
    assert "ndcg" not in logged["metrics"]
    assert "ndcg@10" not in logged["metrics"]
    assert logged["params"]["k"] == "10"


def test_log_eval_harness_run_accepts_live_kind(monkeypatch) -> None:
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
    monkeypatch.setattr(
        mlflow_tracking.mlflow,
        "log_dict",
        lambda payload, path: logged.setdefault("artifact", (payload, path)),
    )
    monkeypatch.setattr(mlflow_tracking, "process_rss_mb", lambda: 128.0)
    metrics = DatasetMetrics(
        question_count=1,
        scored_count=1,
        skipped_count=0,
        k=5,
        ndcg=0.2,
        mrr=0.3,
        recall=0.5,
        hit=1.0,
    )

    run_id = mlflow_tracking.log_eval_harness_run(
        dataset_version="phase7-note-level-v1",
        run_kind="live",
        metrics=metrics,
        duration_seconds=1.0,
        artifact={"items": [{"item_id": "q001"}]},
        extra_params={"rrf_k": 10},
        extra_metrics={"rrf_k": 10.0},
        extra_tags={"retrieval_method": "dense"},
        run_name="eval-live-dense",
    )

    assert run_id == "eval-run"
    assert logged["params"]["run_kind"] == "live"
    assert logged["params"]["rrf_k"] == "10"
    assert logged["tags"]["run_kind"] == "live"
    assert logged["tags"]["retrieval_method"] == "dense"
    assert logged["metrics"]["ndcg_at_5"] == 0.2
    assert logged["metrics"]["rrf_k"] == 10.0
    assert logged["artifact"][1] == "per_question.json"


def test_log_eval_harness_run_rejects_unknown_kind() -> None:
    metrics = DatasetMetrics(
        question_count=0,
        scored_count=0,
        skipped_count=0,
        k=None,
        ndcg=None,
        mrr=None,
        recall=None,
        hit=None,
    )
    try:
        mlflow_tracking.log_eval_harness_run(
            dataset_version="x",
            run_kind="guess",
            metrics=metrics,
            duration_seconds=0.0,
        )
    except ValueError as exc:
        assert "run_kind" in str(exc)
    else:
        raise AssertionError("unknown run_kind must be rejected")
