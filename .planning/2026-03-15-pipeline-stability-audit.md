# Pipeline Stability Audit Report — 2026-03-15

> Deep investigation of all pipeline issues found during E2E testing.
> Each issue includes root cause, affected files, and recommended fix.

---

## Issue 1: Annotation Pipeline Only Runs string_ppi (9/10 Sources Skipped)

**Severity**: CRITICAL — annotations are the core value-add of the database

### Root Cause

The annotation pipeline's `INCREMENTAL` strategy uses `AnnotationSource.is_update_due()` to decide which sources to run. But there's a cascading bug:

1. **`next_update` never set on init**: `init_annotation_sources.py:131` creates `AnnotationSource` records without setting `next_update` → defaults to NULL
2. **`is_update_due()` returns True for NULL**: `gene_annotation.py:112-116` treats NULL `next_update` as "due" — correct
3. **`next_update` only set when `successful > 0`**: `annotation_pipeline.py:828-833` only updates `next_update` when at least one gene annotation succeeds
4. **INCREMENTAL gene selection filters out completed genes**: `annotation_pipeline.py:417-429` uses `HAVING count(annotations) < len(sources)` to find genes needing updates. If a previous run annotated most genes, this returns very few/no genes
5. **Result**: Sources run but find 0 genes to update → `successful = 0` → `next_update` stays NULL → stuck in permanent loop of "due but nothing to do"

### Why string_ppi Works

string_ppi likely has genes that still need its annotations (it was added later or has different coverage patterns).

### Why force=true Didn't Help

The API endpoint at `annotation_updates.py` **ignores the request body** — it reads `strategy` and `force` from query parameters, not JSON body. The curl request sent JSON body but the endpoint uses `Query()` parameters:

```python
# What the endpoint expects:
POST /api/annotations/pipeline/update?strategy=full&force=true

# What was sent:
POST /api/annotations/pipeline/update  body: {"strategy": "full", "force": true}
```

### Affected Files

| File | Line | Issue |
|------|------|-------|
| `backend/app/scripts/init_annotation_sources.py` | 131 | No `next_update` on init |
| `backend/app/pipeline/annotation_pipeline.py` | 828 | Only sets `next_update` when `successful > 0` |
| `backend/app/pipeline/annotation_pipeline.py` | 417-429 | INCREMENTAL filters out already-annotated genes |
| `backend/app/models/gene_annotation.py` | 112-116 | `is_update_due()` NULL handling |
| `backend/app/api/endpoints/annotation_updates.py` | ~line 50 | Reads strategy/force from Query, not Body |

### Recommended Fix

1. **Always set `next_update`** after pipeline run, regardless of success count:
   ```python
   # annotation_pipeline.py:828 - remove the `if successful > 0` guard
   source_record.last_update = datetime.utcnow()
   source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
   ```

2. **Fix FULL strategy** to ignore `is_update_due()` and process ALL genes regardless

3. **Fix the API endpoint** to also accept JSON body parameters (or document that it uses query params)

---

## Issue 2: Orchestrator Loses State on Backend Restart

**Severity**: HIGH — annotations never trigger after any restart

### Root Cause

The orchestrator tracks completed sources in `_completed_sources: set[str]` (in-memory). On restart:

1. `reset_stale_running_status()` converts `running` → `paused`
2. New `PipelineOrchestrator` created with empty `_completed_sources = set()`
3. `start_pipeline()` sets stage to EVIDENCE, calls `start_auto_updates()`
4. `start_auto_updates()` only starts `idle`/`failed`/`paused` sources — skips `completed`
5. Completed sources never fire `on_source_completed()` callback
6. Orchestrator waits forever for all 5 sources, but 4 are already done
7. **DEADLOCK**: Annotations never trigger

### Affected Files

| File | Line | Issue |
|------|------|-------|
| `backend/app/core/pipeline_orchestrator.py` | 52-56 | In-memory only state |
| `backend/app/core/pipeline_orchestrator.py` | 65 | `start_pipeline()` clears sets |
| `backend/app/core/background_tasks.py` | 39-63 | `start_auto_updates()` skips completed |
| `backend/app/main.py` | 113-125 | Creates fresh orchestrator each time |

### Recommended Fix

Add `_load_state_from_db()` to orchestrator init:

