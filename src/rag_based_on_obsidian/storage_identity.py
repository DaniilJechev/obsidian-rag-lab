"""Stable identities shared by PostgreSQL, Qdrant and consistency checks."""

import hashlib
from uuid import NAMESPACE_URL, uuid5


def stable_point_key(
    *,
    source_path: str,
    source_content_hash: str,
    chunking_version: str,
    chunk_index: int,
) -> str:
    """Return a deterministic key independent of database identity IDs."""
    if not source_path.strip():
        raise ValueError("source_path must not be empty")
    if not source_content_hash.strip():
        raise ValueError("source_content_hash must not be empty")
    identity = "\x00".join(
        (
            source_path,
            source_content_hash,
            chunking_version,
            str(chunk_index),
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def point_id_from_key(point_key: str) -> str:
    """Convert a stable key into a Qdrant-compatible deterministic UUID."""
    return str(uuid5(NAMESPACE_URL, point_key))
