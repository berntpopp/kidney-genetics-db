# Codebase Review Remediation — Batch 2: High Priority Performance & Auth

> **Status: 90% COMPLETE** — 9/10 tasks implemented. Task 6b (token rotation wiring) deferred — superseded by HttpOnly cookie auth (S6). Branch: `fix/codebase-review-batch-1-critical` (2026-03-14)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize statistics queries, cache performance, auth security (opaque refresh tokens), Pydantic v2 migration, and exception standardization.

**Architecture:** Five independent sub-batches with zero file overlap, designed for parallel execution in isolated worktrees. Depends on Batch 1 being merged first.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Pydantic v2, cachetools, threading.Lock, SHA-256

**Spec:** `docs/superpowers/specs/2026-03-13-codebase-review-remediation-design.md` (Batch 2 section)

**Prerequisite:** Batch 1 plan completed and merged (`docs/superpowers/plans/2026-03-13-codebase-review-batch-1-critical.md`)

---

## Chunk 1: Sub-batch 2A — Statistics Optimization (Tasks 1–2)

### Task 1: Replace N+1 source overlap query with bitmask approach

**Files:**
- Modify: `backend/app/crud/statistics.py:88-155`
- Test: `backend/tests/test_statistics_overlap.py` (create)

**Context:** Current implementation at lines 88-152 does:
1. Fetches all gene IDs per source via `array_agg` (line 93)
2. Iterates through `combinations()` in Python (lines 122-152)
3. For EACH non-empty intersection, runs a separate DB query to resolve gene symbols (lines 136-144)
This is O(2^n) DB calls — 1023 queries for 10 sources.

- [x] **Step 1: Write failing test for bitmask approach**

Create `backend/tests/test_statistics_overlap.py`:

```python
"""Tests for statistics source overlap computation."""

import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
class TestSourceOverlapBitmask:
    """Verify source overlap uses single-query bitmask approach."""

    def test_source_overlap_does_not_use_combinations(self):
        """Verify itertools.combinations is no longer used in statistics.py."""
        import inspect
        from app.crud import statistics

        source = inspect.getsource(statistics)
        assert "from itertools import combinations" not in source
        assert "combinations(" not in source

    def test_source_overlap_returns_expected_structure(self, db_session):
        """Verify the overlap endpoint returns sets + intersections."""
        from app.crud.statistics import get_source_overlap

        result = get_source_overlap(db_session)
        assert "sets" in result
        assert "intersections" in result
        assert "summary" in result
        assert isinstance(result["sets"], list)
        assert isinstance(result["intersections"], list)
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_statistics_overlap.py::TestSourceOverlapBitmask::test_source_overlap_does_not_use_combinations -v`
Expected: FAIL — `combinations` is still used

- [x] **Step 3: Rewrite source overlap with bitmask SQL**

In `backend/app/crud/statistics.py`, replace the overlap computation (lines ~88-155). The new approach:

1. Single SQL query assigns a bitmask per gene based on which sources it appears in
2. Group by bitmask to get counts
3. Decode bitmasks in Python

Replace the content from the source query through the intersection computation with:

