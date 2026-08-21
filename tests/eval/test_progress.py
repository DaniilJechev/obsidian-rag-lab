from rag_based_on_obsidian.eval.progress import EvalProgress


def test_eval_progress_records_stage_durations() -> None:
    progress = EvalProgress()
    progress.mark("load_yaml", items=50)
    progress.mark("connect_postgres")

    assert "load_yaml" in progress.stage_seconds
    assert "connect_postgres" in progress.stage_seconds
    assert progress.stage_seconds["load_yaml"] >= 0.0
