from pathlib import Path

from rag_based_on_obsidian.eval.judge import OpenRouterJsonJudge
from rag_based_on_obsidian.eval.judge_factory import (
    build_generation_judge,
    judge_scale,
)
from rag_based_on_obsidian.eval.ragas_settings import load_ragas_config
from rag_based_on_obsidian.llm.settings import LLMConfig


def _llm_config() -> LLMConfig:
    return LLMConfig(
        name="test",
        model="openai/gpt-4o-mini",
        base_url="https://openrouter.ai/api/v1",
    )


def _write_config(path: Path, backend: str) -> None:
    path.write_text(
        f"""name: test
gold_path: gold.yaml
dataset_version: v0
api_base_url: http://127.0.0.1:8000
method: hybrid
top_k: 5
subset_size: 1
full_set: false
concurrency: 2
generate_model: openai/gpt-4o-mini
judge_model: openai/gpt-4o-mini
judge_backend: {backend}
""",
        encoding="utf-8",
    )


def test_judge_scale_keeps_backends_apart() -> None:
    assert judge_scale("json") == "0-5"
    assert judge_scale("ragas") == "0-1"


def test_build_generation_judge_json_keeps_openrouter_json_judge(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "ragas.yaml"
    _write_config(config_path, "json")
    captured: dict[str, object] = {}

    class _FakeProvider:
        def __init__(self, _config: object, *, api_key: str) -> None:
            captured["api_key"] = api_key

    monkeypatch.setattr(
        "rag_based_on_obsidian.eval.judge_factory.OpenRouterLLMProvider",
        _FakeProvider,
    )
    judge = build_generation_judge(
        load_ragas_config(config_path),
        _llm_config(),
        "sk-test",
    )
    assert isinstance(judge, OpenRouterJsonJudge)
    assert captured["api_key"] == "sk-test"


def test_build_generation_judge_ragas_uses_local_e5(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "ragas.yaml"
    _write_config(config_path, "ragas")
    captured: dict[str, object] = {}

    class _FakeEmbeddings:
        def __init__(self, _config: object) -> None:
            captured["loaded"] = True

    class _FakeJudge:
        @classmethod
        def from_openrouter(
            cls,
            llm_config: LLMConfig,
            api_key: str,
            embeddings: object,
        ) -> str:
            captured["api_key"] = api_key
            captured["model"] = llm_config.model
            captured["embeddings"] = embeddings
            return "ragas-judge"

    monkeypatch.setattr(
        "rag_based_on_obsidian.eval.judge_factory.TransformersEmbeddingProvider",
        _FakeEmbeddings,
    )
    monkeypatch.setattr(
        "rag_based_on_obsidian.eval.judge_factory.load_embedding_model_config",
        lambda _path: object(),
    )
    monkeypatch.setattr(
        "rag_based_on_obsidian.eval.judge_factory.RagasFrameworkJudge",
        _FakeJudge,
    )
    judge = build_generation_judge(
        load_ragas_config(config_path),
        _llm_config(),
        "sk-test",
    )
    assert judge == "ragas-judge"
    assert captured["loaded"] is True
    assert captured["api_key"] == "sk-test"
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["embeddings"] is not None
