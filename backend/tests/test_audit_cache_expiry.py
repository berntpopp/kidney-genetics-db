"""#296: promoting a DB cache entry to memory must keep the DB expiry."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text

import app.core.cache_service as cache_module
from app.core.cache_service import CacheService


@pytest.fixture
def cache(test_engine):
    ns = f"audit296-{uuid.uuid4().hex[:8]}"
    service = CacheService(db_session=object())  # truthy marker: L2 enabled
    yield service, ns
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM cache_entries WHERE namespace = :ns"), {"ns": ns})


def _persist(test_engine, service, ns, key, value, expires_at):
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO cache_entries (cache_key, namespace, data, expires_at) "
                "VALUES (:k, :ns, CAST(:d AS jsonb), :e)"
            ),
            {
                "k": service._generate_cache_key(key, ns),
                "ns": ns,
                "d": json.dumps(value),
                "e": expires_at,
            },
        )


def _advance_clock(seconds: float):
    real = datetime

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return real.now(tz) + timedelta(seconds=seconds)

    return patch.object(cache_module, "datetime", FakeDatetime)


@pytest.mark.asyncio
@pytest.mark.parametrize("remaining", [2, 30])  # near-expiry and short custom TTL
async def test_promoted_entry_keeps_db_expiry(test_engine, cache, remaining):
    service, ns = cache
    db_expiry = datetime.now(timezone.utc) + timedelta(seconds=remaining)
    _persist(test_engine, service, ns, "k", {"v": 1}, db_expiry)

    assert await service.get("k", ns) == {"v": 1}  # L2 hit -> promoted to memory
    promoted = service.memory_cache[service._generate_cache_key("k", ns)]
    assert promoted.expires_at == db_expiry

    service.db_session = None  # memory only from here on
    with _advance_clock(remaining + 1):
        assert await service.get("k", ns) is None


@pytest.mark.asyncio
async def test_promoted_entry_without_db_expiry_never_expires(test_engine, cache):
    service, ns = cache
    _persist(test_engine, service, ns, "k", {"v": 1}, None)

    assert await service.get("k", ns) == {"v": 1}
    service.db_session = None
    with _advance_clock(10 * 365 * 86400):
        assert await service.get("k", ns) == {"v": 1}
