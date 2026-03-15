# Pipeline Production Readiness — Issues Found 2026-03-15

## Status: NEEDS INVESTIGATION + PLAN

All issues below were discovered during E2E testing today. The current piecemeal fix approach is creating regressions. A comprehensive plan is needed.

## Critical Issues (Blocking Production)

### 1. Annotation pipeline only runs string_ppi
- **Symptom**: `sources_updated: 1`, only `string_ppi` has data after "full" + "force" annotation run
- **Impact**: 9 of 10 annotation sources (hgnc, ensembl, gnomad, clinvar, hpo, uniprot, gtex, descartes, mpo_mgi) never run
- **Status**: NOT FIXED — needs investigation of AnnotationPipeline source selection logic
- **Location**: `backend/app/pipeline/annotation_pipeline.py`

### 2. Orchestrator doesn't survive backend restarts
- **Symptom**: After restart, completed evidence sources don't re-fire `on_source_completed`, so annotations never trigger
- **Root cause**: `_completed_sources` set is in-memory only, lost on restart
- **Impact**: Manual annotation trigger needed after every restart
- **Fix needed**: Check DB for completed sources on startup, or persist orchestrator state

### 3. PubTator keyword search takes 30+ minutes (5,734 pages)
- **Symptom**: PubTator runs through 5,734 pages at 3 req/sec = ~32 minutes
- **Impact**: Blocks annotations from starting (orchestrator waits for all sources)
- **Question**: Is 5,734 pages correct? Should smart mode's `max_pages: 500` be applied?

### 4. Frontend shows 0 genes during pipeline execution
- **Symptom**: Home page shows "0 Genes with Evidence" until aggregation + view refresh runs
- **Impact**: Users see empty database for 30+ minutes on first startup
- **Partial fix**: Orchestrator runs early aggregation after seeding, but only if all sources complete

## Fixed Issues (Today)

| Issue | Commit | Description |
|-------|--------|-------------|
| HTTP redirects | `60d62e5` | CachedHttpClient follow_redirects=True |
| GenCC URL | `bafd460` | Configurable download URL |
| 0-gene completion | `4425ff7` | Mark as failed instead of completed |
| Tracker idempotent | `f6c32ff` | start() skips reset if already running |
| Pipeline orchestrator | `044bf6f` | 3-stage DAG: evidence→annotations→aggregation |
| Initial seeder | `7d098ed` | Merge all files per source + create genes |
| Auth persistence | `e807a86` | Router guard awaits initReady |
| Tracker stats | `e807a86` | Update items_added/updated/failed per batch |
| Pipeline UI | `ed0dd7e` | Stable tile order, WebSocket fix, hybrid section |
| DiagnosticPanels progress | `4414378` | Remove exclusion from tracking |
| Gene-centric removal | `c8607fc` | Revert to keyword search |
| Progress percentage | `578861e` | Don't recalculate on completed status |
| Auth interceptor | `b4cbdbc` | Only refresh on authenticated requests |
| Transaction rollback | `9b97dcc` | Rollback broken transactions in batches |
| Frontend lint | `e3b7be8` | 0 warnings across all files |
| Aggregation + views | `eb1abfd` | Run after seeding, refresh gene_scores |

## Commits on Branch (refactor/migration-squash)

Total: 18 new commits since plan started
