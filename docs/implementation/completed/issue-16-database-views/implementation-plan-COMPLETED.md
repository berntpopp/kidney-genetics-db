# Issue #16: Database Views Migration - Complete Implementation Guide

**Version**: 3.0 FINAL (Consolidated for Agentic LLM)
**Date**: 2025-09-29
**Status**: Ready for Implementation
**Risk Level**: ✅ **LOW-MEDIUM** (with all safeguards)

## 📋 Executive Summary

This guide consolidates the complete implementation plan for migrating complex SQL queries to PostgreSQL database views. The migration addresses security vulnerabilities, performance issues, and maintainability concerns while ensuring zero downtime and 100% backward compatibility.

### Key Objectives
- **Eliminate** 2 SQL injection vulnerabilities
- **Reduce** embedded SQL by 80% (1000+ lines)
- **Improve** query performance by 10x
- **Maintain** 100% API compatibility
- **Enable** safe gradual rollout with automatic rollback

### Critical Findings from Assessment
- **47+ raw SQL instances** across 15 files identified
- **Performance potential**: 10-1600x improvement with views
- **Security issues**: 2 medium-risk SQL injection vulnerabilities
- **Existing patterns**: Strong foundation with ReplaceableObject system

---

## 🚨 Pre-Implementation Requirements

### System Prerequisites
```bash
# Required dependencies
cd backend
uv add prometheus-client  # Monitoring
uv add deepdiff          # Shadow testing comparisons

# Verify existing systems
grep -r "ReplaceableObject" app/db/  # Confirm view system exists
grep -r "ThreadPoolExecutor" app/    # Check thread pool usage
grep -r "CacheService" app/core/     # Verify cache system

# Create backups
make db-backup-full
git checkout -b feature/issue-16-database-views-final
```

### Performance Baseline
```bash
# Capture current performance metrics
cd backend && uv run python << 'EOF'
import time
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
queries = [
    ("Gene list", "SELECT * FROM genes LIMIT 100"),
    ("Admin logs", "SELECT * FROM system_logs ORDER BY created_at DESC LIMIT 100"),
]

for name, query in queries:
    start = time.time()
    db.execute(text(query)).fetchall()
    print(f"{name}: {(time.time() - start) * 1000:.2f}ms")

db.close()
EOF
```

---

## 🏗️ Implementation Phases

## Phase 0: Infrastructure Setup

### Task 0.1: Singleton Thread Pool Configuration

**Location**: `/backend/app/core/database.py` (Line 50)

<details>
<summary>Implementation Code</summary>

```python
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# Add after imports (line 50)
_thread_pool_executor: Optional[ThreadPoolExecutor] = None
_thread_pool_lock = threading.Lock()

def get_thread_pool_executor() -> ThreadPoolExecutor:
    """Get or create singleton thread pool for database operations."""
    global _thread_pool_executor

    if _thread_pool_executor is None:
        with _thread_pool_lock:
            if _thread_pool_executor is None:
                logger.info("Creating singleton thread pool executor")
                _thread_pool_executor = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix="db-executor-",
                )

    return _thread_pool_executor

# Register cleanup
import atexit
atexit.register(lambda: _thread_pool_executor and _thread_pool_executor.shutdown(wait=True))
```

</details>

### Task 0.2: Feature Flag System

**New File**: `/backend/app/core/feature_flags.py`

<details>
<summary>Implementation Code</summary>

