# Comprehensive Error and Warning Analysis - October 15, 2025

**Status**: Active
**Priority**: High
**Date**: 2025-10-15
**Analysis Period**: Last 24 hours
**Total Events Analyzed**: 225 (155 errors + 70 warnings)

## Executive Summary

Deep analysis of 24 hours of system logs revealed **12 unique error patterns** (155 occurrences) and **18 unique warning patterns** (70 occurrences). The most critical issue is cache endpoint failures (144 occurrences - 93% of all errors), followed by pipeline transaction issues and WebSocket communication problems.

## 📊 Statistics Overview

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Errors** | 155 | 68.9% |
| **Total Warnings** | 70 | 31.1% |
| **Unique Error Patterns** | 12 | - |
| **Unique Warning Patterns** | 18 | - |
| **Critical Issues** | 3 | - |
| **Medium Issues** | 5 | - |
| **Low Priority** | 4 | - |

---

## 🔴 CRITICAL ERRORS (Priority 1)

### Error #1: Cache Namespace Stats Failures
**Frequency**: 144 occurrences (93% of all errors)
**Impact**: Admin cache management completely broken
**Status**: Root cause identified, fix documented

#### Breakdown
- 72x `app.api.endpoints.cache` - "Error getting namespace stats" (ValidationError)
- 72x `request_middleware` - "Request failed with unhandled exception" (CacheError)

#### Details
These are paired errors (each failed request generates 2 log entries). The endpoint `/api/admin/cache/stats/{namespace}` returns 500 Internal Server Error for all namespaces except `clinvar`.

**Affected Namespaces** (8 total):
- hgnc
- pubtator
- gencc
- panelapp
- hpo
- clingen
- http
- files

**Root Cause**: Endpoint throws ValidationError when namespace has no cache entries instead of returning zeros.

**Fix**: Documented in `bug-fixes-2025-10-15.md` Issue #2

---

### Error #2: Pipeline Transaction Rollback Issues
**Frequency**: 3 occurrences
**Impact**: Pipeline operations fail mid-execution
**Status**: Requires investigation

#### Occurrences

1. **Parallel update failure** (1x)
   ```
   Logger: app.pipeline.annotation_pipeline
   Message: Error in parallel update for clinvar
   Type: Error
   ```

2. **Invalid transaction state** (1x)
   ```
   Logger: app.pipeline.annotation_pipeline
   Message: Pipeline error: Can't reconnect until invalid transaction is rolled back
   ```

3. **Gene update failure** (1x)
   ```
   Logger: app.pipeline.sources.annotations.base
   Message: Error updating gene PALB2: (psycopg2.OperationalError) server closed the connection unexpectedly
   ```

4. **Endpoint pipeline failure** (1x)
   ```
   Logger: app.api.endpoints.gene_annotations
   Message: Pipeline update failed: Can't reconnect until invalid transaction is rolled back
   ```

#### Root Cause Analysis

These errors indicate database transaction issues where:
1. A transaction encounters an error
2. The transaction is not properly rolled back
3. Subsequent operations fail because the session is in an invalid state

**Probable Causes**:
- Network interruption during DB operation
- Long-running transaction timeout
- Improper exception handling in pipeline code
- Missing rollback in error paths

#### Investigation Required

**Files to Review**:
- `backend/app/pipeline/annotation_pipeline.py` - Parallel update logic
- `backend/app/pipeline/sources/annotations/base.py` - Gene update error handling
- `backend/app/core/database.py` - Transaction context managers

**What to Check**:
1. Are all database operations wrapped in try/except?
2. Do all exception handlers call `db.rollback()`?
3. Are there proper timeout settings?
4. Is connection pool exhaustion happening?

#### Recommended Fix

**Pattern 1**: Ensure all pipeline operations use the robust context manager:

```python
from app.core.database import transactional_context

# CORRECT ✅
async def update_gene_annotations(gene_id: int):
    try:
        with transactional_context(timeout_seconds=300) as db:
            # Perform updates
            result = db.execute(...)
            # Context manager handles commit/rollback
    except Exception as e:
        await logger.error("Update failed", error=e, gene_id=gene_id)
        raise

# INCORRECT ❌
async def update_gene_annotations(gene_id: int):
    db = SessionLocal()
    try:
        result = db.execute(...)
        db.commit()  # What if this fails?
    except Exception as e:
        # Missing rollback!
        await logger.error("Update failed", error=e)
    finally:
        db.close()
```

**Pattern 2**: For parallel operations, use thread pool with proper isolation:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_update(genes: list[int]):
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_event_loop()

    async def update_one(gene_id: int):
        # Each gets its own session
        with transactional_context() as db:
            await update_gene(db, gene_id)

    # Run in parallel
    await asyncio.gather(
        *[update_one(gene_id) for gene_id in genes],
        return_exceptions=True  # Don't fail entire batch on one error
    )
