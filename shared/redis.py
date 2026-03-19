from __future__ import annotations

from typing import Any

from redis.asyncio import Redis

from shared.config import get_base_settings


_redis_client: Redis[Any] | None = None


def get_redis_client() -> Redis[Any]:
    global _redis_client
    if _redis_client is None:
        settings = get_base_settings()
        _redis_client = Redis.from_url(str(settings.redis_url), decode_responses=True)
    return _redis_client

