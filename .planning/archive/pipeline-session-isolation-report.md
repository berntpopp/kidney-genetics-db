# Pipeline Session Isolation Bug Report

**Date**: 2026-03-03
**Severity**: HIGH — causes cascading failures during full pipeline runs
**Component**: `backend/app/pipeline/annotation_pipeline.py`

---

## 1. Problem

During a full `strategy=full&force=true` pipeline run (5,080 genes, 10 sources), Phase 2 parallel sources fail with cascading SQLAlchemy session errors:

```
Error in parallel update for gnomad: Can't reconnect until invalid transaction is rolled back.
Error in parallel update for hpo: This session is in 'prepared' state; no further SQL can be emitted within this transaction.
Error in parallel update for clinvar: This session is in 'prepared' state
Error in parallel update for ensembl: This session is in 'prepared' state
Error in parallel update for uniprot: This session is in 'prepared' state
Error in parallel update for mpo_mgi: Can't reconnect until invalid transaction is rolled back.
Failed to refresh materialized view gene_scores: This session is in 'prepared' state
Failed to refresh materialized view gene_annotations_summary: InFailedSqlTransaction
```

**Result**: Only 5/10 sources updated successfully. The remaining 5 kept stale data from a previous run. Materialized views also failed to refresh.

---

## 2. Root Cause

**A single SQLAlchemy `Session` is shared across all parallel source updates.**

### The current architecture

```python
# annotation_pipeline.py line 52
class AnnotationPipeline:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session          # ← ONE session for entire pipeline

# line 561-608: parallel execution
async def _update_sources_parallel(self, sources, gene_ids, force):
    semaphore = asyncio.Semaphore(3)  # Up to 3 concurrent tasks

    async def rate_limited_update(source_name):
        async with semaphore:
            self.db.execute(text("SELECT 1"))  # ← SHARED session
            self.db.commit()                    # ← SHARED session
            result = await self._update_source_with_recovery(source_name, ...)
            return (source_name, result)

    tasks = [rate_limited_update(src) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

Each parallel source is initialized with the same session reference:

```python
# line 647
source = source_class(self.db)  # ← Same session object
```

### Why this fails

SQLAlchemy sessions are **not safe for concurrent use**. From the official docs:

> The Session lifecycle should be scoped to a logical unit of work. Each concurrent task/thread must have its own Session.

When 3 sources run concurrently via `asyncio.gather`:

1. **Source A** calls `self.db.commit()` — session enters transient "prepared" state
2. **Source B** tries `self.db.execute(...)` while session is still committing
3. SQLAlchemy raises `InvalidRequestError: session is in 'prepared' state`
4. The session's underlying connection enters an aborted transaction state
5. **All remaining tasks** fail with `Can't reconnect until invalid transaction is rolled back`
6. The pipeline's cleanup code (materialized view refresh) also fails because it uses the same poisoned session

### Connection pool interaction

The engine uses `pool_reset_on_return="rollback"` (correct for safety), but this means:
- If one task triggers a connection return to the pool, the pool rolls it back
- Other tasks still referencing the session see an invalidated connection
- This explains the alternating "prepared state" and "can't reconnect" errors

---

## 3. Impact

| Category | Current Behavior | Expected Behavior |
|----------|-----------------|-------------------|
| Source updates | 5/10 succeed per run | 10/10 succeed |
| Materialized views | Fail to refresh | Refresh after all sources |
| Data freshness | Stale for failed sources | All sources current |
| Idempotency | Must run pipeline multiple times | Single run completes all |
| Error blast radius | One source failure kills all concurrent | Isolated failures |

---

## 4. Proposed Fix

### Strategy: Session-per-source

Each parallel source gets its own `SessionLocal()` instance. The main pipeline session is only used for orchestration (progress tracking, checkpoint management).

### 4.1 Core change: `_update_sources_parallel()`

**File**: `annotation_pipeline.py`, `_update_sources_parallel` method

```python
async def _update_sources_parallel(
    self, sources: list[str], gene_ids: list[int], force: bool = False
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(3)

    async def rate_limited_update(source_name: str) -> tuple[str, dict]:
        async with semaphore:
            # NEW: Each source gets its own session
            source_db = SessionLocal()
            try:
                # Health check on the NEW session
                source_db.execute(text("SELECT 1"))
                source_db.commit()

                result = await self._update_source_with_session(
                    source_name, gene_ids, force, source_db
                )
                return (source_name, result)
            except Exception as e:
                source_db.rollback()
                raise
            finally:
                source_db.close()

    tasks = [rate_limited_update(src) for src in sources]
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    # ... process results ...
```