```

---

### Error #3: WebSocket Communication Failures
**Frequency**: 2 occurrences
**Impact**: Real-time progress updates fail
**Status**: Minor, non-blocking

#### Details
```
Logger: app.api.endpoints.progress
Message: Failed to send to websocket
Type: RuntimeError
```

**Likely Causes**:
- Client disconnected before message could be sent
- Network timeout
- WebSocket connection closed prematurely

**Impact**: Low - Progress updates are convenience feature, not critical

**Fix**: Already has error handling (doesn't crash the app), but could improve:

```python
# Current behavior
try:
    await websocket.send_json(message)
except RuntimeError as e:
    await logger.error("Failed to send to websocket", error=e)

# Better behavior
try:
    await websocket.send_json(message)
except RuntimeError as e:
    await logger.warning("Client disconnected, skipping message",
                        client_id=client_id,
                        message_type=message.get("type"))
    # Clean up client from active connections
    await remove_client(client_id)
```

---

## 🟡 MEDIUM PRIORITY ERRORS

### Error #4: Percentile Service Issues
**Frequency**: 3 occurrences
**Impact**: Statistics calculations may be incorrect
**Status**: Requires monitoring

#### Occurrences

1. **All percentiles identical** (1x)
   ```
   ALERT: All percentiles identical for test - calculation may be broken
   ```

2. **Calculation timeout** (1x)
   ```
   Percentile calculation timed out for test
   ```

3. **Validation failure** (1x)
   ```
   Percentile validation failed for test
   ```

#### Analysis

The percentile service (`app.core.percentile_service`) is showing signs of calculation issues. This could indicate:
- Data distribution problems (all values the same)
- Performance issues (timeouts)
- Validation logic too strict

**Investigation Needed**: Review the percentile calculation logic and test data.

---

### Error #5: Gene Deletion Failure
**Frequency**: 1 occurrence
**Impact**: Data cleanup operations may fail

```
Logger: app.api.endpoints.ingestion
Message: Failed to delete by identifier
Type: Error
```

**Needs**: More context from logs to understand what identifier failed and why.

---

### Error #6: Unknown Exception
**Frequency**: 1 occurrence
**Impact**: Unknown

```
Logger: app.core.exceptions
Message: Exception occurred
```

**Action**: Get full traceback to understand this generic error.

---

## 🟡 WARNINGS (Significant Patterns)

### Warning #1: Fallback Namespace List Used
**Frequency**: 18 occurrences
**Impact**: Cache health checks using hardcoded list
**Status**: Related to Error #1

#### Details
```
Logger: app.api.endpoints.cache
Message: Using fallback namespace list
```

**Location**: `backend/app/api/endpoints/cache.py:240`

```python
# Get namespace list dynamically from database
namespaces = await cache_service.get_distinct_namespaces()
if not namespaces:
    # Fallback to known namespaces if database query fails
    await logger.warning("Using fallback namespace list", namespaces_count=len(namespaces))
    namespaces = ["hgnc", "pubtator", "gencc", "panelapp", "hpo", "clingen", "http", "files"]
```

**Why This Happens**: The `cache_entries` table is empty or the query fails, so the code falls back to a hardcoded list.

**Fix**: This is actually working as designed (graceful fallback), but the frequency (18x) suggests the primary path fails often. Once Error #1 is fixed and cache entries exist, this warning should decrease significantly.

---

### Warning #2: Orphaned Data Source Records
**Frequency**: 22 occurrences (11 warning pairs)
**Impact**: Database contains obsolete records
**Status**: Fix documented in bug-fixes-2025-10-15.md Issue #4

#### Details
```
Logger: app.core.startup
Message: Found orphaned data source records
Additional: orphaned_names=['annotation_pipeline']

Logger: app.core.startup
Message: Orphaned records found but not automatically removed
Additional: action_required=Review and manually remove if no longer needed
```

**Fix**: Delete the orphaned record:
```sql
DELETE FROM data_sources WHERE name = 'annotation_pipeline';
```

---

### Warning #3: Shadow Test Mismatches
**Frequency**: 4 occurrences
**Impact**: Test validation discrepancies
**Status**: Investigation required

```
Logger: app.core.shadow_testing
Message: Shadow test mismatch for test
```

**What is Shadow Testing?**: A/B testing or comparison between old and new implementations.

**Action**: Review shadow test configuration to understand why mismatches are occurring.

---

### Warning #4: HTTP Request Retries
**Frequency**: 5 occurrences
**Impact**: External API calls experiencing issues

#### Details
```
Logger: app.core.cached_http_client (3x)
Message: HTTP request attempt failed

Logger: app.core.retry_utils (2x)
Message: Attempt failed, retrying