```python
            # Single-query bitmask approach: assign a power-of-2 per source,
            # sum per gene, group by bitmask. O(1) DB queries instead of O(2^n).

            # Step 1: Get all source names for bitmask mapping
            source_names_result = db.execute(
                text(f"""
                    SELECT DISTINCT gene_evidence.source_name
                    FROM gene_evidence
                    {join_clause}
                    {where_clause}
                    ORDER BY gene_evidence.source_name
                """),
                params,
            ).fetchall()
            source_names = [row[0] for row in source_names_result]

            if not source_names:
                return {"sets": [], "intersections": [], "summary": {"total_unique_genes": 0}}

            # Build CASE expression for bitmask
            case_parts = []
            for i, name in enumerate(source_names):
                case_parts.append(f"WHEN gene_evidence.source_name = :src_{i} THEN {1 << i}")
            case_expr = " ".join(case_parts)

            source_params = {f"src_{i}": name for i, name in enumerate(source_names)}
            all_params = {**params, **source_params}

            # Step 2: Single query — bitmask per gene, grouped
            bitmask_query = f"""
                WITH gene_bitmasks AS (
                    SELECT
                        gene_evidence.gene_id,
                        SUM(DISTINCT CASE {case_expr} ELSE 0 END) AS source_bitmask
                    FROM gene_evidence
                    {join_clause}
                    {where_clause}
                    GROUP BY gene_evidence.gene_id
                ),
                bitmask_groups AS (
                    SELECT
                        source_bitmask,
                        COUNT(*) AS gene_count,
                        array_agg(gene_id ORDER BY gene_id) AS gene_ids
                    FROM gene_bitmasks
                    GROUP BY source_bitmask
                )
                SELECT
                    bg.source_bitmask,
                    bg.gene_count,
                    array_agg(g.approved_symbol ORDER BY g.approved_symbol) AS gene_symbols
                FROM bitmask_groups bg
                JOIN LATERAL unnest(bg.gene_ids) AS gid ON true
                JOIN genes g ON g.id = gid
                GROUP BY bg.source_bitmask, bg.gene_count
                ORDER BY bg.gene_count DESC
            """

            bitmask_results = db.execute(text(bitmask_query), all_params).fetchall()

            # Step 3: Decode bitmasks into source combinations
            # Build sets (per-source counts)
            source_gene_counts: dict[str, int] = {name: 0 for name in source_names}
            intersections: list[IntersectionDict] = []

            for row in bitmask_results:
                bitmask = int(row[0])
                gene_count = row[1]
                gene_symbols = list(row[2]) if row[2] else []

                # Decode which sources this bitmask represents
                combo_sources = [
                    source_names[i]
                    for i in range(len(source_names))
                    if bitmask & (1 << i)
                ]

                # Accumulate per-source totals
                for src in combo_sources:
                    source_gene_counts[src] += gene_count

                intersections.append({
                    "sets": combo_sources,
                    "size": gene_count,
                    "genes": gene_symbols,
                })

            # Build sets list
            sets = [
                {"name": name, "size": source_gene_counts[name]}
                for name in source_names
            ]

            # Sort intersections by size descending
            intersections.sort(key=lambda x: x["size"], reverse=True)
```

Also update the summary statistics section below to use `source_gene_counts` instead of separate queries where possible.

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_statistics_overlap.py -v`
Expected: PASS

- [x] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/crud/statistics.py backend/tests/test_statistics_overlap.py
git commit -m "perf(statistics): replace O(2^n) source overlap with single-query bitmask (P2, P5, P7)"
```

---

## Chunk 2: Sub-batch 2B — Cache Performance (Tasks 2–4)

### Task 2: Add thread-safe locking to CacheService L1 cache

**Files:**
- Modify: `backend/app/core/cache_service.py:112-119`
- Test: `backend/tests/test_cache_thread_safety.py` (create)

- [x] **Step 1: Write failing test for thread safety**

Create `backend/tests/test_cache_thread_safety.py`:

```python
"""Tests for cache service thread safety."""

import threading
import pytest


@pytest.mark.unit
class TestCacheThreadSafety:
    """Verify CacheService uses thread-safe access patterns."""

    def test_cache_service_has_lock(self):
        """CacheService must have a threading.Lock for L1 cache."""
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        assert hasattr(cache, "_memory_lock")
        assert isinstance(cache._memory_lock, type(threading.Lock()))

    def test_concurrent_cache_access_no_race(self):
        """Verify concurrent access doesn't corrupt cache."""
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        errors = []

        def writer(n):
            try:
                for i in range(100):
                    cache.memory_cache[f"key_{n}_{i}"] = f"value_{n}_{i}"
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_cache_thread_safety.py::TestCacheThreadSafety::test_cache_service_has_lock -v`
Expected: FAIL — no `_memory_lock` attribute

- [x] **Step 3: Add threading.Lock to CacheService**

In `backend/app/core/cache_service.py`, in `__init__` (around line 112):

```python
import threading

# In __init__:
        # L1 Cache: In-memory LRU cache with thread-safe access
        self._memory_lock = threading.Lock()
        self.memory_cache: cachetools.LRUCache = cachetools.LRUCache(
            maxsize=settings.CACHE_MAX_MEMORY_SIZE
        )
```

