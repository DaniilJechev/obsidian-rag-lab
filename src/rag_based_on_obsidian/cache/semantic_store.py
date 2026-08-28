"""Semantic cache storage backends (Redis + in-memory for tests)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from rag_based_on_obsidian.cache.settings import CacheConfig
from rag_based_on_obsidian.cache.similarity import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticCacheHit:
    """One cache lookup match."""

    entry_id: str
    similarity: float
    matched_query: str
    response: dict[str, Any]


class SemanticCacheStore(Protocol):
    """Lookup/store contract used by LangGraph cache nodes."""

    def lookup(
        self,
        pipeline_version: str,
        query_embedding: tuple[float, ...],
    ) -> SemanticCacheHit | None:
        """Return the best match at or above threshold, or None."""

    def store(
        self,
        pipeline_version: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        response: dict[str, Any],
    ) -> None:
        """Persist one successful generate payload."""


def _entry_key(pipeline_version: str, entry_id: str) -> str:
    safe_version = pipeline_version.replace(":", "_")
    return f"rag:cache:semantic:{safe_version}:entry:{entry_id}"


def _ids_key(pipeline_version: str) -> str:
    safe_version = pipeline_version.replace(":", "_")
    return f"rag:cache:semantic:{safe_version}:ids"


def _order_key(pipeline_version: str) -> str:
    safe_version = pipeline_version.replace(":", "_")
    return f"rag:cache:semantic:{safe_version}:order"


def _serialize_entry(
    *,
    query_text: str,
    query_embedding: tuple[float, ...],
    response: dict[str, Any],
    pipeline_version: str,
) -> str:
    payload = {
        "query_text": query_text,
        "query_embedding": list(query_embedding),
        "response": response,
        "pipeline_version": pipeline_version,
        "created_at": datetime.now(UTC).isoformat(),
    }
    return json.dumps(payload, ensure_ascii=False)


def _deserialize_entry(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("cache entry must be a JSON object")
    return payload


class InMemorySemanticCacheStore:
    """Process-local store for unit tests (no Redis)."""

    def __init__(self, config: CacheConfig) -> None:
        self._config = config
        self._entries: dict[str, dict[str, dict[str, Any]]] = {}
        self._order: dict[str, list[str]] = {}

    def lookup(
        self,
        pipeline_version: str,
        query_embedding: tuple[float, ...],
    ) -> SemanticCacheHit | None:
        entries = self._entries.get(pipeline_version, {})
        if not entries:
            return None
        best: SemanticCacheHit | None = None
        for entry_id, payload in entries.items():
            stored = payload.get("query_embedding")
            if not isinstance(stored, list):
                continue
            similarity = cosine_similarity(
                query_embedding,
                tuple(float(value) for value in stored),
            )
            if similarity < self._config.similarity_threshold:
                continue
            if best is None or similarity > best.similarity:
                response = payload.get("response")
                query_text = payload.get("query_text")
                if not isinstance(response, dict) or not isinstance(query_text, str):
                    continue
                best = SemanticCacheHit(
                    entry_id=entry_id,
                    similarity=similarity,
                    matched_query=query_text,
                    response=response,
                )
        if best is not None and self._config.refresh_ttl_on_hit:
            order = self._order.setdefault(pipeline_version, [])
            if best.entry_id in order:
                order.remove(best.entry_id)
            order.append(best.entry_id)
        return best

    def store(
        self,
        pipeline_version: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        response: dict[str, Any],
    ) -> None:
        bucket = self._entries.setdefault(pipeline_version, {})
        order = self._order.setdefault(pipeline_version, [])
        entry_id = uuid.uuid4().hex
        bucket[entry_id] = {
            "query_text": query_text,
            "query_embedding": list(query_embedding),
            "response": dict(response),
        }
        order.append(entry_id)
        self._evict_if_needed(pipeline_version, bucket, order)

    def _evict_if_needed(
        self,
        pipeline_version: str,
        bucket: dict[str, dict[str, Any]],
        order: list[str],
    ) -> None:
        while len(order) > self._config.max_entries:
            oldest = order.pop(0)
            bucket.pop(oldest, None)


class RedisSemanticCacheStore:
    """Redis JSON entries with linear-scan cosine lookup."""

    def __init__(self, config: CacheConfig, client: Any) -> None:
        self._config = config
        self._client = client

    def lookup(
        self,
        pipeline_version: str,
        query_embedding: tuple[float, ...],
    ) -> SemanticCacheHit | None:
        try:
            entry_ids = self._client.smembers(_ids_key(pipeline_version))
        except Exception:
            logger.exception("semantic cache lookup failed")
            return None
        if not entry_ids:
            return None
        best: SemanticCacheHit | None = None
        for raw_id in entry_ids:
            entry_id = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            try:
                raw_entry = self._client.get(_entry_key(pipeline_version, entry_id))
            except Exception:
                logger.exception("semantic cache get failed entry=%s", entry_id)
                continue
            if raw_entry is None:
                self._remove_stale(pipeline_version, entry_id)
                continue
            text = raw_entry.decode() if isinstance(raw_entry, bytes) else str(raw_entry)
            try:
                payload = _deserialize_entry(text)
            except (json.JSONDecodeError, TypeError):
                logger.warning("invalid cache entry entry=%s", entry_id)
                continue
            stored = payload.get("query_embedding")
            if not isinstance(stored, list):
                continue
            similarity = cosine_similarity(
                query_embedding,
                tuple(float(value) for value in stored),
            )
            if similarity < self._config.similarity_threshold:
                continue
            response = payload.get("response")
            query_text = payload.get("query_text")
            if not isinstance(response, dict) or not isinstance(query_text, str):
                continue
            if best is None or similarity > best.similarity:
                best = SemanticCacheHit(
                    entry_id=entry_id,
                    similarity=similarity,
                    matched_query=query_text,
                    response=response,
                )
        if best is not None and self._config.refresh_ttl_on_hit:
            try:
                self._client.expire(
                    _entry_key(pipeline_version, best.entry_id),
                    self._config.ttl_seconds,
                )
                self._client.zadd(
                    _order_key(pipeline_version),
                    {best.entry_id: datetime.now(UTC).timestamp()},
                )
            except Exception:
                logger.exception("semantic cache ttl refresh failed")
        return best

    def store(
        self,
        pipeline_version: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        response: dict[str, Any],
    ) -> None:
        entry_id = uuid.uuid4().hex
        key = _entry_key(pipeline_version, entry_id)
        body = _serialize_entry(
            query_text=query_text,
            query_embedding=query_embedding,
            response=response,
            pipeline_version=pipeline_version,
        )
        try:
            self._client.set(key, body, ex=self._config.ttl_seconds)
            self._client.sadd(_ids_key(pipeline_version), entry_id)
            self._client.zadd(
                _order_key(pipeline_version),
                {entry_id: datetime.now(UTC).timestamp()},
            )
            self._evict_if_needed(pipeline_version)
        except Exception:
            logger.exception("semantic cache store failed")

    def _evict_if_needed(self, pipeline_version: str) -> None:
        try:
            count = int(self._client.scard(_ids_key(pipeline_version)))
        except Exception:
            logger.exception("semantic cache scard failed")
            return
        overflow = count - self._config.max_entries
        if overflow <= 0:
            return
        try:
            stale_ids = self._client.zrange(_order_key(pipeline_version), 0, overflow - 1)
        except Exception:
            logger.exception("semantic cache eviction scan failed")
            return
        for raw_id in stale_ids:
            entry_id = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            self._remove_stale(pipeline_version, entry_id)

    def _remove_stale(self, pipeline_version: str, entry_id: str) -> None:
        try:
            self._client.delete(_entry_key(pipeline_version, entry_id))
            self._client.srem(_ids_key(pipeline_version), entry_id)
            self._client.zrem(_order_key(pipeline_version), entry_id)
        except Exception:
            logger.exception("semantic cache stale cleanup failed entry=%s", entry_id)


def build_semantic_cache_store(
    config: CacheConfig,
    *,
    redis_url: str | None,
) -> SemanticCacheStore | None:
    """Return Redis store when URL is set; None when cache infra unavailable."""
    if not redis_url or not redis_url.strip():
        logger.warning("semantic cache store skipped: REDIS_URL is empty")
        return None
    try:
        import redis
    except ImportError as exc:
        raise RuntimeError("redis package is required for semantic cache") from exc
    client = redis.Redis.from_url(redis_url.strip(), decode_responses=False)
    return RedisSemanticCacheStore(config, client)
