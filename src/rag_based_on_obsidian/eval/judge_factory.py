"""Choose JSON 0–5 or ragas 0–1 without mixing scales."""

from __future__ import annotations

from rag_based_on_obsidian.config import DEFAULT_EMBEDDING_MODEL_CONFIG_PATH
from rag_based_on_obsidian.embeddings.settings import load_embedding_model_config
from rag_based_on_obsidian.embeddings.transformers_provider import (
    TransformersEmbeddingProvider,
)
from rag_based_on_obsidian.eval.e5_langchain_embeddings import E5LangchainEmbeddings
from rag_based_on_obsidian.eval.judge import GenerationJudge, OpenRouterJsonJudge
from rag_based_on_obsidian.eval.ragas_judge import RagasFrameworkJudge
from rag_based_on_obsidian.eval.ragas_settings import RagasRunConfig
from rag_based_on_obsidian.llm.openrouter import OpenRouterLLMProvider
from rag_based_on_obsidian.llm.settings import LLMConfig


def judge_scale(backend: str) -> str:
    """JSON Likert is 0–5; native ragas metrics are 0–1."""
    return "0-5" if backend == "json" else "0-1"


def build_generation_judge(
    config: RagasRunConfig,
    llm_config: LLMConfig,
    api_key: str,
) -> GenerationJudge:
    """Build the configured judge. Ragas loads local e5 once per CLI run."""
    if config.judge_backend == "json":
        return OpenRouterJsonJudge(
            OpenRouterLLMProvider(llm_config, api_key=api_key),
        )

    provider = TransformersEmbeddingProvider(
        load_embedding_model_config(DEFAULT_EMBEDDING_MODEL_CONFIG_PATH),
    )
    return RagasFrameworkJudge.from_openrouter(
        llm_config,
        api_key,
        E5LangchainEmbeddings(provider),
    )
