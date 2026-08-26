"""LangGraph orchestration for RAG generate (Phase 11)."""

from rag_based_on_obsidian.lang_graph.policies import MAX_SELF_CHECK_RETRIES

__all__ = [
    "MAX_SELF_CHECK_RETRIES",
    "build_generate_graph",
    "run_generate_graph",
]


def __getattr__(name: str):
    if name in {"build_generate_graph", "run_generate_graph"}:
        from rag_based_on_obsidian.lang_graph import workflow

        return getattr(workflow, name)
    raise AttributeError(name)