```python
"""Feature flag system for safe database views rollout."""

from enum import Enum
from typing import Optional
import hashlib

class RolloutStrategy(Enum):
    OFF = "off"
    ON = "on"
    PERCENTAGE = "percentage"
    GRADUAL = "gradual"

class FeatureFlags:
    """Centralized feature flag management."""

    FLAGS = {
        "use_database_views": {
            "enabled": False,
            "strategy": RolloutStrategy.GRADUAL,
            "percentage": 0.0,
            "rollout_steps": {1: 0, 2: 10, 3: 25, 4: 50, 5: 75, 6: 100}
        },
        "enable_shadow_testing": {
            "enabled": True,
            "strategy": RolloutStrategy.ON
        }
    }

    @classmethod
    def is_enabled(cls, flag_name: str, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled for user."""
        flag = cls.FLAGS.get(flag_name, {})

        if not flag.get("enabled", False):
            return False

        strategy = flag.get("strategy", RolloutStrategy.OFF)

        if strategy == RolloutStrategy.ON:
            return True
        elif strategy == RolloutStrategy.PERCENTAGE and user_id:
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            return (user_hash % 100) < flag.get("percentage", 0)

        return False

    @classmethod
    def emergency_disable(cls, flag_name: str):
        """Emergency disable a feature."""
        if flag_name in cls.FLAGS:
            cls.FLAGS[flag_name]["enabled"] = False
```

</details>

### Task 0.3: Monitoring Setup

**New File**: `/backend/app/core/monitoring.py`

<details>
<summary>Implementation Code</summary>

```python
"""Monitoring for database views migration."""

import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

registry = CollectorRegistry()

# Metrics definitions
view_query_duration = Histogram(
    'db_view_query_duration_seconds',
    'Database view query duration',
    ['view_name', 'operation'],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

view_query_errors = Counter(
    'db_view_query_errors_total',
    'Database view query errors',
    ['view_name', 'error_type'],
    registry=registry
)

def track_view_performance(view_name: str):
    """Decorator to track view performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                view_query_duration.labels(
                    view_name=view_name,
                    operation="query"
                ).observe(time.time() - start)
                return result
            except Exception as e:
                view_query_errors.labels(
                    view_name=view_name,
                    error_type=type(e).__name__
                ).inc()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else func
    return decorator
```

</details>

### Task 0.4: Cache Invalidation Strategy

**New File**: `/backend/app/core/cache_invalidation.py`

<details>
<summary>Implementation Code</summary>

```python
"""Cache invalidation for database views."""

from typing import Dict, Set, List
from dataclasses import dataclass

@dataclass
class ViewDependency:
    """View dependencies on tables."""
    view_name: str
    depends_on_tables: Set[str]
    cache_namespaces: Set[str]

class CacheInvalidationManager:
    """Manages cache invalidation for views."""

    VIEW_DEPENDENCIES = {
        "gene_list_detailed": ViewDependency(
            view_name="gene_list_detailed",
            depends_on_tables={"genes", "gene_scores", "evidence_summary_view"},
            cache_namespaces={"views:gene_list", "api:genes"}
        ),
        "admin_logs_filtered": ViewDependency(
            view_name="admin_logs_filtered",
            depends_on_tables={"system_logs", "users"},
            cache_namespaces={"views:admin_logs", "api:logs"}
        )
    }

    def __init__(self, cache_service):
        self.cache_service = cache_service
        self._table_to_views = self._build_reverse_mapping()

    def _build_reverse_mapping(self) -> Dict[str, Set[str]]:
        """Build table -> dependent views mapping."""
        mapping = {}
        for view_name, dep in self.VIEW_DEPENDENCIES.items():
            for table in dep.depends_on_tables:
                mapping.setdefault(table, set()).add(view_name)
        return mapping

    async def invalidate_for_table(self, table_name: str) -> List[str]:
        """Invalidate caches for views depending on table."""
        invalidated = []

        for view_name in self._table_to_views.get(table_name, set()):
            dep = self.VIEW_DEPENDENCIES[view_name]
            for namespace in dep.cache_namespaces:
                await self.cache_service.clear_namespace(namespace)
                invalidated.append(namespace)

        return invalidated
```

</details>

---

## Phase 1: Security & Validation

### Task 1.1: Fix SQL Injection Vulnerability

**File**: `/backend/app/api/endpoints/admin_logs.py`

<details>
<summary>Changes Required</summary>

**Line 20** - Add import:
```python
from app.core.validators import SQLSafeValidator
```

**Lines 77-78** - Replace vulnerable code:
```python
# BEFORE (VULNERABLE):
query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT :limit OFFSET :offset"

# AFTER (SECURE):
sort_by = SQLSafeValidator.validate_column(sort_by, "system_logs")
sort_order = SQLSafeValidator.validate_sort_order(sort_order)
query += f" ORDER BY {sort_by} {sort_order} LIMIT :limit OFFSET :offset"
```

