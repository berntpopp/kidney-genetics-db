"""
Cache decorator for FastAPI endpoints and functions.
Provides clean @cache syntax similar to fastapi-cache.
"""

import functools
import hashlib
import inspect
import json
from collections.abc import Callable

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger

logger = get_logger(__name__)


def cache(namespace: str = "default", ttl: int | None = None, key_builder: Callable | None = None):
    """
    Cache decorator for async functions.

    Args:
        namespace: Cache namespace for organization
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function

    Usage:
        @cache(namespace="annotations", ttl=3600)
        async def get_gene_data(gene_id: int):
            return expensive_operation(gene_id)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get db session from kwargs if available
            db_session = kwargs.get("db")
            cache_service = get_cache_service(db_session)

            # Build cache key
            if key_builder:
                cache_key = key_builder(func, *args, **kwargs)
            else:
                # Default key builder using function name and args
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                # Create key from function name and arguments
                key_parts = [func.__name__]
                for name, value in bound.arguments.items():
                    if name not in ("self", "cls", "db"):  # Skip common non-cache params
                        key_parts.append(f"{name}:{value}")

                raw_key = ":".join(key_parts)
                cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            # Try to get from cache
            cached_value = await cache_service.get(cache_key, namespace)
            if cached_value is not None:
                logger.sync_debug(f"Cache hit for {func.__name__}", key=cache_key)
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            await cache_service.set(cache_key, result, namespace, ttl)
            logger.sync_debug(f"Cached result for {func.__name__}", key=cache_key)

            return result

        return wrapper

    return decorator


def cache_key_builder(
    func: Callable, namespace: str = "", request=None, response=None, *args, **kwargs
) -> str:
    """
    Build a cache key based on function and request parameters.

    This is a more sophisticated key builder that can be used with FastAPI requests.

    Args:
        func: The function being cached
        namespace: Optional namespace prefix
        request: FastAPI Request object
        response: FastAPI Response object
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Cache key string
    """
    from fastapi import Request

    key_parts = [namespace] if namespace else []

    # Add function name
    key_parts.append(func.__name__)

    # If we have a request, use URL and query params
    if request and isinstance(request, Request):
        key_parts.append(request.method.lower())
        key_parts.append(request.url.path)
        if request.query_params:
            key_parts.append(repr(sorted(request.query_params.items())))

    # Otherwise use function arguments
    else:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if name not in ("self", "cls", "db", "request", "response"):
                # Convert complex types to string representation
                if isinstance(value, dict | list):
                    value_str = json.dumps(value, sort_keys=True, default=str)
                else:
                    value_str = str(value)
                key_parts.append(f"{name}:{value_str}")

    # Create hash of the key for consistent length
    raw_key = ":".join(key_parts)
    return hashlib.sha256(raw_key.encode()).hexdigest()
