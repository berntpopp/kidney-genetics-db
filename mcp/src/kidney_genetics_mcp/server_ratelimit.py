"""Token-bucket rate limiter for the Kidney-Genetics-DB MCP server.

Provides a layered rate limiter with:
- A global requests-per-second ceiling (token bucket).
- Per-tool cost budgets so heavy tools get a smaller individual allowance.

The in-process implementation requires no external dependencies and is fully
deterministic when a custom clock is injected (useful for unit tests).

If ``settings.redis_url`` is set, a thin Redis backend is used instead for the
global bucket, keyed on a per-second window with INCR+EXPIRE semantics. The
Redis path is optional — the in-process path is always available and is the
default; if Redis is unreachable the limiter silently falls back.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

#: Heavy tools that carry a smaller per-tool burst budget.
HEAVY_TOOLS: frozenset[str] = frozenset(
    {"kgdb_get_interaction_partners", "kgdb_get_database_stats"}
)

#: Default per-tool budgets (tokens refilled continuously). Deliberately
#: generous so normal interactive or test use is never throttled.
DEFAULT_TOOL_CAPACITY: float = 30.0
HEAVY_TOOL_CAPACITY: float = 10.0


class _TokenBucket:
    """A single token-bucket with capacity and refill rate.

    Tokens are refilled continuously at *rate* tokens/second up to *capacity*.
    Each call to :meth:`consume` removes *cost* tokens and returns whether the
    bucket had enough.
    """

    def __init__(
        self,
        capacity: float,
        rate: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialise the bucket full to *capacity*.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            rate: Refill rate in tokens per second.
            clock: Monotonic clock callable (injectable for deterministic tests).
        """
        self._capacity = capacity
        self._rate = rate
        self._clock = clock
        self._tokens: float = capacity
        self._last_refill: float = clock()

    def _refill(self) -> None:
        """Add tokens proportional to elapsed time since the last refill."""
        now = self._clock()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)

    def consume(self, cost: float = 1.0) -> bool:
        """Attempt to consume *cost* tokens.

        Args:
            cost: Number of tokens to consume (default 1).

        Returns:
            ``True`` when the bucket had enough tokens; ``False`` otherwise (the
            bucket is not modified on failure).
        """
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    @property
    def available(self) -> float:
        """Current token count (after refill)."""
        self._refill()
        return self._tokens