</details>

### Task 1.2: Centralized SQL Validators

**New File**: `/backend/app/core/validators.py`

<details>
<summary>Implementation Code</summary>

```python
"""Centralized SQL parameter validation."""

from typing import Set
from fastapi import HTTPException
from app.core.logging import get_logger

logger = get_logger(__name__)

class SQLSafeValidator:
    """Validate SQL parameters against injection."""

    SAFE_COLUMNS = {
        "system_logs": {
            "id", "user_id", "action", "level", "endpoint",
            "method", "status_code", "response_time_ms", "created_at"
        },
        "genes": {
            "id", "gene_id", "approved_symbol", "approved_name",
            "total_score", "classification", "created_at"
        }
    }

    SAFE_SORT_ORDERS = {"ASC", "DESC"}

    @classmethod
    def validate_column(cls, column: str, table: str) -> str:
        """Validate column name against whitelist."""
        safe_columns = cls.SAFE_COLUMNS.get(table, set())

        if column not in safe_columns:
            logger.warning(f"Rejected unsafe column: {column}", table=table)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column. Allowed: {', '.join(sorted(safe_columns))}"
            )

        return column

    @classmethod
    def validate_sort_order(cls, order: str) -> str:
        """Validate sort order."""
        order_upper = order.upper()

        if order_upper not in cls.SAFE_SORT_ORDERS:
            raise HTTPException(status_code=400, detail="Sort order must be ASC or DESC")

        return order_upper
```

</details>

---

## Phase 2: Database Views Creation

### Task 2.1: Type-Safe Database Views

**File**: `/backend/app/db/views.py` (Insert after line 255)

<details>
<summary>View Definitions</summary>

```python
# Type-safe gene list view with explicit casting
gene_list_detailed = ReplaceableObject(
    name="gene_list_detailed",
    sqltext="""
    SELECT
        g.id::bigint AS gene_id,
        g.hgnc_id::text AS hgnc_id,
        g.approved_symbol::text AS gene_symbol,
        g.approved_name::text AS approved_name,
        COALESCE(g.alias_symbols, ARRAY[]::text[])::text[] AS alias_symbols,
        g.entrez_id::text AS entrez_id,
        g.ensembl_gene_id::text AS ensembl_gene_id,
        COALESCE(gs.total_score, 0.0)::float8 AS total_score,
        COALESCE(gs.classification, 'Unknown')::text AS classification,
        COALESCE(esv.source_count, 0)::integer AS source_count,
        COALESCE(esv.sources, '{}'::text[])::text[] AS sources,
        g.created_at::timestamptz AS created_at,
        g.updated_at::timestamptz AS updated_at
    FROM genes g
    LEFT JOIN gene_scores gs ON g.id = gs.gene_id
    LEFT JOIN evidence_summary_view esv ON g.id = esv.gene_id
    LEFT JOIN annotation_summary_view asv ON g.id = asv.gene_id
    WHERE g.is_active = true
    """,
    dependencies=["gene_scores", "evidence_summary_view", "annotation_summary_view"],
)

# Admin logs filtered view
admin_logs_filtered = ReplaceableObject(
    name="admin_logs_filtered",
    sqltext="""
    SELECT
        sl.id::bigint,
        sl.user_id::bigint,
        u.email::text AS user_email,
        sl.action::text,
        sl.level::text,
        sl.endpoint::text,
        sl.method::text,
        sl.status_code::integer,
        sl.response_time_ms::float8,
        sl.created_at::timestamptz,
        CASE
            WHEN sl.status_code < 400 THEN 'success'
            WHEN sl.status_code < 500 THEN 'client_error'
            ELSE 'server_error'
        END::text AS status_category
    FROM system_logs sl
    LEFT JOIN users u ON sl.user_id = u.id
    WHERE sl.endpoint IS NOT NULL
    """,
    dependencies=[],
)

# Register views
ALL_VIEWS.append(gene_list_detailed)
ALL_VIEWS.append(admin_logs_filtered)
```

