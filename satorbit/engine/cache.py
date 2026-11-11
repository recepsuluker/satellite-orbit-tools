"""Redis cache layer for analysis results and TLE data."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from satorbit.config import get_settings
from satorbit.logging_config import get_logger

logger = get_logger("engine.cache")

_redis_client = None
_redis_available = False


def _get_redis():
    """Lazy Redis connection with graceful fallback."""
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    try:
        import redis

        settings = get_settings()
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected at %s:%d", settings.redis_host, settings.redis_port)
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning("Redis unavailable, cache disabled: %s", e)
        return None


def _make_key(prefix: str, *args: str) -> str:
    """Create a cache key from prefix and arguments."""
    raw = ":".join(str(a) for a in args)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"sattools:{prefix}:{hashed}"


def cache_get(prefix: str, *args: str) -> Any | None:
    """Get a value from cache. Returns None on miss or if Redis unavailable."""
    r = _get_redis()
    if r is None:
        return None

    key = _make_key(prefix, *args)
    try:
        value = r.get(key)
        if value is not None:
            logger.debug("Cache HIT: %s", key)
            return json.loads(value)
        logger.debug("Cache MISS: %s", key)
        return None
    except Exception as e:
        logger.warning("Cache get error: %s", e)
        return None


def cache_set(prefix: str, *args: str, value: Any, ttl: int | None = None) -> bool:
    """Set a value in cache with optional TTL in seconds."""
    r = _get_redis()
    if r is None:
        return False

    key = _make_key(prefix, *args)
    try:
        serialized = json.dumps(value, default=str)
        if ttl:
            r.setex(key, ttl, serialized)
        else:
            r.set(key, serialized)
        logger.debug("Cache SET: %s (ttl=%s)", key, ttl)
        return True
    except Exception as e:
        logger.warning("Cache set error: %s", e)
        return False


def cache_delete(prefix: str, *args: str) -> bool:
    """Delete a cache entry."""
    r = _get_redis()
    if r is None:
        return False

    key = _make_key(prefix, *args)
    try:
        r.delete(key)
        return True
    except Exception:
        return False


def cache_clear_prefix(prefix: str) -> int:
    """Clear all cache entries with a given prefix."""
    r = _get_redis()
    if r is None:
        return 0

    try:
        pattern = f"sattools:{prefix}:*"
        keys = list(r.scan_iter(pattern))
        if keys:
            r.delete(*keys)
        logger.info("Cleared %d cache entries for prefix '%s'", len(keys), prefix)
        return len(keys)
    except Exception as e:
        logger.warning("Cache clear error: %s", e)
        return 0


def get_cache_stats() -> dict:
    """Get cache statistics."""
    r = _get_redis()
    if r is None:
        return {"available": False}

    try:
        info = r.info("memory")
        keys = r.dbsize()
        return {
            "available": True,
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "total_keys": keys,
        }
    except Exception:
        return {"available": False}