Then wrap all `self.memory_cache` reads/writes with `with self._memory_lock:`. Search for all direct accesses to `self.memory_cache` in the file and wrap them.

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_cache_thread_safety.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/core/cache_service.py backend/tests/test_cache_thread_safety.py
git commit -m "fix(cache): add threading.Lock to CacheService L1 cache (M10)"
```

### Task 3: Remove manual TTL cache from genes.py

**Files:**
- Modify: `backend/app/api/endpoints/genes.py:38-148`
- Test: Verify through existing endpoint tests

**Context:** Lines 39-148 contain 3 module-level manual cache dicts (`_metadata_cache`, `_hpo_classifications_cache`, `_gene_ids_cache`) with custom TTL logic. These should be replaced with `CacheService` calls.

- [x] **Step 1: Write test verifying no module-level cache dicts**

Add to `backend/tests/test_cache_thread_safety.py`:

```python
@pytest.mark.unit
class TestGenesEndpointCache:
    """Verify genes endpoint uses CacheService, not manual cache."""

    def test_no_module_level_cache_dicts(self):
        """Module-level cache dicts should be removed from genes.py."""
        import inspect
        from app.api.endpoints import genes

        source = inspect.getsource(genes)
        assert "_metadata_cache: dict" not in source
        assert "_hpo_classifications_cache: dict" not in source
        assert "_gene_ids_cache: dict" not in source
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_cache_thread_safety.py::TestGenesEndpointCache -v`
Expected: FAIL — module-level caches still present

- [x] **Step 3: Replace manual caches with CacheService**

In `backend/app/api/endpoints/genes.py`:

1. Remove lines 39-48 (the three cache dicts and TTLs)
2. Remove `get_filter_metadata()` function (lines 54-138) — replace with CacheService-based version
3. Remove `invalidate_metadata_cache()` (lines 141-148) — replace with cache namespace invalidation
4. Remove `clear_gene_ids_cache()` (lines 151-159) — replace with cache namespace invalidation

Replace with:

```python
from app.core.cache_service import get_cache_service

METADATA_CACHE_KEY = "filter_metadata"
METADATA_CACHE_NAMESPACE = "genes_metadata"
METADATA_CACHE_TTL = 300  # 5 minutes

HPO_CACHE_NAMESPACE = "hpo_classifications"
HPO_CACHE_TTL = 3600  # 1 hour

GENE_IDS_CACHE_NAMESPACE = "gene_ids"
GENE_IDS_CACHE_TTL = 3600  # 1 hour


async def get_filter_metadata(db: Session) -> dict[str, Any]:
    """Get filter metadata with CacheService caching."""
    cache = get_cache_service(db)
    cached = await cache.get(METADATA_CACHE_KEY, namespace=METADATA_CACHE_NAMESPACE)
    if cached is not None:
        return cached

    # Fetch fresh data (same logic as before)
    max_count_result = db.execute(text("SELECT MAX(evidence_count) FROM gene_scores")).scalar()
    sources_result = db.execute(
        text("SELECT DISTINCT source_name FROM gene_evidence ORDER BY source_name")
    ).fetchall()

    tier_distribution_query = text("""
        SELECT evidence_group, evidence_tier, COUNT(*) as gene_count
        FROM gene_scores WHERE percentage_score > 0
        GROUP BY evidence_group, evidence_tier
        ORDER BY
            CASE evidence_group
                WHEN 'well_supported' THEN 1
                WHEN 'emerging_evidence' THEN 2
                ELSE 3
            END,
            MIN(percentage_score) DESC
    """)
    tier_results = db.execute(tier_distribution_query).fetchall()

    tier_meta: dict[str, dict[str, int]] = {"well_supported": {}, "emerging_evidence": {}}
    for row in tier_results:
        group = row.evidence_group
        tier = row.evidence_tier
        count = row.gene_count
        if group in tier_meta:
            tier_meta[group][tier] = count

    tier_meta["well_supported"]["total"] = sum(tier_meta["well_supported"].values())
    tier_meta["emerging_evidence"]["total"] = sum(tier_meta["emerging_evidence"].values())

    metadata = {
        "max_count": max_count_result or 0,
        "sources": [row[0] for row in sources_result],
        "tier_distribution": tier_meta,
    }

    await cache.set(METADATA_CACHE_KEY, metadata, namespace=METADATA_CACHE_NAMESPACE, ttl=METADATA_CACHE_TTL)
    return metadata


async def invalidate_metadata_cache(db: Session) -> None:
    """Invalidate metadata cache via CacheService."""
    cache = get_cache_service(db)
    await cache.invalidate_namespace(METADATA_CACHE_NAMESPACE)
```

**Important — call site migration**: `get_filter_metadata` is now `async`. Grep for all callers:

```bash
cd backend && grep -rn "get_filter_metadata\|invalidate_metadata_cache\|clear_gene_ids_cache" app/ --include="*.py"
```

Each caller that was previously sync must be updated to `await`. The main call site is in the gene list endpoint in `genes.py` itself — convert to `await get_filter_metadata(db)`. Any sync callers that cannot be made async should use `run_in_threadpool` or `asyncio.run()`.

- [x] **Step 4: Update all call sites to use await**

Fix every caller found in the grep above. The most common pattern:
```python
# Before:
metadata = get_filter_metadata(db)
# After:
metadata = await get_filter_metadata(db)
```

- [x] **Step 5: Run tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/genes.py backend/tests/test_cache_thread_safety.py
git commit -m "refactor(cache): replace manual TTL caches in genes.py with CacheService (P8, M10)"
```