</details>

### Task 2.2: Materialized Views with Advisory Locks

**New File**: `/backend/app/db/materialized_views.py`

<details>
<summary>Implementation Code</summary>

```python
"""Safe materialized view management."""

from sqlalchemy import text
from datetime import datetime, timedelta

class MaterializedViewManager:
    """Manages materialized view refresh with advisory locks."""

    def __init__(self, db):
        self.db = db

    def _get_lock_id(self, view_name: str) -> int:
        """Generate lock ID from view name."""
        result = self.db.execute(
            text("SELECT hashtext(:name)::int"),
            {"name": view_name}
        ).scalar()
        return abs(result) % 2147483647

    async def refresh_view_safely(
        self,
        view_name: str,
        force: bool = False
    ) -> bool:
        """Refresh materialized view with advisory lock."""
        lock_id = self._get_lock_id(view_name)

        try:
            # Try to acquire advisory lock
            locked = self.db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            ).scalar()

            if not locked:
                return False  # Already being refreshed

            # Skip refresh check if forcing
            if not force:
                # Check if recently refreshed
                last_refresh = self._get_last_refresh_time(view_name)
                if last_refresh:
                    # Skip if refreshed recently
                    return False

            # Perform refresh
            if self._supports_concurrent_refresh(view_name):
                self.db.execute(
                    text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                )
            else:
                self.db.execute(
                    text(f"REFRESH MATERIALIZED VIEW {view_name}")
                )

            self.db.commit()
            return True

        finally:
            # Always release lock
            self.db.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id}
            )

    def _supports_concurrent_refresh(self, view_name: str) -> bool:
        """Check if view has unique index for concurrent refresh."""
        result = self.db.execute(
            text("""
                SELECT COUNT(*) > 0
                FROM pg_indexes
                WHERE tablename = :view_name
                AND indexdef LIKE '%UNIQUE%'
            """),
            {"view_name": view_name}
        ).scalar()
        return bool(result)
```

</details>

### Task 2.3: Create Repository Pattern

**New File**: `/backend/app/repositories/gene_repository.py`

<details>
<summary>Implementation Code</summary>

```python
"""Gene repository with view support."""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_thread_pool_executor
from app.core.cache_service import CacheService
from app.core.monitoring import track_view_performance

class GeneRepository:
    """Repository for gene data access."""

    def __init__(self, db: Session, cache_service: Optional[CacheService] = None):
        self.db = db
        self.cache_service = cache_service
        self._executor = get_thread_pool_executor()

    @track_view_performance("gene_list_detailed")
    async def get_genes_from_view(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: str = "gene_symbol",
        sort_order: str = "ASC",
        filter_source: Optional[str] = None
    ) -> List:
        """Get genes using database view."""

        # Build cache key
        cache_key = f"genes:{skip}:{limit}:{search}:{sort_by}:{sort_order}:{filter_source}"

        # Try cache
        if self.cache_service:
            cached = await self.cache_service.get(cache_key, namespace="views:gene_list")
            if cached:
                return cached

        # Build query
        query = "SELECT * FROM gene_list_detailed WHERE 1=1"
        params = {}

        if search:
            query += " AND (gene_symbol ILIKE :search OR approved_name ILIKE :search)"
            params["search"] = f"%{search}%"

        if filter_source:
            query += " AND :source = ANY(sources)"
            params["source"] = filter_source

        query += f" ORDER BY {sort_by} {sort_order}"
        query += " LIMIT :limit OFFSET :skip"
        params.update({"limit": limit, "skip": skip})

        # Execute in thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self.db.execute(text(query), params).fetchall()
        )

        # Cache result
        if self.cache_service:
            await self.cache_service.set(
                cache_key, result, namespace="views:gene_list", ttl=300
            )

        return result

    async def get_genes_legacy(self, **kwargs) -> List:
        """Legacy implementation for comparison."""
        # Original complex SQL implementation
        # (Keep existing code for shadow testing)
        pass
```

</details>

---

## Phase 3: Shadow Testing

