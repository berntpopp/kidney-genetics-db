# Source Overlap Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the CROSS JOIN in the `source_overlap_statistics` materialized view with an efficient INNER JOIN, wire the view into the statistics summary endpoint, and remove deprecated dead code.

**Architecture:** The materialized view SQL is updated in-place (no migration needed — views are managed by `MaterializedViewManager`). A new CRUD method reads the pre-computed view for the summary endpoint. The filtered `/source-overlaps` endpoint remains unchanged.

**Tech Stack:** PostgreSQL materialized views, SQLAlchemy, FastAPI, pytest

---

### Task 1: Replace CROSS JOIN with efficient JOIN in materialized view

**Files:**
- Modify: `backend/app/db/materialized_views.py:54-85`

**Step 1: Replace the view definition SQL**

In `backend/app/db/materialized_views.py`, replace the `source_overlap_statistics` definition (lines 56-77) with the CTE + INNER JOIN version:

```python
        "source_overlap_statistics": MaterializedViewConfig(
            name="source_overlap_statistics",
            definition="""
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
                    NULLIF(st1.total, 0) * 100,
                    2
                )::float8 AS overlap_percentage
            FROM gene_evidence e1
            JOIN gene_evidence e2
                ON e1.gene_id = e2.gene_id
                AND e1.source_name < e2.source_name
            JOIN source_totals st1 ON st1.source_name = e1.source_name
            JOIN source_totals st2 ON st2.source_name = e2.source_name
            GROUP BY e1.source_name, e2.source_name, st1.total, st2.total
            """,
            indexes=[
                "CREATE INDEX idx_source_overlap_sources ON source_overlap_statistics(source1, source2)",
            ],
            dependencies=set(),
            refresh_strategy=RefreshStrategy.CONCURRENT,
            refresh_interval_hours=24,
        ),
```

The output schema is identical: `source1, source2, overlap_count, source1_total, source2_total, overlap_percentage`.

**Step 2: Run lint**

Run: `cd backend && uv run ruff check app/db/materialized_views.py --fix`
Expected: No errors

**Step 3: Commit**

```bash
git add backend/app/db/materialized_views.py
git commit -m "perf: replace CROSS JOIN with INNER JOIN in source_overlap_statistics view"
```

---

### Task 2: Add CRUD method to read from materialized view

**Files:**
- Modify: `backend/app/crud/statistics.py` (add method after `get_source_overlaps`, before `get_source_distributions`)

**Step 1: Write the test**

Create `backend/tests/test_statistics_crud.py`:

```python
"""Tests for statistics CRUD operations."""

import pytest
from sqlalchemy import text

from app.crud.statistics import statistics_crud


@pytest.mark.integration
class TestGetPairwiseOverlapsFromView:
    """Tests for get_pairwise_overlaps_from_view method."""

    def test_returns_list(self, db_session):
        """Method returns a list (may be empty if view has no data)."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        assert isinstance(result, list)

    def test_row_structure(self, db_session):
        """Each row has the expected keys if data exists."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        if len(result) > 0:
            row = result[0]
            assert "source1" in row
            assert "source2" in row
            assert "overlap_count" in row
            assert "source1_total" in row
            assert "source2_total" in row
            assert "overlap_percentage" in row

    def test_no_duplicate_pairs(self, db_session):
        """No (source1, source2) pair appears more than once."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        pairs = [(r["source1"], r["source2"]) for r in result]
        assert len(pairs) == len(set(pairs))

    def test_source1_less_than_source2(self, db_session):
        """source1 is always alphabetically before source2 (no duplicates)."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        for row in result:
            assert row["source1"] < row["source2"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_statistics_crud.py -v`
Expected: FAIL with `AttributeError: 'CRUDStatistics' object has no attribute 'get_pairwise_overlaps_from_view'`

**Step 3: Implement the method**

Add to `backend/app/crud/statistics.py`, inside the `CRUDStatistics` class, after `get_source_overlaps` (after line 209):

```python
    def get_pairwise_overlaps_from_view(self, db: Session) -> list[dict[str, Any]]:
        """
        Read pre-computed pairwise source overlap statistics from the materialized view.

        Returns unfiltered overlap data. For filtered queries, use get_source_overlaps() instead.
        """
        try:
            rows = db.execute(
                text(
                    "SELECT source1, source2, overlap_count, "
                    "source1_total, source2_total, overlap_percentage "
                    "FROM source_overlap_statistics "
                    "ORDER BY overlap_count DESC"
                )
            ).fetchall()
            return [
                {
                    "source1": r[0],
                    "source2": r[1],
                    "overlap_count": r[2],
                    "source1_total": r[3],
                    "source2_total": r[4],
                    "overlap_percentage": float(r[5]),
                }
                for r in rows
            ]
        except Exception as e:
            logger.sync_error("Error reading source_overlap_statistics view", error=e)
            raise
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_statistics_crud.py -v`
Expected: All 4 tests PASS (tests run against the existing dev database)

**Step 5: Lint**