### Task 4: Batch cache stats persistence

**Files:**
- Modify: `backend/app/core/cache_service.py` (stats writing pattern)

- [x] **Step 1: Write test for batched stats**

Add to `backend/tests/test_cache_thread_safety.py`:

```python
@pytest.mark.unit
class TestCacheStatsBatching:
    """Verify cache stats are batched, not written per-operation."""

    def test_stats_have_batch_counter(self):
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        assert hasattr(cache.stats, "operations_since_persist")
        assert hasattr(cache.stats, "PERSIST_THRESHOLD")
```

- [x] **Step 2: Add batched persistence to CacheStats**

In `backend/app/core/cache_service.py`, modify the `CacheStats` class to track operations and persist every 100 ops or 60 seconds:

```python
import time
import threading

class CacheStats:
    PERSIST_THRESHOLD = 100
    PERSIST_INTERVAL_SECONDS = 60

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.operations_since_persist = 0
        self._last_persist_time = time.monotonic()
        self._lock = threading.Lock()

    def record_hit(self):
        with self._lock:
            self.hits += 1
            self.operations_since_persist += 1

    def record_miss(self):
        with self._lock:
            self.misses += 1
            self.operations_since_persist += 1

    def should_persist(self) -> bool:
        with self._lock:
            if self.operations_since_persist >= self.PERSIST_THRESHOLD:
                return True
            if time.monotonic() - self._last_persist_time >= self.PERSIST_INTERVAL_SECONDS:
                return True
            return False

    def mark_persisted(self):
        with self._lock:
            self.operations_since_persist = 0
            self._last_persist_time = time.monotonic()
```

Then modify cache get/set methods to call `should_persist()` and write to DB only when threshold is met.

- [x] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_cache_thread_safety.py -v`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add backend/app/core/cache_service.py backend/tests/test_cache_thread_safety.py
git commit -m "perf(cache): batch cache stats persistence to reduce DB writes (P4)"
```

---

## Chunk 3: Sub-batch 2C — Auth Security (Tasks 5–7)

### Task 5: Create RefreshToken model and migration

**Files:**
- Create: `backend/app/models/refresh_token.py`
- Modify: `backend/app/models/__init__.py`
- Create: New Alembic migration
- Test: `backend/tests/test_refresh_token.py` (create)

- [x] **Step 1: Write failing test for RefreshToken model**

Create `backend/tests/test_refresh_token.py`:

```python
"""Tests for opaque refresh token system."""

import pytest
from datetime import datetime, timezone


@pytest.mark.unit
class TestRefreshTokenModel:
    """Verify RefreshToken model structure."""

    def test_model_exists(self):
        from app.models.refresh_token import RefreshToken
        assert RefreshToken.__tablename__ == "refresh_tokens"

    def test_has_required_columns(self):
        from app.models.refresh_token import RefreshToken
        columns = {c.name for c in RefreshToken.__table__.columns}
        assert "id" in columns
        assert "token_hash" in columns
        assert "family_id" in columns
        assert "user_id" in columns
        assert "is_revoked" in columns
        assert "created_at" in columns
        assert "expires_at" in columns
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_refresh_token.py -v`
Expected: FAIL — module does not exist

- [x] **Step 3: Create RefreshToken model**

Create `backend/app/models/refresh_token.py`:

```python
"""Opaque refresh token model with SHA-256 hashing and family-based revocation."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class RefreshToken(Base, TimestampMixin):
    """Refresh token stored as SHA-256 hash with family-based revocation."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    family_id = Column(String(36), nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
```

- [x] **Step 4: Update models/__init__.py**

Add import:
```python
from app.models.refresh_token import RefreshToken  # noqa: F401
```

- [x] **Step 5: Add relationship to User model**

In `backend/app/models/user.py`, add:
```python
refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
```

- [x] **Step 6: Generate and run migration**

```bash
cd backend && uv run alembic revision --autogenerate -m "add refresh_tokens table"
cd backend && uv run alembic upgrade head
```

- [x] **Step 7: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_refresh_token.py -v`
Expected: PASS

- [x] **Step 8: Commit**

```bash
git add backend/app/models/refresh_token.py backend/app/models/__init__.py \
  backend/app/models/user.py backend/alembic/versions/ backend/tests/test_refresh_token.py
