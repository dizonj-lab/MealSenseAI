"""Redis cache with graceful fallback to an in-process dict when Redis is unavailable."""
import json
import logging

import redis

from app.core.config import settings

log = logging.getLogger(__name__)
_client = None
_local: dict[str, str] = {}
stats = {"hits": 0, "misses": 0, "backend": "unknown"}


def _redis():
    global _client
    if _client is None:
        try:
            c = redis.Redis.from_url(settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
            c.ping()
            _client = c
            stats["backend"] = "redis"
        except Exception:
            _client = False
            stats["backend"] = "memory"
            log.warning("Redis unavailable; using in-memory cache")
    return _client or None


def get(key: str):
    r = _redis()
    try:
        raw = r.get(key) if r else _local.get(key)
    except Exception:
        raw = _local.get(key)
    if raw is None:
        stats["misses"] += 1
        return None
    stats["hits"] += 1
    return json.loads(raw)


def set(key: str, value, ttl: int = 3600):
    raw = json.dumps(value)
    r = _redis()
    try:
        if r:
            r.set(key, raw, ex=ttl)
            return
    except Exception:
        pass
    _local[key] = raw


def ping() -> bool:
    r = _redis()
    try:
        return bool(r and r.ping())
    except Exception:
        return False