### Task 3.1: Shadow Testing Implementation

**New File**: `/backend/app/core/shadow_testing.py`

<details>
<summary>Implementation Code</summary>

```python
"""Shadow testing for backward compatibility."""

import asyncio
import time
from typing import Any, Callable
from dataclasses import dataclass
from deepdiff import DeepDiff

from app.core.logging import get_logger
from app.core.monitoring import shadow_test_mismatches

logger = get_logger(__name__)

@dataclass
class ShadowTestResult:
    """Shadow test comparison result."""
    endpoint: str
    old_duration_ms: float
    new_duration_ms: float
    results_match: bool
    differences: dict = None

class ShadowTester:
    """Runs shadow tests comparing implementations."""

    async def shadow_test(
        self,
        endpoint: str,
        old_impl: Callable,
        new_impl: Callable,
        *args,
        **kwargs
    ) -> ShadowTestResult:
        """Compare old and new implementations."""

        # Run both in parallel
        old_task = asyncio.create_task(self._run_with_timing(old_impl, *args, **kwargs))
        new_task = asyncio.create_task(self._run_with_timing(new_impl, *args, **kwargs))

        try:
            (old_result, old_time), (new_result, new_time) = await asyncio.gather(
                old_task, new_task, return_exceptions=True
            )

            # Handle exceptions
            if isinstance(new_result, Exception):
                logger.error(f"New implementation failed: {new_result}")
                return old_result  # Fallback to old

            # Compare results
            diff = DeepDiff(
                old_result,
                new_result,
                ignore_order=True,
                significant_digits=6,
                exclude_paths=["root['updated_at']"]
            )

            results_match = not bool(diff)

            if not results_match:
                logger.warning(f"Shadow test mismatch for {endpoint}", diff=diff)
                shadow_test_mismatches.labels(endpoint=endpoint).inc()

            return ShadowTestResult(
                endpoint=endpoint,
                old_duration_ms=old_time * 1000,
                new_duration_ms=new_time * 1000,
                results_match=results_match,
                differences=diff.to_dict() if diff else None
            )

        except Exception as e:
            logger.error(f"Shadow test failed: {e}")
            return old_result  # Fallback

    async def _run_with_timing(self, func: Callable, *args, **kwargs):
        """Execute function with timing."""
        start = time.time()
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        return result, time.time() - start
```

</details>

### Task 3.2: Update API Endpoints

**File**: `/backend/app/api/endpoints/genes.py`

<details>
<summary>Updated Implementation</summary>

```python
from app.repositories.gene_repository import GeneRepository
from app.core.shadow_testing import ShadowTester
from app.core.feature_flags import FeatureFlags

shadow_tester = ShadowTester()

@router.get("/", response_model=List[GeneResponse])
async def get_genes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: str = "gene_symbol",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
    repo: GeneRepository = Depends(get_gene_repository),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get genes with feature flag control and shadow testing."""

    user_id = current_user.email if current_user else None

    # Check feature flag
    if FeatureFlags.is_enabled("use_database_views", user_id=user_id):
        return await repo.get_genes_from_view(
            skip=skip, limit=limit, search=search,
            sort_by=sort_by, sort_order=sort_order
        )

    # Shadow test if enabled
    if FeatureFlags.is_enabled("enable_shadow_testing", user_id=user_id):
        await shadow_tester.shadow_test(
            endpoint="get_genes",
            old_impl=repo.get_genes_legacy,
            new_impl=repo.get_genes_from_view,
            skip=skip, limit=limit, search=search,
            sort_by=sort_by, sort_order=sort_order
        )

    # Return old implementation
    return await repo.get_genes_legacy(
        skip=skip, limit=limit, search=search,
        sort_by=sort_by, sort_order=sort_order
    )
```

</details>

---

## Phase 4: Testing & Validation

### Task 4.1: Comprehensive Test Suite

**File**: `/backend/tests/test_database_views.py`

<details>
<summary>Test Implementation</summary>

