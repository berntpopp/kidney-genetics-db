"""API rate limiting using SlowAPI with Redis backend.

Provides tiered rate limiting:
- Anonymous (IP-based): 60 req/min
- Authenticated (JWT): 300 req/min
- Admin: 1000 req/min (safety net)

Uses Redis DB 1 (separate from ARQ on DB 0).
Falls back to in-memory if Redis unavailable.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_real_ip(request: Request) -> str:
    """Get real client IP, respecting X-Forwarded-For behind reverse proxy."""
    forwarded: str | None = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the real client
        ip: str = forwarded.split(",")[0].strip()
        return ip
    result: str = get_remote_address(request)
    return result


def _get_rate_limit_key(request: Request) -> str:
    """Determine rate limit key: user ID if authenticated, else IP address."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.core.security import verify_token

            payload = verify_token(auth_header.split(" ", 1)[1], token_type="access")
            if payload and "sub" in payload:
                # Check for admin role — give higher limits
                role = payload.get("role", "")
                if role == "admin":
                    return f"admin:{payload['sub']}"
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return _get_real_ip(request)


def _build_redis_url() -> str:
    """Build Redis URL for rate limiting using separate DB."""
    base = settings.REDIS_URL
    # Replace DB number in URL
    if "/" in base.rsplit(":", 1)[-1]:
        # URL has a DB number, replace it
        return base.rsplit("/", 1)[0] + f"/{settings.REDIS_RATE_LIMIT_DB}"
    return f"{base}/{settings.REDIS_RATE_LIMIT_DB}"


def _get_storage_uri() -> str:
    """Get storage URI with Redis fallback to in-memory."""
    try:
        import redis

        r = redis.from_url(_build_redis_url())
        r.ping()
        uri = _build_redis_url()
        logger.sync_info("Rate limiter using Redis storage", uri=uri)
        return uri
    except Exception:
        logger.sync_warning("Redis unavailable for rate limiting, using in-memory storage")
        return "memory://"


limiter = Limiter(
    key_func=_get_rate_limit_key,
    storage_uri=_get_storage_uri(),
    default_limits=["60/minute"],
    headers_enabled=True,
)

# Limit strings for per-endpoint use
LIMIT_ANONYMOUS = "60/minute"
LIMIT_AUTHENTICATED = "300/minute"
LIMIT_ADMIN = "1000/minute"
LIMIT_AUTH_LOGIN = "5/minute"
LIMIT_AUTH_REGISTER = "3/minute"
LIMIT_GENE_LIST = "30/minute"
LIMIT_NETWORK = "10/minute"
LIMIT_STATISTICS = "30/minute"
LIMIT_PIPELINE = "5/hour"
LIMIT_CLIENT_LOGS = "30/minute"
