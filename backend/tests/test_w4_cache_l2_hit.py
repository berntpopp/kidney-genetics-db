"""#363: an L2 cache hit is one statement on one session, off the event loop."""

import threading
import uuid

import pytest
from sqlalchemy import text

import app.core.cache_service as cache_module


@pytest.fixture
def cache(test_engine, monkeypatch):
    monkeypatch.setattr(cache_module, "cache_service", None)
    svc = cache_module.get_cache_service(object())  # any non-None marks L2 enabled
    ns = f"w4-{uuid.uuid4().hex[:8]}"
    yield svc, ns
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM cache_entries WHERE namespace = :ns"), {"ns": ns})


def _access_count(engine, key: str) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT access_count FROM cache_entries WHERE cache_key = :k"), {"k": key}
        ).scalar_one()


@pytest.mark.integration
async def test_l2_hit_is_one_statement_off_the_loop(test_engine, cache, monkeypatch):
    svc, ns = cache
    assert await svc.set("k", {"v": 1}, ns)
    key = svc._generate_cache_key("k", ns)
    before = _access_count(test_engine, key)
    svc.memory_cache.clear()

    threads: list[int] = []
    execute = svc._execute

    def spy(*args, **kwargs):
        threads.append(threading.get_ident())
        return execute(*args, **kwargs)

    monkeypatch.setattr(svc, "_execute", spy)
    assert await svc.get("k", ns) == {"v": 1}
    assert len(threads) == 1  # SELECT and access-stat UPDATE are one statement
    assert threads[0] != threading.get_ident()  # blocking I/O ran in a worker thread
    assert _access_count(test_engine, key) == before + 1
    assert svc.memory_cache[key].expires_at is not None  # DB expiry kept in L1

    # Expired entries are misses and are not touched.
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE cache_entries SET expires_at = NOW() - interval '1 s' WHERE cache_key = :k"
            ),
            {"k": key},
        )
    svc.memory_cache.clear()
    assert await svc.get("k", ns, default="miss") == "miss"
    assert _access_count(test_engine, key) == before + 1