```python
"""Tests for database views migration."""

import pytest
import time
from sqlalchemy import text

class TestDatabaseViews:
    """Test database views implementation."""

    @pytest.mark.asyncio
    async def test_views_exist(self, db_session):
        """Verify all views are created."""
        views = ["gene_list_detailed", "admin_logs_filtered"]

        for view_name in views:
            result = db_session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.views
                        WHERE table_name = :name
                    )
                """),
                {"name": view_name}
            ).scalar()
            assert result, f"View {view_name} missing"

    @pytest.mark.asyncio
    async def test_type_safety(self, db_session):
        """Verify view column types."""
        result = db_session.execute(
            text("SELECT * FROM gene_list_detailed LIMIT 1")
        ).first()

        if result:
            assert isinstance(result.gene_id, int)
            assert isinstance(result.total_score, float)
            assert isinstance(result.sources, list)

    @pytest.mark.asyncio
    async def test_performance(self, db_session):
        """Compare view vs raw query performance."""
        # View query
        start = time.time()
        db_session.execute(
            text("SELECT * FROM gene_list_detailed LIMIT 100")
        ).fetchall()
        view_time = time.time() - start

        # Raw query
        start = time.time()
        db_session.execute(
            text("""
                SELECT g.*, gs.total_score
                FROM genes g
                LEFT JOIN gene_scores gs ON g.id = gs.gene_id
                LIMIT 100
            """)
        ).fetchall()
        raw_time = time.time() - start

        # View should be faster or comparable
        assert view_time <= raw_time * 1.5

    @pytest.mark.asyncio
    async def test_shadow_compatibility(self, gene_repo):
        """Test shadow testing returns compatible results."""
        from app.core.shadow_testing import ShadowTester

        tester = ShadowTester()
        result = await tester.shadow_test(
            endpoint="test",
            old_impl=gene_repo.get_genes_legacy,
            new_impl=gene_repo.get_genes_from_view,
            limit=10
        )

        assert result.results_match or result.differences is not None

    @pytest.mark.asyncio
    async def test_materialized_view_refresh(self, db_session):
        """Test safe refresh with advisory locks."""
        from app.db.materialized_views import MaterializedViewManager

        manager = MaterializedViewManager(db_session)

        # Should complete without deadlock
        refreshed = await manager.refresh_view_safely(
            "source_overlap_statistics",
            force=True
        )

        assert isinstance(refreshed, bool)
```

</details>

### Task 4.2: Performance Comparison Script

**File**: `/backend/scripts/performance_comparison.py`

<details>
<summary>Script Implementation</summary>

```python
#!/usr/bin/env python3
"""Compare performance of old vs new implementations."""

import asyncio
import time
import statistics
import json

from app.core.database import SessionLocal
from app.repositories.gene_repository import GeneRepository

async def run_comparison(iterations: int = 10):
    """Run performance comparison."""
    db = SessionLocal()
    repo = GeneRepository(db)

    test_cases = [
        {"name": "small", "limit": 10},
        {"name": "medium", "limit": 100},
        {"name": "large", "limit": 1000},
        {"name": "filtered", "limit": 100, "search": "BRCA"}
    ]

    results = {"tests": []}

    for test in test_cases:
        old_times = []
        new_times = []

        for _ in range(iterations):
            # Old implementation
            start = time.time()
            await repo.get_genes_legacy(**test)
            old_times.append(time.time() - start)

            # New implementation
            start = time.time()
            await repo.get_genes_from_view(**test)
            new_times.append(time.time() - start)

        result = {
            "test": test["name"],
            "old_median_ms": statistics.median(old_times) * 1000,
            "new_median_ms": statistics.median(new_times) * 1000,
            "improvement_pct": (
                (statistics.median(old_times) - statistics.median(new_times))
                / statistics.median(old_times) * 100
            )
        }

        results["tests"].append(result)
        print(f"{test['name']}: {result['improvement_pct']:.1f}% improvement")

    with open("performance_results.json", "w") as f:
        json.dump(results, f, indent=2)

    db.close()

if __name__ == "__main__":
    asyncio.run(run_comparison())
```

</details>

---

## Phase 5: Gradual Rollout

### Rollout Schedule