```python
def _load_state_from_db(self) -> None:
    """Reconstruct completed/failed state from database."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        for source_name in self.EVIDENCE_SOURCES:
            progress = db.query(DataSourceProgress)\
                .filter_by(source_name=source_name).first()
            if progress:
                if progress.status == SourceStatus.completed:
                    self._completed_sources.add(source_name)
                elif progress.status == SourceStatus.failed:
                    self._failed_sources.add(source_name)
    finally:
        db.close()
```

Then in `start_pipeline()`, check if all sources are already done before waiting:

```python
async def start_pipeline(self) -> None:
    self._load_state_from_db()
    # ... existing logic ...
    # If all sources already completed from a previous run, skip to next stage
    if (self._completed_sources | self._failed_sources) >= set(self.EVIDENCE_SOURCES):
        await self._advance_to_annotations()
        return
    await self.task_manager.start_auto_updates()
```

---

## Issue 3: PubTator Smart Mode Not Working (5,734 Pages Instead of 500)

**Severity**: HIGH — 32 minutes instead of ~3 minutes

### Root Cause (Three Bugs)

**Bug 1**: Early stopping threshold is hardcoded to `> 100` consecutive duplicate pages, not the configured `consecutive_pages: 3`
- **File**: `pubtator.py:487` — `if consecutive_duplicates > 100`
- **Should be**: `if consecutive_duplicates >= self.smart_consecutive_pages`

**Bug 2**: Mode-specific `max_pages` is never loaded from config
- Config defines `smart_update.max_pages: 500` but the source only reads the top-level `max_pages: null`
- The mode-specific config is never applied

**Bug 3**: Duplicate detection rarely triggers with score-sorted results
- PubTator API sorts by score descending
- New high-score results appear at the top of later pages
- Consecutive pages rarely hit 90% duplicate threshold

### Affected Files

| File | Line | Issue |
|------|------|-------|
| `backend/app/pipeline/sources/unified/pubtator.py` | 487 | Hardcoded `> 100` threshold |
| `backend/app/pipeline/sources/unified/pubtator.py` | 80 | Only reads top-level `max_pages` |
| `backend/config/datasources.yaml` | 37-40 | Smart config defined but never used |

### Recommended Fix

1. Load mode-specific max_pages in `update_data()`:
   ```python
   if mode == "smart":
       effective_max_pages = get_source_parameter("PubTator", "smart_update.max_pages", 500)
   else:
       effective_max_pages = self.max_pages  # null = unlimited
   ```

2. Fix early stopping threshold:
   ```python
   consecutive_threshold = get_source_parameter("PubTator", "smart_update.consecutive_pages", 3)
   if mode == "smart" and consecutive_duplicates >= consecutive_threshold:
       break
   ```

---

## Issue 4: Frontend Shows "0 Genes" During Pipeline Execution

**Severity**: MEDIUM — bad UX but data is correct after pipeline completes

### Root Cause

The Home page calls `GET /api/datasources/` which counts genes using:
```sql
SELECT COUNT(DISTINCT ge.gene_id)
FROM gene_evidence ge
INNER JOIN gene_scores gs ON gs.gene_id = ge.gene_id
WHERE gs.percentage_score > 0
```

This `INNER JOIN gene_scores` requires the materialized view to be refreshed. During pipeline execution:
- `gene_evidence` has new genes (populated by evidence sources)
- `gene_scores` is stale (last refreshed from previous run)
- INNER JOIN eliminates all new genes → count = 0

### Dependency Chain

```
Home.vue → datasources API → gene_filters.py → gene_scores (materialized view)
                                                     ↓ depends on
                                              combined_evidence_scores (view)
                                                     ↓ depends on
                                              evidence_normalized_scores (view)
                                                     ↓ depends on
                                              evidence_count_percentiles (view)
                                                     ↓ depends on
                                              gene_curations (table - needs aggregation)
```

### Affected Files

| File | Line | Issue |
|------|------|-------|
| `frontend/src/views/Home.vue` | 204-206 | Displays `total_unique_genes` from API |
| `backend/app/api/endpoints/datasources.py` | 268-269 | Queries via gene_filters |
| `backend/app/core/gene_filters.py` | 90-107 | INNER JOIN on gene_scores |
| `backend/app/db/views.py` | 237-307 | gene_scores materialized view |

### Recommended Fix

**Option A (Quick)**: Use `LEFT JOIN` or count from `gene_evidence` directly when `gene_scores` is empty:
```sql
-- Fallback when gene_scores has no data
SELECT COUNT(DISTINCT gene_id) FROM gene_evidence
```

