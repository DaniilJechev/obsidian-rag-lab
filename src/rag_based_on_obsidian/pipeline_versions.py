"""Version constants for deterministic pipeline behavior."""

PARSER_VERSION = "markdown-parser-v1"
CHUNKING_VERSION = "not-applicable"
EMBEDDING_MODEL = None
EMBEDDING_VERSION = None
EMBEDDING_PARAMETERS: dict[str, object] = {}

__all__ = [
    "CHUNKING_VERSION",
    "EMBEDDING_MODEL",
    "EMBEDDING_PARAMETERS",
    "EMBEDDING_VERSION",
    "PARSER_VERSION",
]