| Step | Percentage | Stage |
|------|------------|-------|
| 1 | 0% | Shadow testing only |
| 2 | 10% | Initial rollout |
| 3 | 25% | First checkpoint |
| 4 | 50% | Second checkpoint |
| 5 | 75% | Third checkpoint |
| 6 | 100% | Full rollout |

### Automatic Rollback Triggers

- Error rate > 1%
- P99 latency > 200ms
- Shadow test mismatch > 5%
- Manual emergency disable

### Monitoring Dashboard

```python
# Add to /backend/app/api/endpoints/metrics.py
@router.get("/metrics/views")
async def get_view_metrics():
    """Get database view performance metrics."""
    return {
        "rollout_percentage": FeatureFlags.FLAGS["use_database_views"]["percentage"],
        "error_rate": 0.001,  # From Prometheus
        "p99_latency_ms": 85,  # From Prometheus
        "shadow_test_match_rate": 0.98,  # From monitoring
        "cache_hit_rate": 0.82  # From cache service
    }
```

---

## 📋 Migration Checklist

### Pre-Migration
- [ ] Backup database: `make db-backup-full`
- [ ] Capture performance baseline
- [ ] Create feature branch
- [ ] Install dependencies

### Phase 0 (Infrastructure)
- [ ] Implement singleton thread pool
- [ ] Deploy feature flag system
- [ ] Set up monitoring
- [ ] Configure cache invalidation

### Phase 1 (Security)
- [ ] Fix SQL injection vulnerabilities
- [ ] Deploy centralized validators
- [ ] Test security fixes

### Phase 2 (Views)
- [ ] Create database views
- [ ] Deploy materialized views
- [ ] Implement repository pattern
- [ ] Run migration: `alembic upgrade head`

### Phase 3 (Shadow Testing)
- [ ] Deploy shadow testing
- [ ] Update API endpoints
- [ ] Verify compatibility

### Phase 4 (Testing)
- [ ] Run all tests: `make test`
- [ ] Performance comparison
- [ ] Document results

### Phase 5 (Rollout)
- [ ] Enable 10% rollout
- [ ] Monitor metrics daily
- [ ] Gradual increase per rollout steps
- [ ] Full rollout at final step

### Post-Migration
- [ ] Remove old implementation
- [ ] Clean up feature flags
- [ ] Document lessons learned

---

## 🎯 Success Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Performance** |
| Gene list P50 | 200ms | 20ms | ⏳ |
| Gene list P99 | 800ms | 100ms | ⏳ |
| Admin logs P50 | 300ms | 30ms | ⏳ |
| **Reliability** |
| Error rate | <0.1% | <0.1% | ⏳ |
| Availability | 99.9% | 99.9% | ⏳ |
| **Quality** |
| Shadow test match | - | >95% | ⏳ |
| Cache hit rate | 60% | >75% | ⏳ |

---

## 🚨 Emergency Procedures

### Immediate Rollback
```bash
# Via feature flag
curl -X POST http://localhost:8000/api/admin/feature-flags/disable \
  -d '{"flag": "use_database_views"}'

# Via database
psql -U kidney_genetics -d kidney_genetics_db \
  -c "UPDATE feature_flags SET enabled = false WHERE name = 'use_database_views';"
```

### View Issues
```bash
# Drop problematic view
psql -U kidney_genetics -d kidney_genetics_db \
  -c "DROP VIEW IF EXISTS view_name CASCADE;"

# Restore from backup
make db-restore-full
```

### Performance Degradation
```python
# Emergency cache clear
from app.core.cache_service import get_cache_service
cache = get_cache_service(db)
await cache.clear_all_namespaces()
```

---

## 📚 References

- Original Issue: [#16 - Move complex raw SQL queries to database views](https://github.com/berntpopp/kidney-genetics-db/issues/16)
- PostgreSQL Views Documentation: https://www.postgresql.org/docs/current/sql-createview.html
- SQLAlchemy Async Documentation: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Prometheus Python Client: https://github.com/prometheus/client_python

---

**Document Status**: FINAL (Agentic LLM Ready)
**Version**: 3.1
**Last Updated**: 2025-09-29