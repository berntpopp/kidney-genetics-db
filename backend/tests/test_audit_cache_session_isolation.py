"""#293: persistent cache I/O must never commit/roll back a caller's transaction."""

import threading
import uuid

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import sessionmaker

import app.core.cache_service as cache_module

BIZ = text(
    "INSERT INTO cache_entries (cache_key, namespace, data) VALUES (:k, :ns, CAST('{}' AS jsonb))"
)


@pytest.fixture
def ns(test_engine, monkeypatch):
    """Fresh singleton + unique namespace; committed rows removed afterwards."""
    monkeypatch.setattr(cache_module, "cache_service", None)
    namespace = f"audit293-{uuid.uuid4().hex[:8]}"
    yield namespace
    with test_engine.begin() as conn:
        conn.execute(
            text("DELETE FROM cache_entries WHERE namespace LIKE :p"), {"p": namespace + "%"}
        )


@pytest.fixture
def owners(test_engine):
    """Two independent caller sessions (A, B), each with a pending business write."""
    factory = sessionmaker(bind=test_engine)
    sessions = [factory(), factory()]
    yield sessions
    for s in sessions:
        s.rollback()
        s.close()


def _committed(engine, key: str) -> bool:
    with engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM cache_entries WHERE cache_key = :k"), {"k": key}
            ).first()
            is not None
        )


def _pending(session, key: str) -> bool:
    return (
        session.execute(
            text("SELECT 1 FROM cache_entries WHERE cache_key = :k"), {"k": key}
        ).first()
        is not None
    )


def _count_executes(session) -> list[int]:
    calls: list[int] = []
    event.listen(session, "do_orm_execute", lambda _ctx: calls.append(threading.get_ident()))
    return calls


@pytest.mark.asyncio
async def test_interleaved_owners_cannot_commit_or_roll_back_each_other(test_engine, ns, owners):
    a, b = owners
    a.execute(BIZ, {"k": f"{ns}-biz-a", "ns": ns + "-biz"})
    b.execute(BIZ, {"k": f"{ns}-biz-b", "ns": ns + "-biz"})
    calls_a, calls_b = _count_executes(a), _count_executes(b)

    cache_a = cache_module.get_cache_service(a)
    cache_module.get_cache_service(b)  # rebinding by another owner

    assert await cache_a.set("k", {"v": 1}, ns) is True  # write
    cache_a.memory_cache.clear()
    assert await cache_a.get("k", ns) == {"v": 1}  # L2 read + access-stat write
    # PostgreSQL rejects \u0000 in jsonb -> exercises the DB error/rollback path
    assert await cache_a.set("bad", {"v": "\u0000"}, ns) in (True, False)
    assert await cache_a.delete("k", ns) is True
    await cache_a.clear_namespace(ns)
    await cache_a.get_stats(ns)

    # The cache never executed on either caller's session.
    assert calls_a == [] and calls_b == []
    # Neither owner's business transaction was committed ...
    assert not _committed(test_engine, f"{ns}-biz-a")
    assert not _committed(test_engine, f"{ns}-biz-b")
    # ... nor rolled back: both pending writes are still visible to their owner.
    assert _pending(a, f"{ns}-biz-a")
    assert _pending(b, f"{ns}-biz-b")


@pytest.mark.asyncio
async def test_cache_persists_through_its_own_session(test_engine, ns, owners):
    a, _ = owners
    cache = cache_module.get_cache_service(a)
    await cache.set("k", {"v": 2}, ns)
    key = cache._generate_cache_key("k", ns)
    a.rollback()  # caller rollback must not discard the committed cache entry
    assert _committed(test_engine, key)


def test_sync_clear_from_worker_thread_does_not_use_caller_session(test_engine, ns, owners):
    a, _ = owners
    a.execute(BIZ, {"k": f"{ns}-biz-a", "ns": ns})
    calls = _count_executes(a)
    cache = cache_module.get_cache_service(a)

    worker = threading.Thread(target=cache.clear_namespace_sync, args=(ns,))
    worker.start()
    worker.join()

    assert calls == []
    assert not _committed(test_engine, f"{ns}-biz-a")
    assert _pending(a, f"{ns}-biz-a")