class RateLimiter:
    """Layered token-bucket rate limiter (global ceiling + per-tool budgets)."""

    def __init__(
        self,
        global_rps: float = 10.0,
        tool_capacity: float = DEFAULT_TOOL_CAPACITY,
        heavy_tool_capacity: float = HEAVY_TOOL_CAPACITY,
        heavy_tools: frozenset[str] = HEAVY_TOOLS,
        clock: Callable[[], float] = time.monotonic,
        redis_url: str | None = None,
    ) -> None:
        """Initialise the layered rate limiter.

        Args:
            global_rps: Server-wide requests-per-second ceiling.
            tool_capacity: Burst budget for standard tools.
            heavy_tool_capacity: Burst budget for heavy tools.
            heavy_tools: Set of tool names treated as heavy.
            clock: Monotonic clock callable (injectable for tests).
            redis_url: Optional Redis URL for the global bucket backend.
        """
        self._global_rps = global_rps
        self._tool_capacity = tool_capacity
        self._heavy_tool_capacity = heavy_tool_capacity
        self._heavy_tools = heavy_tools
        self._clock = clock
        self._redis_url = redis_url

        # In-process global bucket (capacity = 2 × rps for burst headroom).
        self._global_bucket = _TokenBucket(
            capacity=max(global_rps * 2, 1.0),
            rate=global_rps,
            clock=clock,
        )
        self._tool_buckets: dict[str, _TokenBucket] = {}

        self._redis: Any = None
        if redis_url:
            self._redis = self._try_connect_redis(redis_url)

    @staticmethod
    def _try_connect_redis(url: str) -> Any:
        """Attempt to create a Redis client; return ``None`` on failure.

        Args:
            url: The Redis connection URL.

        Returns:
            A redis client, or ``None`` if the import/connection setup fails.
        """
        try:
            import redis as _redis

            return _redis.from_url(url, decode_responses=True)
        except Exception:  # noqa: BLE001
            return None

    def _redis_allow_global(self) -> bool:
        """Check the global rate limit via Redis INCR+EXPIRE (1-second window).

        Returns:
            ``True`` when within the per-second window or Redis is unavailable.
        """
        if self._redis is None:
            return True
        try:
            window_key = f"kgdb_mcp:ratelimit:global:{int(time.time())}"
            current = self._redis.incr(window_key)
            if current == 1:
                self._redis.expire(window_key, 2)
            return int(current) <= int(self._global_rps)
        except Exception:  # noqa: BLE001
            return True

    def _get_tool_bucket(self, tool_name: str) -> _TokenBucket:
        """Return (or lazily create) the per-tool bucket for *tool_name*.

        Args:
            tool_name: The MCP tool name.

        Returns:
            The bucket sized for a heavy or standard tool.
        """
        if tool_name not in self._tool_buckets:
            capacity = (
                self._heavy_tool_capacity
                if tool_name in self._heavy_tools
                else self._tool_capacity
            )
            self._tool_buckets[tool_name] = _TokenBucket(
                capacity=capacity,
                rate=capacity / 2.0,
                clock=self._clock,
            )
        return self._tool_buckets[tool_name]

    def allow(self, tool_name: str) -> bool:
        """Return whether this request is within the global and per-tool limits.

        Args:
            tool_name: The MCP tool name being invoked.

        Returns:
            ``True`` when allowed, ``False`` when it should be rejected with a
            ``temporarily_unavailable`` error.
        """
        if self._redis is not None:
            if not self._redis_allow_global():
                return False
        elif not self._global_bucket.consume():
            return False

        tool_bucket = self._get_tool_bucket(tool_name)
        return tool_bucket.consume()

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of current bucket states for observability.

        Returns:
            A dict with ``global_available`` and a per-tool ``tools`` map.
        """
        return {
            "global_available": round(self._global_bucket.available, 2),
            "tools": {
                name: round(bucket.available, 2)
                for name, bucket in self._tool_buckets.items()
            },
        }

    @classmethod
    def from_settings_params(
        cls,
        global_rps: float,
        redis_url: str | None = None,
    ) -> RateLimiter:
        """Construct a :class:`RateLimiter` from server settings parameters.

        Args:
            global_rps: Global requests-per-second ceiling from settings.
            redis_url: Optional Redis URL from settings.

        Returns:
            A configured :class:`RateLimiter` instance.
        """
        return cls(
            global_rps=global_rps,
            tool_capacity=DEFAULT_TOOL_CAPACITY,
            heavy_tool_capacity=HEAVY_TOOL_CAPACITY,
            redis_url=redis_url,
        )


# Module-level singleton — populated by build_app(); None until then.
_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter | None:
    """Return the module-level singleton limiter, or ``None`` if uninitialised."""
    return _limiter


def set_limiter(limiter: RateLimiter | None) -> None:
    """Set the module-level singleton limiter (called by ``build_app``).

    Args:
        limiter: The limiter to install, or ``None`` to clear it.
    """
    global _limiter  # noqa: PLW0603
    _limiter = limiter


def rate_limit_info_json() -> str:
    """Return a JSON string with current limiter stats (for /health or debug).

    Returns:
        A JSON string of the limiter snapshot, or a ``not_initialised`` marker.
    """
    lim = get_limiter()
    if lim is None:
        return json.dumps({"rate_limiter": "not_initialised"})
    return json.dumps({"rate_limiter": lim.stats()})