### 4.2 New method: `_update_source_with_session()`

Extract the source update logic to accept an explicit session parameter instead of using `self.db`:

```python
async def _update_source_with_session(
    self, source_name: str, gene_ids: list[int],
    force: bool, db: Session
) -> dict[str, Any]:
    """Run a single source update with its own dedicated session."""
    # Fetch genes using the source-local session
    genes = db.query(Gene).filter(Gene.id.in_(gene_ids)).all()
    db.commit()  # Release read lock

    # Initialize source with its own session
    source = source_class(db)
    source.batch_mode = True

    # ... existing fetch_batch / store_annotation logic ...
    # All operations use `db` (the source-local session)

    db.commit()  # Final commit for this source
    return result
```

### 4.3 Keep `self.db` for orchestration only

The main `self.db` session continues to be used for:
- Progress tracker updates (`data_source_progress` table)
- Checkpoint saves/restores
- Materialized view refreshes (after all sources complete)

This is safe because these operations are sequential (not concurrent).

### 4.4 Materialized view refresh with fresh session

The view refresh should also use a fresh session to avoid inheriting any state from the parallel phase:

```python
async def _refresh_views(self):
    """Refresh materialized views with a dedicated session."""
    view_db = SessionLocal()
    try:
        for view_name in view_names:
            await run_in_threadpool(
                lambda: view_db.execute(
                    text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                )
            )
            view_db.commit()
    except Exception as e:
        view_db.rollback()
        raise
    finally:
        view_db.close()
```

---

## 5. Connection Pool Considerations

With session-per-source, peak concurrent connections increases:

| Component | Connections |
|-----------|----------:|
| Main pipeline session (orchestration) | 1 |
| Parallel sources (Semaphore=3) | 3 |
| Web requests (concurrent users) | ~2-5 |
| Background scheduler | 1 |
| **Peak total** | **~10** |

Current pool config (`pool_size=10, max_overflow=15` = 25 max) handles this comfortably.

---

## 6. Implementation Checklist

1. **Import `SessionLocal`** in `annotation_pipeline.py`
2. **Create session-per-source** in `_update_sources_parallel()` — each `rate_limited_update` creates and closes its own session
3. **Extract `_update_source_with_session()`** that takes an explicit `db` parameter
4. **Pass source-local session** to `source_class(db)` instead of `self.db`
5. **Add rollback + close** in `finally` block for each source session
6. **Fresh session for view refresh** — don't reuse `self.db` after parallel phase
7. **Update bulk upsert** (`_bulk_upsert_annotations`) to use the passed session, not `self.db`
8. **Add error isolation** — log but continue if one source fails, don't propagate to others
9. **Update tests** — mock `SessionLocal` factory, verify each source gets its own session
10. **Connection pool monitoring** — log `engine.pool.status()` at pipeline start/end

---

## 7. Testing Plan

| Test | Validates |
|------|----------|
| `test_parallel_sources_get_separate_sessions` | Each source receives a unique session instance |
| `test_source_failure_does_not_cascade` | One source error doesn't affect others |
| `test_materialized_views_refresh_after_partial_failure` | Views refresh even if some sources failed |
| `test_session_cleanup_on_source_error` | Session is rolled back and closed after error |
| `test_connection_pool_not_exhausted` | Pool connections returned after each source completes |

---

## 8. References

- [SQLAlchemy Session Basics — "Session lifecycle should be scoped to a logical unit of work"](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [SQLAlchemy: Parallel Session Queries (Mike Bayer)](https://github.com/sqlalchemy/sqlalchemy/discussions/10573) — "Each task must have its own Session"
- [SQLAlchemy Error: "prepared state"](https://docs.sqlalchemy.org/en/20/errors.html) — concurrent commit on shared session
- [FastAPI BackgroundTasks Session Lifecycle](https://github.com/fastapi/fastapi/discussions/10622) — never pass request session to background tasks
- [Azure PostgreSQL Connection Pooling Best Practices](https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-pooling-best-practices)
