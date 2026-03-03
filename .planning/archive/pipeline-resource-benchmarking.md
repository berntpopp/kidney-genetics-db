# Pipeline Resource Benchmarking — COMPLETED

**Status**: Completed and merged to main (df59cbb, 2026-03-03)
**CI**: All checks passing

## What Was Done

Added lightweight resource monitoring to the annotation pipeline with an external
benchmark script. Also fixed a CI migration failure.

### Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `backend/pyproject.toml` | EDIT | Added `psutil>=5.9.0` to dev deps |
| `backend/app/core/resource_monitor.py` | CREATE | RSS/CPU checkpoint utility (psutil + /proc fallback) |
| `backend/app/pipeline/annotation_pipeline.py` | EDIT | 6 resource checkpoint calls at phase boundaries |
| `backend/scripts/benchmark_pipeline.py` | CREATE | External process monitor + JSON report generator |
| `Makefile` | EDIT | `benchmark-pipeline` and `benchmark-pipeline-fresh` targets |
| `backend/alembic/versions/15ad8825b8e5_...py` | FIX | Handle both VIEW and MATERIALIZED VIEW in migration |

### Benchmark Results (5,080 genes, 10 sources)

| Metric | Value |
|--------|-------|
| Total Duration | ~582s (9m 42s) |
| Baseline RSS | 1,182 MB |
| **Peak RSS** | **2,227 MB** (Ensembl GTF at t=336s) |
| Post-pipeline RSS | 1,471 MB |
| VPS Fitness | GOOD — 56% of 4 GB budget |

### Key Finding

The initial concern that Ensembl GTF parsing might use 4-6 GB was overstated.
Actual peak is 2.2 GB — safe for 8-GB VPS deployment without a streaming parser.

### CI Fix

Migration `15ad8825b8e5` tried `DROP VIEW IF EXISTS gene_scores` but `gene_scores`
was already a materialized view (created by `ae289b364fa1` importing current
`views.py` at runtime). Fixed by trying `DROP MATERIALIZED VIEW` first.

### Bug Fix in Benchmark Script

Added idle-detection fallback (30s CPU < 5% after sources start completing) to
handle sources that aren't re-timestamped during a pipeline run.
