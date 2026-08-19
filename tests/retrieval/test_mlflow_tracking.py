from rag_based_on_obsidian.retrieval import mlflow_tracking


class _FakeRun:
    def __init__(self) -> None:
        self.info = type("Info", (), {"run_id": "search-run"})()

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_log_search_run_writes_operation_and_latency(monkeypatch) -> None:
    logged: dict[str, object] = {}

    monkeypatch.setattr(mlflow_tracking, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(mlflow_tracking.os, "environ", {"MLFLOW_TRACKING_URI": "http://127.0.0.1:5000"})
    monkeypatch.setattr(mlflow_tracking.mlflow, "set_tracking_uri", lambda uri: logged.setdefault("uri", uri))
    monkeypatch.setattr(mlflow_tracking, "_configure_search_experiment", lambda: None)
    monkeypatch.setattr(mlflow_tracking.mlflow, "start_run", lambda **_kwargs: _FakeRun())
    monkeypatch.setattr(mlflow_tracking.mlflow, "log_params", lambda params: logged.setdefault("params", params))
    monkeypatch.setattr(mlflow_tracking.mlflow, "set_tags", lambda tags: logged.setdefault("tags", tags))
    monkeypatch.setattr(mlflow_tracking.mlflow, "log_metrics", lambda metrics: logged.setdefault("metrics", metrics))
    monkeypatch.setattr(mlflow_tracking.mlflow, "set_tag", lambda *args: None)

    run_id = mlflow_tracking.log_search_run(
        operation="hybrid",
        query="nDCG",
        top_k=5,
        candidate_k=20,
        rrf_k=60,
        chunking_version="sprint9-policy-512-v2",
        result_count=3,
        duration_seconds=1.25,
        stage_seconds={"embed_query": 0.4, "rrf": 0.01},
        collection_name="rag_chunks",
        model_name="intfloat/multilingual-e5-small",
        model_revision="main",
        device="cpu",
        dimension=384,
    )

    assert run_id == "search-run"
    assert logged["params"]["operation"] == "hybrid"
    assert logged["metrics"]["duration_seconds"] == 1.25
    assert logged["metrics"]["result_count"] == 3.0
    assert logged["metrics"]["stage_embed_query_seconds"] == 0.4
    assert logged["tags"]["experiment_type"] == "retrieval-search"
    assert logged["tags"]["sprint"] == "15"
