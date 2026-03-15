# Pipeline Stability Audit — 2026-03-15

> Critical issues found during E2E testing. Fixes applied where possible.

## Status Summary

| # | Issue | Status | Commit |
|---|-------|--------|--------|
| 1 | Annotations skip 9/10 sources | **FIXED** | `48e1eb6` |
| 2 | Orchestrator restart deadlock | **FIXED** | `5115414` |
| 3 | Frontend shows 0 during pipeline | **FIXED** (fallback) | `0219ff6` |
| 4 | PubTator transaction crash | **FIXED** | `a619519` |
| 5 | Progress bars wrong % | **FIXED** | `578861e` |
| 6 | Annotation pipeline starves DB pool | **KNOWN** | Needs ARQ worker |
| 7 | Stale annotation checkpoint | **WORKAROUND** | Clear metadata manually |
| 8 | PubTator smart mode (re-runs) | **KNOWN** | P2 for future |

## Issue 6: Annotation Pipeline Starves DB Connection Pool (BLOCKING)

**Severity**: CRITICAL — frontend completely unresponsive during annotations

The annotation pipeline creates multiple `SessionLocal()` instances (one per source, one for views, one for HGNC, plus ThreadPoolExecutor workers). With 10 sources + 2 thread workers + progress tracker, it can hold 15+ connections, exhausting the pool (15+20=35 max). API requests hang waiting for connections.

**Root cause**: Pipeline runs in-process via FastAPI BackgroundTasks, sharing the same connection pool as the API.

**Solution**: Run annotation pipeline in the ARQ worker process (`USE_ARQ_WORKER=true` + `make worker`). This gives it a separate process with its own connection pool, completely isolating it from API connections.

**Workaround**: Increase `pool_size` and `max_overflow` (already done: 15+20). Still not enough when all annotation sources run concurrently.

## All Commits on This Branch

| Commit | Description |
|--------|-------------|
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
| `48e1eb6` | Annotations: run ALL sources, accept JSON body |
| `5115414` | Orchestrator: survive restarts via DB state |
| `0219ff6` | Datasources: fallback count when views stale |
| `4736c39` | DB pool size increase |
| `a619519` | PubTator: handle DB errors in PMID check |
