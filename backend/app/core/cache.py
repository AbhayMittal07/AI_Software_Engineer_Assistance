"""Redis-backed cache with a transparent in-process fallback."""
import json
import time
from typing import Any, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class _MemoryBackend:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}
        self._counters: dict[str, tuple[float, int]] = {}

    async def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl: int) -> None:
        self._store[key] = (time.time() + ttl if ttl else 0, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr_window(self, key: str, window: int) -> int:
        now = time.time()
        reset_at, count = self._counters.get(key, (0.0, 0))
        if reset_at < now:
            reset_at, count = now + window, 0
        count += 1
        self._counters[key] = (reset_at, count)
        return count


class CacheService:
    def __init__(self) -> None:
        self._redis = None
        self._memory = _MemoryBackend()
        self.backend = "memory"

    async def connect(self) -> None:
        try:
            import redis.asyncio as redis  # imported lazily so Redis stays optional

            client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
            await client.ping()
            self._redis = client
            self.backend = "redis"
            logger.info("Cache backend: redis (%s)", settings.REDIS_URL)
        except Exception as exc:  # noqa: BLE001 - Redis is optional
            self._redis = None
            self.backend = "memory"
            logger.warning("Redis unavailable (%s); using in-process cache", exc)

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await (self._redis.get(key) if self._redis else self._memory.get(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        payload = json.dumps(value, default=str)
        ttl = ttl if ttl is not None else settings.CACHE_TTL_SECONDS
        if self._redis:
            await self._redis.set(key, payload, ex=ttl)
        else:
            await self._memory.set(key, payload, ttl)

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(key)
        else:
            await self._memory.delete(key)

    async def delete_prefix(self, prefix: str) -> None:
        if self._redis:
            async for key in self._redis.scan_iter(match=f"{prefix}*"):
                await self._redis.delete(key)
        else:
            for key in [k for k in list(self._memory._store) if k.startswith(prefix)]:
                await self._memory.delete(key)

    async def hit_rate_limit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Returns (blocked, current_count)."""
        if self._redis:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, window)
        else:
            count = await self._memory.incr_window(key, window)
        return count > limit, count


cache = CacheService()