Logger: app.core.retry_utils (1x)
Message: Circuit breaker opened
```

**Analysis**: The retry system is working as designed:
1. HTTP request fails
2. Retry logic kicks in
3. After multiple failures, circuit breaker opens to prevent cascade failures

**Action**: Monitor which external services are failing and investigate:
- HGNC API
- PubTator API
- GenCC API
- ClinGen API
- PanelApp API

---

### Warning #5: Database Connection Issues
**Frequency**: 1 occurrence
**Impact**: Transient connection problem

```
Logger: app.core.database
Message: Connection invalidated
```

**Status**: Single occurrence suggests transient issue, but should monitor for patterns.

---

## 📋 Issue Priority Matrix

| Priority | Issue | Occurrences | % of Total | Status |
|----------|-------|-------------|------------|--------|
| 🔴 P1 | Cache endpoint failures | 144 | 64% | Fix documented |
| 🔴 P1 | Pipeline transaction errors | 4 | 1.8% | Investigation needed |
| 🔴 P1 | WebSocket failures | 2 | 0.9% | Minor fix needed |
| 🟡 P2 | Orphaned data sources | 22 | 9.8% | Fix documented |
| 🟡 P2 | Fallback namespace list | 18 | 8% | Will resolve with P1 fix |
| 🟡 P2 | HTTP retries | 5 | 2.2% | Monitoring needed |
| 🟡 P2 | Shadow test mismatches | 4 | 1.8% | Investigation needed |
| 🟡 P2 | Percentile service errors | 3 | 1.3% | Investigation needed |
| 🟢 P3 | Other warnings | 23 | 10.2% | Normal operations |

---

## 🎯 Action Plan

### Immediate Actions (This Week)

1. **Fix Cache Endpoint Bug** (Priority 1)
   - Impact: Resolves 144 errors (64% of all issues)
   - Effort: 1-2 hours
   - Files: `backend/app/api/endpoints/cache.py`
   - Details: See `bug-fixes-2025-10-15.md` Issue #2

2. **Fix Unawaited Coroutine** (Priority 1)
   - Impact: Prevents memory leaks
   - Effort: 5 minutes
   - Files: `backend/app/core/database.py:44`
   - Details: See `bug-fixes-2025-10-15.md` Issue #1

3. **Clean Up Orphaned Record** (Priority 2)
   - Impact: Resolves 22 warnings
   - Effort: 1 minute
   - SQL: `DELETE FROM data_sources WHERE name = 'annotation_pipeline';`

### Investigation Required (Next Sprint)

4. **Pipeline Transaction Issues** (Priority 1)
   - Review error handling in pipeline code
   - Add proper rollback logic
   - Implement better connection management
   - Test parallel update scenarios

5. **Percentile Service Debug** (Priority 2)
   - Review calculation logic
   - Check test data quality
   - Add more detailed logging
   - Verify validation thresholds

6. **Shadow Test Analysis** (Priority 2)
   - Understand what tests are mismatching
   - Determine if this indicates bugs or expected differences
   - Document findings

### Monitoring (Ongoing)

7. **HTTP Retry Patterns**
   - Track which external APIs fail most often
   - Consider increasing timeout values
   - Add more detailed error messages

8. **WebSocket Stability**
   - Monitor disconnect frequency
   - Consider implementing reconnection logic
   - Add client heartbeat/ping mechanism

---

## 📈 Success Metrics

After implementing the fixes, we should see:

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Total errors (24h) | 155 | <20 | 87% reduction |
| Cache errors | 144 | 0 | 100% elimination |
| Orphan warnings | 22 | 0 | 100% elimination |
| Fallback warnings | 18 | <5 | 72% reduction |
| Pipeline errors | 4 | 0 | 100% elimination |

---

## 🔧 Technical Debt Identified

1. **Error Handling Inconsistency**
   - Some code uses try/except without proper rollback
   - Need to standardize on context managers

2. **Type Annotation Issues**
   - Several endpoints declare `AsyncSession` but use `Session`
   - Misleading for developers and IDEs

3. **Validation Logic**
   - Treating "empty" as "error" instead of valid state
   - Need better distinction between "not found" and "no data"

4. **Connection Management**
   - Possible connection pool exhaustion
   - Need better monitoring and alerting

---

## 📚 Related Documents

- [Bug Fixes Implementation Guide](./bug-fixes-2025-10-15.md)
- [Logging System Reference](../../reference/logging-system.md)
- [Non-Blocking Architecture](../../CLAUDE.md#non-blocking-patterns-critical)
- [Database Best Practices](../../architecture/database.md)
- [Pipeline Architecture](../../architecture/data-pipeline.md)

---

## 📝 Notes

- This analysis covers 24 hours of production logs
- Some warning patterns are expected (retries, fallbacks)
- Focus should be on eliminating the high-frequency errors first
- After fixes are deployed, rerun analysis to verify improvements

---

**Document Created**: 2025-10-15
**Analysis Period**: 2025-10-14 to 2025-10-15
**Next Review**: After Priority 1 fixes are deployed
**Status**: Ready for team review
