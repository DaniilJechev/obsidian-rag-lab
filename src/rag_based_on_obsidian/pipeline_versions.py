"""Pipeline version constants for deterministic cache namespaces."""

PARSER_VERSION = "markdown-parser-v1"
CHUNKING_VERSION = "not-applicable"
EMBEDDING_MODEL = None
EMBEDDING_VERSION = None
EMBEDDING_PARAMETERS: dict[str, object] = {}

# Bump when system prompt / packing policy changes (invalidates semantic cache).
PROMPT_VERSION = "generate-v1"
CACHE_SCHEMA_VERSION = "semantic-v1"


def cache_pipeline_fingerprint(
    *,
    llm_model: str,
    method: str,
    chunking_version: str,
    embedding_model: str,
    rerank_enabled: bool,
) -> str:
    """Stable namespace for semantic cache entries."""
    rerank_label = "rerank-on" if rerank_enabled else "rerank-off"
    return (
        f"{CACHE_SCHEMA_VERSION}|{llm_model.strip()}|{method.strip()}|"
        f"{chunking_version.strip()}|{embedding_model.strip()}|{rerank_label}|"
        f"{PROMPT_VERSION}"
    )


__all__ = [
    "CACHE_SCHEMA_VERSION",
    "CHUNKING_VERSION",
    "EMBEDDING_MODEL",
    "EMBEDDING_PARAMETERS",
    "EMBEDDING_VERSION",
    "PARSER_VERSION",
    "PROMPT_VERSION",
    "cache_pipeline_fingerprint",
]