git commit -m "feat(auth): add RefreshToken model with SHA-256 hashing and family revocation (S5)"
```

### Task 6: Implement opaque refresh token functions in security.py

**Files:**
- Modify: `backend/app/core/security.py`
- Test: `backend/tests/test_refresh_token.py` (extend)

- [x] **Step 1: Write failing test for token creation**

Add to `backend/tests/test_refresh_token.py`:

```python
@pytest.mark.unit
class TestOpaqueRefreshToken:
    """Verify opaque refresh token creation and hashing."""

    def test_create_opaque_refresh_token(self):
        from app.core.security import create_opaque_refresh_token

        raw_token, token_hash = create_opaque_refresh_token()
        assert isinstance(raw_token, str)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA-256 hex

    def test_token_hash_is_deterministic(self):
        from app.core.security import hash_token

        token = "test_token_value"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_different_tokens_different_hashes(self):
        from app.core.security import create_opaque_refresh_token

        _, hash1 = create_opaque_refresh_token()
        _, hash2 = create_opaque_refresh_token()
        assert hash1 != hash2
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_refresh_token.py::TestOpaqueRefreshToken -v`
Expected: FAIL — functions don't exist

- [x] **Step 3: Add opaque token functions to security.py**

Add to `backend/app/core/security.py`:

```python
import hashlib
import secrets


