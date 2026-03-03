# Design: Optimize source_overlap_statistics + Dead Code Cleanup

**Date:** 2026-03-03
**Status:** Approved
**Scope:** Backend only — materialized view SQL, statistics CRUD, statistics endpoint

## Problem

Two issues from the annotation pipeline assessment (R1):

1. **CROSS JOIN in `source_overlap_statistics`**: The materialized view creates a Cartesian product of `gene_evidence x gene_evidence` (~2.5B intermediate rows at 50K evidence rows). An INNER JOIN on `gene_id` produces only matching pairs.

2. **The view is unused**: The `/api/statistics/source-overlaps` endpoint does dynamic Python set computation instead of querying the view, because it needs per-request filtering (sources, tiers, scores). The unfiltered statistics summary could use the view.

3. **Dead code**: `get_source_distributions_old()` in `crud/statistics.py` (220 lines) was marked "will be removed after frontend migration" — migration is complete.

## Solution

### 1. Replace CROSS JOIN with efficient JOIN

**File:** `backend/app/db/materialized_views.py`

Replace the current SQL:
```sql
FROM gene_evidence s1
CROSS JOIN gene_evidence s2
WHERE s1.source_name < s2.source_name
```

With a CTE + INNER JOIN approach:
```sql
WITH source_totals AS (
    SELECT source_name, COUNT(DISTINCT gene_id) AS total
    FROM gene_evidence
    GROUP BY source_name
)
SELECT
    e1.source_name AS source1,
    e2.source_name AS source2,
    COUNT(DISTINCT e1.gene_id)::integer AS overlap_count,
    st1.total::integer AS source1_total,
    st2.total::integer AS source2_total,
    ROUND(
        COUNT(DISTINCT e1.gene_id)::numeric /
        NULLIF(st1.total, 0) * 100, 2
    )::float8 AS overlap_percentage
FROM gene_evidence e1
JOIN gene_evidence e2
    ON e1.gene_id = e2.gene_id
    AND e1.source_name < e2.source_name
JOIN source_totals st1 ON st1.source_name = e1.source_name
JOIN source_totals st2 ON st2.source_name = e2.source_name
GROUP BY e1.source_name, e2.source_name, st1.total, st2.total
```

Output schema is identical: `source1, source2, overlap_count, source1_total, source2_total, overlap_percentage`.

### 2. Wire view into statistics summary endpoint

**File:** `backend/app/crud/statistics.py`

Add `get_pairwise_overlaps_from_view()` method that reads directly from the materialized view. Used by the `/api/statistics/summary` endpoint for the unfiltered pairwise overlap data.

**File:** `backend/app/api/endpoints/statistics.py`

In `get_statistics_summary()`, include pairwise overlap data from the view in the response. The filtered `/source-overlaps` endpoint remains unchanged (dynamic computation).

### 3. Remove deprecated method

**File:** `backend/app/crud/statistics.py`

Delete `get_source_distributions_old()` (~220 lines). Verify no callers exist.

## What Does NOT Change

- `/api/statistics/source-overlaps` endpoint (filtered, dynamic computation for UpSet plot)
- Other materialized views (`gene_distribution_analysis`, `upset_plot_data`)
- Frontend components (no API contract changes)
- Cache invalidation rules for `source_overlap_statistics`
- No Alembic migration needed (views managed by `MaterializedViewManager`)

## Verification

- `make db-refresh-views` succeeds
- New view output matches old (same rows/values for identical data)
- `make test` passes
- `make lint` + mypy clean
- `/api/statistics/summary` returns pairwise overlap data
- `/api/statistics/source-overlaps` unaffected

## References

- [PostgreSQL JOIN optimization](https://geeklogbook.com/optimizing-joins-in-postgresql-practical-cases/)
- [Materialized view best practices](https://medium.com/@ShivIyer/optimizing-materialized-views-in-postgresql-best-practices-for-performance-and-efficiency-3e8169c00dc1)
- [PostgreSQL planner + explicit JOINs](https://www.postgresql.org/docs/current/explicit-joins.html)