**Option B (Better)**: Run aggregation + view refresh after EACH evidence source completes (not just after all 5). This gives progressive visibility.

**Option C (Best)**: Decouple the Home page stats from the materialized view — count directly from `gene_evidence` for the "Genes with Evidence" stat.

---

## Issue 5: Progress Bars Show Wrong Percentage for Completed Sources

**Severity**: LOW — cosmetic, fixed for future runs

### Root Cause (FIXED)

`_commit_and_broadcast()` recalculated `progress_percentage` from `current_item/total_items` before every commit, overwriting the 100% set by `complete()`.

**Fix applied**: Commit `578861e` — only recalculate when `status == running`.

**Remaining issue**: Sources completed before the fix still have stale percentages in DB. These need a one-time DB update or will correct on next run.

---

## Issue 6: Auth Session Lost on Backend Restart

**Severity**: MEDIUM — users have to re-login after every restart

### Root Cause

Refresh tokens are stored in the `users.refresh_token` column. On backend restart, the refresh token cookie in the browser is still valid, but:
1. The backend creates a new process
2. The old refresh token in the cookie matches the DB record (this part works)
3. BUT: if the backend crashed and didn't commit the token, or if the token was rotated, the mismatch causes 401

Additionally, the 401 interceptor was too aggressive — triggering on public endpoints.

**Fix applied**: Commit `b4cbdbc` — only attempt refresh on authenticated requests.

**Remaining issue**: Backend restarts still invalidate sessions if the token rotation doesn't match.

---

## Issue 7: Transaction Rollback Not Handled in Batch Processing

**Severity**: HIGH — causes PubTator to crash mid-run

### Root Cause (FIXED)

When a DB query fails mid-batch (e.g., connection drop during long PubTator runs), SQLAlchemy enters `PendingRollbackError` state. All subsequent queries fail until `rollback()` is called. Neither PubTator nor the base `DataSourceClient` handled this.

**Fix applied**: Commit `9b97dcc` — rollback after individual gene errors AND wrap batch commits with recovery.

---

## Issue 8: WebSocket Progress Updates Not Arriving in Frontend

**Severity**: MEDIUM — fixed

### Root Cause (FIXED)

Backend wraps progress updates in arrays (`[data]`), but frontend handler expected a single object. `data.source_name` was `undefined` on an array.

**Fix applied**: Commit `ed0dd7e` — unwrap array in handler.

---

## Summary: Priority Order for Fixes

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| **P0** | #1 Annotations skip 9/10 sources | No annotations = unusable DB | Medium |
| **P0** | #2 Orchestrator restart deadlock | Requires manual intervention | Small |
| **P1** | #3 PubTator 32min instead of 3min | Blocks pipeline completion | Small |
| **P1** | #4 Frontend shows 0 during pipeline | Bad first impression | Medium |
| **P2** | #5 Progress bars wrong % | Cosmetic | Done (future runs) |
| **P2** | #6 Auth lost on restart | Annoying but not blocking | Medium |
| **Done** | #7 Transaction rollback | Was crashing PubTator | Done |
| **Done** | #8 WebSocket format mismatch | Stats not updating | Done |

---

## Already Fixed Today (18 commits)

| Commit | Fix |
|--------|-----|
| `60d62e5` | CachedHttpClient follow_redirects |
| `bafd460` | GenCC configurable download URL |
| `4425ff7` | 0-gene results marked as failed |
| `f6c32ff` | tracker.start() idempotent |
| `044bf6f` | Pipeline orchestrator (3-stage DAG) |
| `1e99a48` | Wire orchestrator into startup |
| `8238f42` | Initial seeder for DiagnosticPanels/Literature |
| `17d1d02` | Auto-seed on empty DB |
| `7abb034` | Move seeding after evidence sources |
| `470c382` | Handle CancelledError in callbacks |
| `1bbc0e8` | Fix mypy no-any-return errors |
| `7d098ed` | Seeder: merge all files + create genes |
| `eb1abfd` | Run aggregation + refresh views after seeding |
| `e807a86` | Auth persistence + tracker stats |
| `ed0dd7e` | Pipeline UI: stable tiles, WebSocket fix |
| `4414378` | DiagnosticPanels progress tracking |
| `c8607fc` | Remove gene-centric PubTator mode |
| `578861e` | Progress percentage fix |
| `b4cbdbc` | Auth interceptor fix |
| `9b97dcc` | Transaction rollback in batches |
| `e3b7be8` | Frontend lint: 0 warnings |