def hash_token(token: str) -> str:
    """SHA-256 hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_opaque_refresh_token() -> tuple[str, str]:
    """Create an opaque refresh token.

    Returns:
        Tuple of (raw_token, sha256_hash).
        The raw_token is sent to the client; the hash is stored in the DB.
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_refresh_token.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_refresh_token.py
git commit -m "feat(auth): add opaque refresh token creation and SHA-256 hashing (S5)"
```

### Task 6b: Wire opaque refresh tokens into auth endpoints (rotation + reuse detection)

**Files:**
- Modify: `backend/app/api/endpoints/auth.py` (login, refresh, logout)
- Test: `backend/tests/test_refresh_token.py` (extend)

**Context:** Tasks 5-6 created the `RefreshToken` model and hash functions but did not wire them into the auth flow. This task implements token rotation on every use and family-based reuse detection per S5.

- [ ] **Step 1: Write failing test for token rotation** **SKIPPED:** Token rotation not wired into auth flow — superseded by HttpOnly cookie strategy (S6, Batch 3).

Add to `backend/tests/test_refresh_token.py`:

```python
@pytest.mark.integration
class TestTokenRotation:
    """Verify refresh token rotation and family-based reuse detection."""

    def test_refresh_returns_new_token(self, db_session):
        """Refreshing a token should return a new access token and rotate the refresh token."""
        from app.core.security import create_opaque_refresh_token, hash_token
        from app.models.refresh_token import RefreshToken
        from datetime import datetime, timezone, timedelta

        # Create initial token in DB
        raw_token, token_hash = create_opaque_refresh_token()
        rt = RefreshToken(
            token_hash=token_hash,
            family_id="test-family",
            user_id=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(rt)
        db_session.commit()

        # The old token should be revokable
        assert not rt.is_revoked

    def test_reused_token_revokes_family(self, db_session):
        """Presenting a revoked token should invalidate the entire family."""
        from app.models.refresh_token import RefreshToken
        from datetime import datetime, timezone, timedelta

        family_id = "reuse-test-family"
        # Create two tokens in same family, first is revoked
        rt1 = RefreshToken(
            token_hash="hash1",
            family_id=family_id,
            user_id=1,
            is_revoked=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        rt2 = RefreshToken(
            token_hash="hash2",
            family_id=family_id,
            user_id=1,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add_all([rt1, rt2])
        db_session.commit()

        # Simulate reuse detection: revoke all in family
        db_session.query(RefreshToken).filter(
            RefreshToken.family_id == family_id
        ).update({"is_revoked": True})
        db_session.commit()

        # Both should be revoked
        assert db_session.query(RefreshToken).filter(
            RefreshToken.family_id == family_id,
            RefreshToken.is_revoked == False,
        ).count() == 0
```

- [ ] **Step 2: Implement token rotation in auth.py login endpoint** **SKIPPED:** Token rotation not wired into auth flow — superseded by HttpOnly cookie strategy (S6, Batch 3).

In the login endpoint, after generating the JWT access token, also create an opaque refresh token and store its hash:

```python
from app.core.security import create_opaque_refresh_token, hash_token
from app.models.refresh_token import RefreshToken
import uuid

# In login endpoint, after authentication succeeds:
    raw_refresh, refresh_hash = create_opaque_refresh_token()
    family_id = str(uuid.uuid4())
    rt = RefreshToken(
        token_hash=refresh_hash,
        family_id=family_id,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(rt)
    db.commit()

    return {"access_token": access_token, "refresh_token": raw_refresh, "token_type": "bearer"}
```

- [ ] **Step 3: Implement token rotation in refresh endpoint** **SKIPPED:** Token rotation not wired into auth flow — superseded by HttpOnly cookie strategy (S6, Batch 3).

In the refresh endpoint:

```python
@router.post("/refresh")
async def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)

    # Look up the token
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
    ).first()

    if not stored_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # REUSE DETECTION: if token is revoked, invalidate entire family
    if stored_token.is_revoked:
        db.query(RefreshToken).filter(
            RefreshToken.family_id == stored_token.family_id
        ).update({"is_revoked": True})
        db.commit()
        raise HTTPException(status_code=401, detail="Token reuse detected — family revoked")

    # Check expiration
    if stored_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke old token
    stored_token.is_revoked = True

    # Create new token in same family
    new_raw, new_hash = create_opaque_refresh_token()
    new_rt = RefreshToken(
        token_hash=new_hash,
        family_id=stored_token.family_id,
        user_id=stored_token.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_rt)
    db.commit()

    # Create new access token
    access_token = create_access_token(subject=str(stored_token.user_id), ...)

    return {"access_token": access_token, "refresh_token": new_raw, "token_type": "bearer"}
```

- [ ] **Step 4: Run tests** **SKIPPED:** Token rotation not wired into auth flow — superseded by HttpOnly cookie strategy (S6, Batch 3).

Run: `cd backend && uv run pytest tests/test_refresh_token.py -v`
Expected: PASS

- [ ] **Step 5: Commit** **SKIPPED:** Token rotation not wired into auth flow — superseded by HttpOnly cookie strategy (S6, Batch 3).

```bash
git add backend/app/api/endpoints/auth.py backend/tests/test_refresh_token.py
git commit -m "feat(auth): implement opaque token rotation with family-based reuse detection (S5)"
```

### Task 7: Fix password reset logging and add rate limit

**Files:**
- Modify: `backend/app/api/endpoints/auth.py:270-274`
- Test: `backend/tests/test_auth_security.py` (create)

- [x] **Step 1: Write test for password reset security**

Create `backend/tests/test_auth_security.py`:

```python
"""Tests for auth security improvements."""

import pytest
import inspect


@pytest.mark.unit
class TestPasswordResetSecurity:
    """Verify password reset does not leak tokens."""

    def test_no_token_in_log(self):
        """Reset token must not appear in log messages."""
        from app.api.endpoints import auth

        source = inspect.getsource(auth.forgot_password)
        assert "token=reset_token" not in source
        assert "token=" not in source.split("logger")[1] if "logger" in source else True

    def test_forgot_password_has_rate_limit(self):
        """forgot_password must have rate limiting."""
        from app.api.endpoints import auth

        source = inspect.getsource(auth.forgot_password)
        # The decorator should be on the function
        # Check the full module source for the rate limit decorator near forgot_password
        module_source = inspect.getsource(auth)
        # Find forgot_password definition and check preceding lines
        idx = module_source.index("async def forgot_password")
        preceding = module_source[max(0, idx - 200):idx]
        assert "limiter.limit" in preceding
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_auth_security.py -v`
Expected: FAIL — token is still logged, no rate limit on forgot_password

- [x] **Step 3: Fix auth.py**

In `backend/app/api/endpoints/auth.py`:

**Remove token logging** (lines 270-274):
```python
# Before:
        # TODO: Send email with reset token
        # For now, log the token (remove in production!)
        await logger.info(
            "Password reset requested", email=request.email, token=reset_token[:8] + "..."
        )

# After:
        # NOTE: Email service integration is a separate feature.
        # Reset token is stored in DB; email delivery TBD.
        await logger.info("Password reset requested", email=request.email)
```

**Add rate limit to forgot_password** — add decorator and rename body parameter (around line 252):

The current signature is `async def forgot_password(request: PasswordReset, ...)`. The `@limiter.limit` decorator requires a Starlette `Request` as the first parameter. Rename the Pydantic body from `request` to `body` to avoid the name collision:

```python
@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, body: PasswordReset, db: Session = Depends(get_db)) -> dict[str, str]:
```

**Also update all references** to `request.email` inside the function body → `body.email`:
```python
# Before:
    result = db.execute(select(User).where(User.email == request.email))
    await logger.info("Password reset requested", email=request.email)
# After:
    result = db.execute(select(User).where(User.email == body.email))
    await logger.info("Password reset requested", email=body.email)
```

Add import at top of file if not already present: `from starlette.requests import Request`

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_auth_security.py -v`
Expected: PASS

- [x] **Step 5: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/api/endpoints/auth.py backend/tests/test_auth_security.py
git commit -m "fix(auth): remove token logging and add rate limit on password reset (S8, S9)"
```

---

## Chunk 4: Sub-batch 2D — Pydantic v2 Migration (Task 8)

### Task 8: Replace class Config with model_config = ConfigDict

**Files:**
- Modify: `backend/app/schemas/gene.py:40-41,84-85`
- Modify: `backend/app/schemas/releases.py:67-68`
- Modify: `backend/app/schemas/gene_staging.py:35-36,53-54`
- Modify: `backend/app/schemas/auth.py:69-70`
- Test: `backend/tests/test_pydantic_v2.py` (create)

- [x] **Step 1: Write failing test**

Create `backend/tests/test_pydantic_v2.py`:

```python
"""Tests for Pydantic v2 compliance."""

import pytest
import ast
import pathlib


@pytest.mark.unit
class TestPydanticV2Config:
    """Verify no deprecated class Config patterns remain."""

    SCHEMA_FILES = [
        "app/schemas/gene.py",
        "app/schemas/releases.py",
        "app/schemas/gene_staging.py",
        "app/schemas/auth.py",
    ]

    def test_no_class_config_in_schemas(self):
        """No schema file should have 'class Config:' pattern."""
        base = pathlib.Path("app/schemas")
        for schema_file in base.glob("*.py"):
            source = schema_file.read_text()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "Config":
                    # Check if parent is a Pydantic model
                    pytest.fail(
                        f"Found deprecated 'class Config:' in {schema_file.name}. "
                        "Use 'model_config = ConfigDict(...)' instead."
                    )

    def test_model_config_used(self):
        """Verify model_config = ConfigDict is used."""
        for rel_path in self.SCHEMA_FILES:
            source = pathlib.Path(rel_path).read_text()
            if "from_attributes" in source:
                assert "model_config" in source, (
                    f"{rel_path} uses from_attributes but not model_config"
                )
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pydantic_v2.py -v`
Expected: FAIL — `class Config:` still present in 4 files

- [x] **Step 3: Replace in gene.py (2 occurrences)**

In `backend/app/schemas/gene.py`:

Add at top: `from pydantic import ConfigDict` (if not already imported)

Line 40-41 (in GeneInDB):
```python
# Before:
    class Config:
        from_attributes = True
# After:
    model_config = ConfigDict(from_attributes=True)
```

Line 84-85 (in GeneCurationSummary):
```python
# Before:
    class Config:
        from_attributes = True
# After:
    model_config = ConfigDict(from_attributes=True)
```

- [x] **Step 4: Replace in releases.py (1 occurrence)**

In `backend/app/schemas/releases.py`, line 67-68:

Add import: `from pydantic import ConfigDict`

```python
# Before:
    class Config:
        from_attributes = True  # Allows conversion from SQLAlchemy models
# After:
    model_config = ConfigDict(from_attributes=True)
```

- [x] **Step 5: Replace in gene_staging.py (2 occurrences)**

In `backend/app/schemas/gene_staging.py`, lines 35-36 and 53-54:

Add import: `from pydantic import ConfigDict`

Both locations:
```python
# Before:
    class Config:
        from_attributes = True
# After:
    model_config = ConfigDict(from_attributes=True)
```

- [x] **Step 6: Replace in auth.py (1 occurrence)**

In `backend/app/schemas/auth.py`, line 69-70:

Add import: `from pydantic import ConfigDict`

```python
# Before:
    class Config:
        from_attributes = True
# After:
    model_config = ConfigDict(from_attributes=True)
```

- [x] **Step 7: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_pydantic_v2.py -v`
Expected: PASS

- [x] **Step 8: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS — schema serialization still works

- [x] **Step 9: Commit**

```bash
git add backend/app/schemas/gene.py backend/app/schemas/releases.py \
  backend/app/schemas/gene_staging.py backend/app/schemas/auth.py \
  backend/tests/test_pydantic_v2.py
git commit -m "refactor(schemas): replace class Config with model_config = ConfigDict (B1)"
```

---

## Chunk 5: Sub-batch 2E — Exception Standardization (Tasks 9–10)

### Task 9: Register global exception handlers in main.py

**Files:**
- Modify: `backend/app/main.py` (add exception handlers)
- Test: `backend/tests/test_exception_handlers.py` (create)

**Context:** `backend/app/core/exceptions.py` already has a rich hierarchy (13 exception classes). We need to map them to HTTP responses via global exception handlers.

- [x] **Step 1: Write failing test**

Create `backend/tests/test_exception_handlers.py`:

```python
"""Tests for global exception handler registration."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestExceptionHandlers:
    """Verify domain exceptions produce correct HTTP responses."""

    def test_gene_not_found_returns_404(self):
        from app.main import app
        from app.core.exceptions import GeneNotFoundError

        @app.get("/test-gene-not-found")
        async def raise_gene_not_found():
            raise GeneNotFoundError("TEST123")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-gene-not-found")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data or "detail" in data

    def test_authentication_error_returns_401(self):
        from app.main import app
        from app.core.exceptions import AuthenticationError

        @app.get("/test-auth-error")
        async def raise_auth_error():
            raise AuthenticationError("Invalid credentials")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-auth-error")
        assert response.status_code == 401

    def test_permission_denied_returns_403(self):
        from app.main import app
        from app.core.exceptions import PermissionDeniedError

        @app.get("/test-perm-error")
        async def raise_perm_error():
            raise PermissionDeniedError("admin", "test_operation")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-perm-error")
        assert response.status_code == 403
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_exception_handlers.py -v`
Expected: FAIL — domain exceptions not caught, result in 500

- [x] **Step 3: Add exception handlers to main.py**

In `backend/app/main.py`, after the `register_error_handlers(app)` line (line 165), add:

```python
import uuid
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    KidneyGeneticsException,
    GeneNotFoundError,
    ValidationError as DomainValidationError,
    AuthenticationError,
    PermissionDeniedError,
    ResourceConflictError,
    RateLimitExceededError,
)


@app.exception_handler(GeneNotFoundError)
async def gene_not_found_handler(request: Request, exc: GeneNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": {"type": "not_found", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )


@app.exception_handler(DomainValidationError)
async def domain_validation_handler(request: Request, exc: DomainValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {"type": "validation_error", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={
            "error": {"type": "authentication_error", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=403,
        content={
            "error": {"type": "permission_denied", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )


@app.exception_handler(ResourceConflictError)
async def resource_conflict_handler(request: Request, exc: ResourceConflictError):
    return JSONResponse(
        status_code=409,
        content={
            "error": {"type": "resource_conflict", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={
            "error": {"type": "rate_limit_exceeded", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
    )


@app.exception_handler(KidneyGeneticsException)
async def kidney_genetics_handler(request: Request, exc: KidneyGeneticsException):
    return JSONResponse(
        status_code=500,
        content={
            "error": {"type": "internal_error", "message": exc.message, "error_id": str(uuid.uuid4())},
        },
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_exception_handlers.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_exception_handlers.py
git commit -m "feat(errors): register global exception handlers for domain exceptions (M2)"
```

### Task 10: Replace raw HTTPException with domain exceptions in endpoints

**Files:**
- Modify: `backend/app/api/endpoints/gene_annotations.py` (~9 occurrences)
- Modify: `backend/app/api/endpoints/releases.py` (~12 occurrences)
- Modify: Other endpoint files as found via grep

- [x] **Step 1: Grep for all HTTPException raises**

```bash
cd backend && grep -rn "raise HTTPException" app/api/endpoints/ --include="*.py" | head -60
```

- [x] **Step 2: Replace in gene_annotations.py**

For each `raise HTTPException(status_code=404, detail="...")`, replace with the appropriate domain exception:
- 404 → `raise GeneNotFoundError(identifier)`
- 403 → `raise PermissionDeniedError(required_permission)`
- 400 → `raise ValidationError(field, reason)` (from `app.core.exceptions`)

Add imports at top:
```python
from app.core.exceptions import GeneNotFoundError, ValidationError as DomainValidationError
```

**Example replacement** (pattern to follow for each occurrence):
```python
# Before:
raise HTTPException(status_code=404, detail=f"Gene {gene_id} not found")
# After:
raise GeneNotFoundError(gene_id)
```

- [x] **Step 3: Replace in releases.py**

Same pattern — replace raw HTTPException with domain exceptions.

- [x] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 5: Run lint**

Run: `make lint`
Expected: No errors (remove unused HTTPException imports where appropriate)

- [x] **Step 6: Commit**

```bash
git add backend/app/api/endpoints/
git commit -m "refactor(errors): replace raw HTTPException with domain exceptions across endpoints (M2)"
```

---

## Final Verification

- [x] **Step 1: Run full test suite**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [x] **Step 2: Run lint**

Run: `make lint`
Expected: No errors

- [x] **Step 3: Typecheck modified files**

```bash
cd backend && uv run mypy app/crud/statistics.py app/core/cache_service.py \
  app/api/endpoints/genes.py app/api/endpoints/auth.py app/core/security.py \
  app/schemas/gene.py app/schemas/releases.py app/schemas/gene_staging.py \
  app/schemas/auth.py app/main.py --ignore-missing-imports
```
Expected: No errors