Run: `cd backend && uv run ruff check app/crud/statistics.py --fix`
Expected: No errors

**Step 6: Commit**

```bash
git add backend/app/crud/statistics.py backend/tests/test_statistics_crud.py
git commit -m "feat: add get_pairwise_overlaps_from_view CRUD method with tests"
```

---

### Task 3: Wire view into statistics summary endpoint

**Files:**
- Modify: `backend/app/api/endpoints/statistics.py:250-326` (the `get_statistics_summary` function)

**Step 1: Write the test**

Add to `backend/tests/test_statistics_crud.py`:

```python
@pytest.mark.integration
class TestStatisticsSummaryEndpoint:
    """Tests for the /api/statistics/summary endpoint integration."""

    def test_summary_includes_pairwise_overlaps(self, client):
        """Summary endpoint should include pairwise_overlaps key."""
        response = client.get("/api/statistics/summary")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "pairwise_overlaps" in data

    def test_pairwise_overlaps_is_list(self, client):
        """pairwise_overlaps should be a list."""
        response = client.get("/api/statistics/summary")
        assert response.status_code == 200
        data = response.json()["data"]
        assert isinstance(data["pairwise_overlaps"], list)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_statistics_crud.py::TestStatisticsSummaryEndpoint -v`
Expected: FAIL (either `pairwise_overlaps` key missing, or `client` fixture not available — we need to check if the `client` fixture exists)

Note: If the `client` fixture is not available, skip these endpoint-level tests and rely on manual verification via `curl` or Swagger. The CRUD-level tests in Task 2 already validate the core logic.

**Step 3: Modify the summary endpoint**

In `backend/app/api/endpoints/statistics.py`, update `get_statistics_summary()`:

1. Add a fourth parallel query that reads from the materialized view:

```python
        def _get_pairwise_overlaps() -> list[dict[str, Any]]:
            with SessionLocal() as s:
                return statistics_crud.get_pairwise_overlaps_from_view(s)
```

2. Add it to the `asyncio.gather` call:

```python
        overlap_data, composition_data, distribution_data, pairwise_overlaps = (
            await asyncio.gather(
                run_in_threadpool(_get_overlaps),
                run_in_threadpool(_get_composition),
                run_in_threadpool(_get_distributions),
                run_in_threadpool(_get_pairwise_overlaps),
            )
        )
```

3. Add `pairwise_overlaps` to the summary response dict (after the `"coverage"` key):

```python
            "pairwise_overlaps": pairwise_overlaps,
```

**Step 4: Lint and typecheck**

Run: `cd backend && uv run ruff check app/api/endpoints/statistics.py --fix`
Run: `cd backend && uv run mypy app/api/endpoints/statistics.py --ignore-missing-imports`
Expected: No errors

**Step 5: Manual verification**

Start the backend (`make backend`) and verify:
- `curl http://localhost:8000/api/statistics/summary | python3 -m json.tool` — should include `pairwise_overlaps` array
- `curl http://localhost:8000/api/statistics/source-overlaps | python3 -m json.tool` — should be unchanged

**Step 6: Commit**

```bash
git add backend/app/api/endpoints/statistics.py backend/tests/test_statistics_crud.py
git commit -m "feat: include pairwise overlap data from materialized view in statistics summary"
```

---

### Task 4: Remove deprecated get_source_distributions_old method

**Files:**
- Modify: `backend/app/crud/statistics.py:300-521` (delete the method)

**Step 1: Verify no callers**

Search for `get_source_distributions_old` in the codebase (excluding archives and this plan).
Expected: Only found in `backend/app/crud/statistics.py` itself.

**Step 2: Delete the method**

Remove `get_source_distributions_old` (lines 300-521 approximately) from `backend/app/crud/statistics.py`.

**Step 3: Lint**

Run: `cd backend && uv run ruff check app/crud/statistics.py --fix`
Expected: No errors

**Step 4: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/crud/statistics.py
git commit -m "refactor: remove deprecated get_source_distributions_old method"
```

---

### Task 5: Refresh views and run full verification

**Step 1: Refresh materialized views**

Run: `make db-refresh-views`
Expected: Success, all views recreated including updated `source_overlap_statistics`

**Step 2: Run full test suite**

Run: `make test`
Expected: All tests pass

**Step 3: Run lint and format check**

Run: `make lint`
Run: `make format-check`
Expected: Clean

**Step 4: Run mypy on changed files**

Run: `cd backend && uv run mypy app/db/materialized_views.py app/crud/statistics.py app/api/endpoints/statistics.py --ignore-missing-imports`
Expected: No errors

**Step 5: Verify API responses manually**

Start backend (`make backend`) and test:
- `GET /api/statistics/summary` — includes `pairwise_overlaps` with correct data
- `GET /api/statistics/source-overlaps` — unchanged, UpSet plot data still works
- `GET /api/statistics/source-distributions` — unchanged
- `GET /api/statistics/evidence-composition` — unchanged

**Step 6: Final commit if any fixups needed**

If any verification steps required fixes, commit them now.
