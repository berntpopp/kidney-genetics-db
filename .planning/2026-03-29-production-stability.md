# Production Stability & Deployment Hardening Plan

> **Context:** Comprehensive audit of kidney-genetics-db after initial VPS deployment. Covers all issues discovered during deployment, pipeline execution, and ongoing operation. Organized by severity and domain.

**Goal:** Eliminate silent failures, fix architectural antipatterns, and harden the deployment for reliable production operation.

**Status of existing fixes:** PR #131 addresses issues #124, #125, #127, #129, #132, #133, #134, #135 with targeted patches. This plan covers the deeper architectural issues that PR #131's patches don't fully resolve.

---

## Table of Contents

1. [Critical: Silent Failure Elimination](#1-critical-silent-failure-elimination)
2. [Critical: Pipeline Parallelism Redesign](#2-critical-pipeline-parallelism-redesign)
3. [Critical: Session & Cache Singleton Antipattern](#3-critical-session--cache-singleton-antipattern)
4. [High: Docker & Deployment Hardening](#4-high-docker--deployment-hardening)
5. [High: Database Initialization Safety](#5-high-database-initialization-safety)
6. [High: Multi-Worker Readiness](#6-high-multi-worker-readiness)
7. [Medium: Error Handling Consistency](#7-medium-error-handling-consistency)
8. [Medium: Observability & Alerting](#8-medium-observability--alerting)
9. [Low: Configuration & Dependency Cleanup](#9-low-configuration--dependency-cleanup)
10. [Summary Matrix](#10-summary-matrix)

---

## 1. Critical: Silent Failure Elimination

**Root cause of most deployment failures:** PermissionError on `/app/.cache` and `/app/data` was silently caught, causing every annotation source to fall back to per-gene API calls, triggering rate limits, 100% CPU, and 0 annotations.

### 1.1 Startup Directory Validation

**File:** `backend/docker-entrypoint.sh`

Add fail-fast permission checks before migrations:

```sh
#!/bin/sh
set -e

# Fail fast on permission issues (the #1 production failure cause)
for dir in /app/.cache /app/data; do
  if [ ! -w "$dir" ]; then
    echo "FATAL: $dir is not writable by $(whoami) (uid=$(id -u))" >&2
    exit 1
  fi
done

echo "Running database migrations..."
python -m alembic upgrade head
exec "$@"
```

### 1.2 Upgrade Silent Fallbacks to Loud Failures

**Files affected (15+ instances):**

| File | Lines | Current Behavior | Fix |
|------|-------|-----------------|-----|
| `pipeline/sources/unified/bulk_mixin.py` | 319-327 | `OSError` swallowed on meta write | Log at ERROR, not WARNING |
| `pipeline/sources/unified/bulk_mixin.py` | 314-315 | `except (json.JSONDecodeError, OSError): pass` | Log + return `False` (cache invalid) |
| `pipeline/sources/annotations/descartes.py` | 168-189 | Returns `None` on HTTP error | Raise exception, let pipeline handle |
| `pipeline/annotation_pipeline.py` | 106-117 | `except Exception: pass` on pool status | Log at WARNING minimum |
| `core/hgnc_client.py` | 201-220 | Three `except Exception: pass` blocks | Log each failure, track fallback chain |
| `api/endpoints/datasources.py` | 75-77 | Query failure returns empty list `[]` | Return 500, not empty data |
| `core/cache_service.py` | 239-301 | Deserialization error returns `None` | Distinguish None (miss) vs error |

**Principle:** No `except Exception: pass` without logging. No `except OSError: pass` without at minimum WARNING level logging.

### 1.3 Circuit Breaker Logging Level

**File:** `core/retry_utils.py:135`

Circuit breaker opening is a system-level event. Change from WARNING to ERROR:

```python
# BEFORE
logger.sync_warning("Circuit breaker opened", ...)
# AFTER
logger.sync_error("Circuit breaker opened — source unavailable", ...)
```

Same fix needed in `gnomad.py:449` and `clinvar.py:940`.

---

## 2. Critical: Pipeline Parallelism Redesign

**Root cause:** Pipeline claims 3 concurrent sources but effectively runs 1 at a time because retry sleeps hold the semaphore, and domain rate limiter pauses block the event loop.

### 2.1 Move Semaphore Inside Fetch Loop, Not Around Entire Source

**File:** `pipeline/annotation_pipeline.py:619-644`

**Current (broken):**
```python
semaphore = asyncio.Semaphore(3)
async def rate_limited_update(source_name):
    async with semaphore:  # Held for ENTIRE source (minutes/hours)
        # ... all fetches, all retries, all sleeps
```

**Fix:** Semaphore should gate concurrent *API calls*, not entire source lifecycles. Each source should run freely; the semaphore should limit concurrent HTTP requests to avoid pool exhaustion:

```python
# Remove source-level semaphore
# Instead, limit concurrent HTTP requests via domain rate limiter
async def rate_limited_update(source_name):
    source_db = SessionLocal(expire_on_commit=False)
    try:
        # Each source runs independently
        # Rate limiting happens at HTTP request level via DomainRateLimiter
        result = await source.update_annotations(source_db, ...)
    finally:
        source_db.close()
```

### 2.2 Fix Retry Sleep Blocking

**File:** `core/retry_utils.py:173-202`

The `@retry_with_backoff` decorator sleeps while holding whatever context the caller acquired. This is the main serialization cause.

**Fix:** Release semaphore before sleeping, re-acquire after:
- Or better: don't use a source-level semaphore at all (see 2.1)

### 2.3 Domain Rate Limiter Pause Should Not Block Acquire

**File:** `core/domain_rate_limiter.py:44-54`

**Current:** `acquire()` sleeps synchronously when domain is paused, blocking the semaphore slot.

**Fix:** The pause should be a per-domain gate that other domains bypass:

```python
@asynccontextmanager
async def acquire(self) -> AsyncGenerator[None, None]:
    # Wait for unpause (only affects THIS domain)
    while self.is_paused:
        wait_time = self._paused_until - time.monotonic()
        if wait_time > 0:
            await asyncio.sleep(min(wait_time, 1.0))  # Check every 1s
        else:
            break

    async with self._semaphore:
        await self._rate_limiter.acquire()
        yield
```

### 2.4 Add Jitter to Prevent Synchronized Retry Storms

**File:** `core/retry_utils.py:47-62`

When 3 sources all hit 429 at the same time, they retry in synchronized waves. Add full jitter:

```python
def calculate_delay(self, attempt: int) -> float:
    delay = min(self.initial_delay * (self.exponential_base ** attempt), self.max_delay)
    # Full jitter: random between 0 and calculated delay
    return random.uniform(0, delay)
```

### 2.5 Add Semaphore Acquisition Timeout

Currently there is no timeout on semaphore acquisition. If a source hangs, all others wait forever.

```python
try:
    await asyncio.wait_for(semaphore.acquire(), timeout=300)  # 5 min max wait
except asyncio.TimeoutError:
    logger.sync_error(f"Source {source_name} timed out waiting for semaphore")
    return source_name, {"status": "timeout"}
```

---

## 3. Critical: Session & Cache Singleton Antipattern

**Root cause of cache deserialization errors and progress tracker stuck state.**

### 3.1 Remove Cache Service Global Singleton

**File:** `core/cache_service.py:983-994`

The global `cache_service` singleton has its `db_session` reassigned from concurrent contexts, causing race conditions.

**Fix:** Create per-context cache service instances:

```python
# REMOVE global singleton pattern
# INSTEAD: Create per-request/per-task instances

def create_cache_service(db_session: Session) -> CacheService:
    """Create a new CacheService instance for this context."""
    return CacheService(db_session)

# For L1 (in-memory) cache sharing, extract the LRU cache to a separate singleton
# that doesn't hold a session reference
```

### 3.2 Lock Progress Tracker Access

**File:** `core/progress_tracker.py`

Progress tracker is mutated from parallel async tasks without synchronization.

**Fix:** Add `asyncio.Lock`:

```python
class ProgressTracker:
    def __init__(self, db, ...):
        self._lock = asyncio.Lock()

    async def update(self, ...):
        async with self._lock:
            # ... merge, update, commit
```

### 3.3 Fix Status Restoration Antipattern

**File:** `core/progress_tracker.py:72-89`

Code saves status before merge, then *restores stale value* if merge changed it. This overwrites newer database state.

**Fix:** Trust the merge result. If the database has a different status, it's because another process updated it:

```python
progress = cast(DataSourceProgress, self.db.merge(progress))
# DO NOT restore stale status — the database value is authoritative
```

### 3.4 Cache Service Should Not Commit

**File:** `core/cache_service.py:718, 731`

Every cache operation calls `.commit()` on the passed session, potentially committing the caller's uncommitted work.

**Fix:** Cache operations should `.flush()` (write to DB buffer) but let the caller control transaction boundaries. Or use a dedicated session for cache operations.

---

## 4. High: Docker & Deployment Hardening

### 4.1 Add Volume Mounts for Persistent Data

**File:** `docker-compose.prod.yml`

Backend has NO volume mounts. Cache and data directories are ephemeral.

```yaml
services:
  backend:
    volumes:
      - cache_data:/app/.cache
      - string_data:/app/data

volumes:
  cache_data:
  string_data:
```

### 4.2 Fix Hardcoded Developer Path

**File:** `backend/app/core/config.py:87-89`

```python
# BEFORE (broken in production)
STRING_DATA_DIR: str = "/home/bernt-popp/development/kidney-genetics-db/backend/data/string/v12.0"

# AFTER
STRING_DATA_DIR: str = "./data/string/v12.0"
```

### 4.3 Fix CORS Origins for Production

**File:** `.env.production.example:31`

```bash
# BEFORE (blocks all frontend requests)
BACKEND_CORS_ORIGINS=[]

# AFTER
BACKEND_CORS_ORIGINS=["https://kidney-genetics.org"]
```

### 4.4 Use Docker Secrets for Sensitive Values

For `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `ZENODO_API_TOKEN`:

```yaml
services:
  backend:
    secrets:
      - jwt_secret_key
      - admin_password
      - zenodo_api_token

secrets:
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt
  admin_password:
    file: ./secrets/admin_password.txt
```

The backend already supports this via `secrets_dir="/run/secrets"` in Pydantic Settings config.

### 4.5 Pin Redis Image Digest

```yaml
# BEFORE
image: redis:7-alpine

# AFTER
image: redis:7-alpine@sha256:<digest>
```

### 4.6 Remove DAC_OVERRIDE from Redis

The `DAC_OVERRIDE` capability bypasses all file permission checks. Fix volume ownership instead.

### 4.7 Improve Entrypoint Error Reporting

**File:** `backend/docker-entrypoint.sh`

Add migration failure handling and process identity logging (see 1.1 for full script).

---

## 5. High: Database Initialization Safety

### 5.1 Add Advisory Locks for Multi-Worker Safety

**File:** `core/database_init.py:219-294`

Admin creation and annotation source seeding have race conditions when multiple workers start simultaneously.

```python
async def create_default_admin(db: Session) -> bool:
    db.execute(text("SELECT pg_advisory_lock(1001)"))
    try:
        admin = db.query(User).filter(...).first()
        if not admin:
            # create...
    finally:
        db.execute(text("SELECT pg_advisory_unlock(1001)"))
```

### 5.2 Verify Operations After Commit

After creating admin user, re-query to verify:

```python
db.commit()
created_user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
if not created_user:
    raise RuntimeError("Failed to create admin user")
```

### 5.3 Separate AnnotationPipeline Initialization from Source Seeding

Current code instantiates `AnnotationPipeline(db)` just to enumerate sources. Extract the source registry:

```python
# Instead of creating entire pipeline just to list sources:
KNOWN_SOURCES = {
    "panelapp": {"display_name": "PanelApp", "source_type": "gene_list"},
    "hgnc": {"display_name": "HGNC", "source_type": "annotation"},
    # ...
}
```

---

## 6. High: Multi-Worker Readiness (Gunicorn)

### 6.1 Add Gunicorn Process Manager

**File:** `backend/Dockerfile` CMD, `pyproject.toml` dependencies

```dockerfile
CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn_worker.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]
```

**Rationale:** Single uvicorn process cannot utilize the 4 CPUs allocated in docker-compose.prod.yml.

### 6.2 Adjust Connection Pool for Multi-Worker

**File:** `core/database.py:64-86`

With 4 workers, reduce per-worker pool to avoid exceeding PostgreSQL max_connections:

```python
pool_size=5,        # 5 per worker × 4 workers = 20 base
max_overflow=10,    # 10 per worker × 4 workers = 40 overflow
# Total max: 60 (well within PostgreSQL default 100)
```

### 6.3 Pipeline Tasks Must Use ARQ, Not BackgroundTasks

With Gunicorn `--max-requests`, workers are recycled. A pipeline running via FastAPI `BackgroundTasks` is killed when its worker is recycled. Long-running pipeline operations must use ARQ (Redis queue).

---

## 7. Medium: Error Handling Consistency

### 7.1 Replace All Bare `except Exception: pass`

Audit found 15+ instances. Each must have at minimum WARNING-level logging:

| Location | Current | Fix |
|----------|---------|-----|
| `annotation_pipeline.py:106-117` | `except Exception: pass` | Log WARNING |
| `annotation_pipeline.py:320-324` | `except Exception: pass` | Log WARNING |
| `pubtator.py:755-758` | Rollback `except Exception: pass` | Log ERROR (rollback failure is serious) |
| `pubtator.py:1013-1016` | Same | Same |
| `hgnc_client.py:201-220` | Three `pass` blocks | Log each failure |
| `resource_monitor.py:37-38,70-71` | Returns None | Log WARNING |
| `admin_logs.py:167-169` | Comment: "logging removed for circular import" | Fix circular import, restore logging |

### 7.2 Consistent `raise_for_status()` Usage

All HTTP requests through RetryableHTTPClient should call `raise_for_status()`. Sources doing manual status code checks should migrate:

```python
# BEFORE (descartes.py)
if response.status_code != 200:
    logger.warning(...)
    return

# AFTER
response.raise_for_status()  # Let retry_with_backoff handle it
```

### 7.3 Distinguish "No Data" from "Error" in API Responses

**File:** `api/endpoints/datasources.py:75-77`

Returning empty `[]` on query failure hides errors from frontend. Return 500 with error detail instead.

---

## 8. Medium: Observability & Alerting

### 8.1 Add Prometheus Metrics

```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

Gives RED metrics (Rate, Errors, Duration) per endpoint with zero custom code.

### 8.2 Log Process Identity at Startup

```python
import os
logger.sync_info("Process started",
                  uid=os.getuid(), gid=os.getgid(),
                  writable_cache=os.access(".cache", os.W_OK),
                  writable_data=os.access("data", os.W_OK))
```

### 8.3 Key Alerting Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| P95 latency | > 2s for 5 min | Investigate DB/external API |
| 5xx rate | > 1% for 5 min | Check logs |
| DB pool utilization | > 80% | Increase pool or find leak |
| Pipeline source failures | > 3 concurrent | External API outage |
| Container restarts | > 2/hour | Crash loop |

### 8.4 Add Request ID Propagation

Generate UUID per request in middleware, bind to logger, return in `X-Request-ID` header.

---

## 9. Low: Configuration & Dependency Cleanup

### 9.1 Remove Unused passlib Dependency

**File:** `pyproject.toml:45`

`passlib[bcrypt]>=1.7.4` is listed but never imported. The codebase uses direct `bcrypt` calls. This was the root cause of the auth 500 error (passlib 1.7.4 incompatible with bcrypt 5.0.0).

### 9.2 Complete `.env.production.example`

Missing variables that cause silent misconfiguration:
- `STRING_DATA_DIR` (defaults to hardcoded dev path)
- `ARQ_*` settings
- `CACHE_*` settings
- `ZENODO_*` settings
- `ADMIN_USERNAME`, `ADMIN_EMAIL`

### 9.3 Disable `idle_in_transaction_session_timeout = 0` in Pipeline

**File:** `annotation_pipeline.py:216, 629`

Setting timeout to 0 disables leak detection. Use a generous but finite timeout:

```python
source_db.execute(text("SET idle_in_transaction_session_timeout = 300000"))  # 5 min
```

### 9.4 Add Backup Verification

Current backup container runs `pg_dump` daily but never verifies restorability. Add periodic `pg_restore --list` check.

---

## 10. Summary Matrix

| # | Issue | Severity | Effort | PR #131 | Section |
|---|-------|----------|--------|---------|---------|
| 1 | Silent PermissionError cascades | **CRITICAL** | Low | Partial | 1.1-1.2 |
| 2 | Pipeline runs serial (semaphore design) | **CRITICAL** | High | Partial (#132) | 2.1-2.5 |
| 3 | Cache singleton session race | **CRITICAL** | Medium | Partial (#134) | 3.1, 3.4 |
| 4 | Progress tracker concurrent mutation | **CRITICAL** | Medium | Partial (#135) | 3.2-3.3 |
| 5 | No backend volume mounts | **HIGH** | Low | No | 4.1 |
| 6 | Hardcoded dev path in config | **HIGH** | Trivial | No | 4.2 |
| 7 | CORS empty in production | **HIGH** | Trivial | No | 4.3 |
| 8 | Secrets in env vars (not Docker secrets) | **HIGH** | Low | No | 4.4 |
| 9 | DB init race condition (multi-worker) | **HIGH** | Low | No | 5.1 |
| 10 | Single uvicorn process (wastes 3 CPUs) | **HIGH** | Medium | No | 6.1-6.2 |
| 11 | Pipeline tasks killed on worker recycle | **HIGH** | Medium | No | 6.3 |
| 12 | 15+ bare `except: pass` blocks | **MEDIUM** | Medium | No | 7.1 |
| 13 | Inconsistent HTTP error handling | **MEDIUM** | Low | No | 7.2 |
| 14 | No Prometheus metrics | **MEDIUM** | Low | No | 8.1 |
| 15 | Unused passlib dependency | **LOW** | Trivial | No | 9.1 |
| 16 | Incomplete .env.production.example | **LOW** | Low | No | 9.2 |
| 17 | Infinite idle_in_transaction timeout | **LOW** | Trivial | No | 9.3 |

### Recommended Implementation Order

**Phase 1 — Immediate (prevent repeat of deployment failures):**
- 1.1 Startup validation in entrypoint
- 4.1 Volume mounts in docker-compose.prod.yml
- 4.2 Fix hardcoded STRING_DATA_DIR
- 4.3 Fix CORS origins
- 9.1 Remove passlib

**Phase 2 — Short-term (pipeline reliability):**
- 2.1-2.5 Pipeline parallelism redesign
- 3.1-3.4 Session/cache singleton fix
- 7.1-7.3 Error handling cleanup

**Phase 3 — Medium-term (production hardening):**
- 5.1-5.3 Database init safety
- 6.1-6.3 Gunicorn multi-worker
- 4.4 Docker secrets migration
- 8.1-8.4 Observability

**Phase 4 — Long-term (operational maturity):**
- 9.2-9.4 Configuration cleanup
- Backup verification
- Adaptive rate limiting
- Circuit breakers for external APIs
