# Pipeline Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize the annotation pipeline by migrating sources to bulk downloads (~4x speedup), fixing architecture bottlenecks, and validating data parity via golden file snapshots.

**Architecture:** Source-by-source migration using a `BulkDataSourceMixin` added to existing `UnifiedDataSource` classes. Each migration validated against golden file snapshots. Architecture fixes (N+1 queries, thread safety, pool alignment) integrated alongside source work.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core (bulk upserts), PostgreSQL JSONB, asyncio, cachetools, httpx

---

## Phase 0: Foundation

### Task 1: Golden File Validation Framework

**Files:**
- Create: `backend/app/pipeline/golden_file.py`
- Test: `backend/tests/pipeline/test_golden_file.py`

**Step 1: Write the failing test**

```python
# backend/tests/pipeline/test_golden_file.py
"""Tests for golden file snapshot comparison."""

import json
import math
import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
class TestGoldenFileComparison:
    """Test snapshot export and comparison logic."""

    def test_compare_identical_snapshots(self):
        """Identical snapshots produce zero diffs."""
        from app.pipeline.golden_file import compare_snapshots

        snapshot = {
            "PKD1": {
                "gnomAD": {"pLI": 0.99, "LOEUF": 0.15},
                "HGNC": {"hgnc_id": "HGNC:9008"},
            }
        }
        before = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        after = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(snapshot, before)
        json.dump(snapshot, after)
        before.close()
        after.close()

        result = compare_snapshots(Path(before.name), Path(after.name))
        assert result["total_differences"] == 0
        assert result["missing_genes"] == []
        assert result["new_genes"] == []

    def test_compare_detects_value_change(self):
        """Value changes in core fields are detected."""
        from app.pipeline.golden_file import compare_snapshots

        before_data = {"PKD1": {"gnomAD": {"pLI": 0.99}}}
        after_data = {"PKD1": {"gnomAD": {"pLI": 0.85}}}

        before = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        after = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(before_data, before)
        json.dump(after_data, after)
        before.close()
        after.close()

        result = compare_snapshots(Path(before.name), Path(after.name))
        assert result["total_differences"] > 0
        assert any(d["gene"] == "PKD1" for d in result["differences"])

    def test_compare_float_tolerance(self):
        """Float values within tolerance are treated as equal."""
        from app.pipeline.golden_file import compare_snapshots

        before_data = {"PKD1": {"gnomAD": {"pLI": 0.990000001}}}
        after_data = {"PKD1": {"gnomAD": {"pLI": 0.990000002}}}

        before = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        after = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(before_data, before)
        json.dump(after_data, after)
        before.close()
        after.close()

        result = compare_snapshots(Path(before.name), Path(after.name))
        assert result["total_differences"] == 0

    def test_compare_detects_missing_gene(self):
        """Genes present in before but not after are reported."""
        from app.pipeline.golden_file import compare_snapshots

        before_data = {"PKD1": {"gnomAD": {"pLI": 0.99}}, "PKD2": {"gnomAD": {"pLI": 0.5}}}
        after_data = {"PKD1": {"gnomAD": {"pLI": 0.99}}}

        before = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        after = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(before_data, before)
        json.dump(after_data, after)
        before.close()
        after.close()

        result = compare_snapshots(Path(before.name), Path(after.name))
        assert "PKD2" in result["missing_genes"]

    def test_compare_detects_new_gene(self):
        """Genes present in after but not before are reported."""
        from app.pipeline.golden_file import compare_snapshots

        before_data = {"PKD1": {"gnomAD": {"pLI": 0.99}}}
        after_data = {"PKD1": {"gnomAD": {"pLI": 0.99}}, "UMOD": {"gnomAD": {"pLI": 0.3}}}

        before = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        after = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(before_data, before)
        json.dump(after_data, after)
        before.close()
        after.close()

        result = compare_snapshots(Path(before.name), Path(after.name))
        assert "UMOD" in result["new_genes"]


@pytest.mark.unit
class TestGoldenFileExport:
    """Test DB export (requires db_session)."""

    def test_export_creates_file(self, db_session):
        """Export produces a valid JSON file."""
        from app.pipeline.golden_file import export_golden_snapshot

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        export_golden_snapshot(db_session, output_path)
        assert output_path.exists()

        data = json.loads(output_path.read_text())
        assert isinstance(data, dict)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_golden_file.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.pipeline.golden_file'`

**Step 3: Write implementation**

```python
# backend/app/pipeline/golden_file.py
"""
Golden file snapshot export and comparison for data parity validation.

Used during pipeline optimization to verify that bulk download migrations
produce identical core scientific values to the previous API-based approach.
"""

import json
import math
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

# Tolerance for floating-point comparisons
FLOAT_TOLERANCE = 1e-6


def export_golden_snapshot(db: Session, output_path: Path) -> dict[str, dict]:
    """
    Export gene_annotations table as a golden file snapshot.

    Groups annotations by (gene_symbol, source) and extracts core values.

    Args:
        db: Database session
        output_path: Path to write JSON snapshot

    Returns:
        The exported snapshot dict
    """
    query = text("""
        SELECT g.approved_symbol, ga.source, ga.annotations
        FROM gene_annotations ga
        JOIN genes g ON g.id = ga.gene_id
        ORDER BY g.approved_symbol, ga.source
    """)

    rows = db.execute(query).fetchall()

    snapshot: dict[str, dict] = {}
    for row in rows:
        symbol = row[0]
        source = row[1]
        annotations = row[2] or {}

        if symbol not in snapshot:
            snapshot[symbol] = {}
        snapshot[symbol][source] = annotations

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, default=str))

    logger.sync_info(
        "Golden snapshot exported",
        gene_count=len(snapshot),
        output_path=str(output_path),
    )
    return snapshot


def compare_snapshots(
    before_path: Path,
    after_path: Path,
    float_tolerance: float = FLOAT_TOLERANCE,
) -> dict[str, Any]:
    """
    Compare two golden file snapshots and report differences.

    Args:
        before_path: Path to the before snapshot JSON
        after_path: Path to the after snapshot JSON
        float_tolerance: Tolerance for float comparisons

    Returns:
        Dict with keys: total_differences, missing_genes, new_genes, differences
    """
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())

    before_genes = set(before.keys())
    after_genes = set(after.keys())

    missing_genes = sorted(before_genes - after_genes)
    new_genes = sorted(after_genes - before_genes)

    differences: list[dict[str, Any]] = []

    for gene in sorted(before_genes & after_genes):
        before_sources = before[gene]
        after_sources = after[gene]

        for source in set(before_sources.keys()) | set(after_sources.keys()):
            if source not in before_sources:
                differences.append({
                    "gene": gene,
                    "source": source,
                    "type": "source_added",
                })
                continue
            if source not in after_sources:
                differences.append({
                    "gene": gene,
                    "source": source,
                    "type": "source_removed",
                })
                continue

            diffs = _diff_values(
                before_sources[source],
                after_sources[source],
                float_tolerance=float_tolerance,
            )
            for diff in diffs:
                differences.append({
                    "gene": gene,
                    "source": source,
                    **diff,
                })

    return {
        "total_differences": len(differences) + len(missing_genes) + len(new_genes),
        "missing_genes": missing_genes,
        "new_genes": new_genes,
        "differences": differences,
    }


def generate_parity_report(comparison: dict[str, Any]) -> str:
    """Generate a human-readable parity report from a comparison result."""
    lines = ["# Golden File Parity Report", ""]

    if comparison["total_differences"] == 0:
        lines.append("**PASS**: All core values match exactly.")
        return "\n".join(lines)

    lines.append(f"**Total differences**: {comparison['total_differences']}")
    lines.append("")

    if comparison["missing_genes"]:
        lines.append(f"## Missing genes ({len(comparison['missing_genes'])})")
        for gene in comparison["missing_genes"]:
            lines.append(f"- {gene}")
        lines.append("")

    if comparison["new_genes"]:
        lines.append(f"## New genes ({len(comparison['new_genes'])})")
        for gene in comparison["new_genes"]:
            lines.append(f"- {gene}")
        lines.append("")

    if comparison["differences"]:
        lines.append(f"## Value differences ({len(comparison['differences'])})")
        for diff in comparison["differences"][:50]:  # Cap at 50 for readability
            lines.append(f"- **{diff['gene']}** ({diff['source']}): {diff.get('type', 'changed')}")
            if "path" in diff:
                lines.append(f"  - Field: `{diff['path']}`")
                lines.append(f"  - Before: `{diff.get('before')}`")
                lines.append(f"  - After: `{diff.get('after')}`")
        if len(comparison["differences"]) > 50:
            lines.append(f"  ... and {len(comparison['differences']) - 50} more")

    return "\n".join(lines)


def _diff_values(
    before: Any,
    after: Any,
    path: str = "",
    float_tolerance: float = FLOAT_TOLERANCE,
) -> list[dict[str, Any]]:
    """Recursively diff two values, returning list of differences."""
    diffs: list[dict[str, Any]] = []

    if isinstance(before, dict) and isinstance(after, dict):
        for key in set(before.keys()) | set(after.keys()):
            child_path = f"{path}.{key}" if path else key
            if key not in before:
                diffs.append({"type": "field_added", "path": child_path, "after": after[key]})
            elif key not in after:
                diffs.append({"type": "field_removed", "path": child_path, "before": before[key]})
            else:
                diffs.extend(
                    _diff_values(before[key], after[key], child_path, float_tolerance)
                )
    elif isinstance(before, (int, float)) and isinstance(after, (int, float)):
        if not math.isclose(float(before), float(after), abs_tol=float_tolerance):
            diffs.append({
                "type": "value_changed",
                "path": path,
                "before": before,
                "after": after,
            })
    elif isinstance(before, list) and isinstance(after, list):
        if sorted(str(x) for x in before) != sorted(str(x) for x in after):
            diffs.append({
                "type": "list_changed",
                "path": path,
                "before": before,
                "after": after,
            })
    elif before != after:
        diffs.append({
            "type": "value_changed",
            "path": path,
            "before": before,
            "after": after,
        })

    return diffs
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/pipeline/test_golden_file.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/pipeline/golden_file.py backend/tests/pipeline/test_golden_file.py
git commit -m "feat: add golden file validation framework for pipeline data parity"
```

---

### Task 2: BulkDataSourceMixin Base Class

**Files:**
- Create: `backend/app/pipeline/sources/unified/bulk_mixin.py`
- Test: `backend/tests/pipeline/test_bulk_mixin.py`

**Step 1: Write the failing test**

```python
# backend/tests/pipeline/test_bulk_mixin.py
"""Tests for BulkDataSourceMixin."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestBulkDataSourceMixin:
    """Test bulk download, caching, and lookup functionality."""

    def test_mixin_attributes_exist(self):
        """Mixin defines required class attributes."""
        from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

        assert hasattr(BulkDataSourceMixin, "bulk_file_url")
        assert hasattr(BulkDataSourceMixin, "bulk_cache_dir")
        assert hasattr(BulkDataSourceMixin, "bulk_cache_ttl_hours")

    @pytest.mark.asyncio
    async def test_parse_bulk_file_is_abstract(self):
        """parse_bulk_file must be implemented by subclasses."""
        from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

        mixin = BulkDataSourceMixin()
        with pytest.raises(NotImplementedError):
            await mixin.parse_bulk_file(Path("/tmp/test.tsv"))

    @pytest.mark.asyncio
    async def test_lookup_gene_from_parsed_data(self):
        """lookup_gene returns data from pre-parsed bulk dict."""
        from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

        mixin = BulkDataSourceMixin()
        mixin._bulk_data = {"PKD1": {"pLI": 0.99}, "PKD2": {"pLI": 0.5}}
        result = await mixin.lookup_gene("PKD1")
        assert result == {"pLI": 0.99}

    @pytest.mark.asyncio
    async def test_lookup_gene_returns_none_for_missing(self):
        """lookup_gene returns None for genes not in bulk data."""
        from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

        mixin = BulkDataSourceMixin()
        mixin._bulk_data = {"PKD1": {"pLI": 0.99}}
        result = await mixin.lookup_gene("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_is_bulk_cache_fresh(self):
        """Bulk cache freshness check based on file age."""
        from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

        mixin = BulkDataSourceMixin()
        mixin.bulk_cache_ttl_hours = 168

        # Non-existent file is not fresh
        assert not mixin._is_bulk_cache_fresh(Path("/tmp/nonexistent_file.tsv"))
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_bulk_mixin.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# backend/app/pipeline/sources/unified/bulk_mixin.py
"""
Mixin for annotation sources that support bulk file downloads.

Provides download, caching, parsing, and per-gene lookup from bulk files.
Sources using this mixin can optionally fall back to per-gene API calls
when genes are not found in the bulk data.
"""

import gzip
import hashlib
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

# Default cache directory for bulk downloads
DEFAULT_BULK_CACHE_DIR = Path("data/bulk_cache")


class BulkDataSourceMixin:
    """
    Mixin providing bulk file download and lookup capabilities.

    Sources using this mixin define:
    - bulk_file_url: URL to download the bulk file
    - bulk_cache_ttl_hours: How long to cache the downloaded file
    - bulk_file_format: File format (tsv, json, gct, txt, gz)

    Subclasses must implement:
    - parse_bulk_file(path) -> dict mapping gene keys to annotation data
    """

    bulk_file_url: str = ""
    bulk_cache_dir: Path = DEFAULT_BULK_CACHE_DIR
    bulk_cache_ttl_hours: int = 168  # 7 days
    bulk_file_format: str = "tsv"

    # Populated after parse
    _bulk_data: dict[str, dict[str, Any]] | None = None

    async def download_bulk_file(self, force: bool = False) -> Path:
        """
        Download the bulk file, using local cache if fresh.

        Args:
            force: Force re-download even if cache is fresh

        Returns:
            Path to the downloaded (or cached) file
        """
        self.bulk_cache_dir.mkdir(parents=True, exist_ok=True)

        # Generate cache filename from URL hash
        url_hash = hashlib.md5(self.bulk_file_url.encode()).hexdigest()[:12]
        filename = f"{self.__class__.__name__}_{url_hash}.{self.bulk_file_format}"
        cache_path = self.bulk_cache_dir / filename

        if not force and self._is_bulk_cache_fresh(cache_path):
            logger.sync_info(
                "Using cached bulk file",
                source=self.__class__.__name__,
                path=str(cache_path),
            )
            return cache_path

        logger.sync_info(
            "Downloading bulk file",
            source=self.__class__.__name__,
            url=self.bulk_file_url,
        )

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            response = await client.get(self.bulk_file_url)
            response.raise_for_status()

            cache_path.write_bytes(response.content)

        logger.sync_info(
            "Bulk file downloaded",
            source=self.__class__.__name__,
            size_mb=round(cache_path.stat().st_size / 1024 / 1024, 1),
            path=str(cache_path),
        )
        return cache_path

    async def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """
        Parse the bulk file into a gene-keyed dictionary.

        Must be implemented by each source subclass.

        Args:
            path: Path to the downloaded bulk file

        Returns:
            Dict mapping gene identifier (symbol or ID) to annotation data
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement parse_bulk_file()"
        )

    async def ensure_bulk_data_loaded(self, force: bool = False) -> None:
        """
        Ensure bulk data is downloaded, parsed, and loaded into memory.

        Call this at the start of a pipeline run to pre-load the bulk file.
        """
        if self._bulk_data is not None and not force:
            return

        path = await self.download_bulk_file(force=force)

        # Handle gzipped files
        if path.suffix == ".gz" or self.bulk_file_format.endswith(".gz"):
            decompressed_path = path.with_suffix("")
            if not decompressed_path.exists() or force:
                with gzip.open(path, "rb") as f_in:
                    decompressed_path.write_bytes(f_in.read())
            path = decompressed_path

        start = time.monotonic()
        self._bulk_data = await self.parse_bulk_file(path)
        elapsed = time.monotonic() - start

        logger.sync_info(
            "Bulk data parsed",
            source=self.__class__.__name__,
            gene_count=len(self._bulk_data),
            parse_time_s=round(elapsed, 2),
        )

    async def lookup_gene(self, gene_key: str) -> dict[str, Any] | None:
        """
        Look up a single gene from the parsed bulk data.

        Args:
            gene_key: Gene identifier (symbol, HGNC ID, etc.)

        Returns:
            Annotation data dict, or None if not found
        """
        if self._bulk_data is None:
            await self.ensure_bulk_data_loaded()
        return self._bulk_data.get(gene_key)  # type: ignore[union-attr]

    def _is_bulk_cache_fresh(self, cache_path: Path) -> bool:
        """Check if a cached bulk file is still within its TTL."""
        if not cache_path.exists():
            return False
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        return age_hours < self.bulk_cache_ttl_hours
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/pipeline/test_bulk_mixin.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/pipeline/sources/unified/bulk_mixin.py backend/tests/pipeline/test_bulk_mixin.py
git commit -m "feat: add BulkDataSourceMixin for bulk file download sources"
```

---

### Task 3: N+1 Subquery Fix in Gene Listing

**Files:**
- Modify: `backend/app/api/endpoints/genes.py:469-507`
- Test: Run existing tests + manual API check

**Step 1: Understand the current problem**

Read `backend/app/api/endpoints/genes.py` lines 469-507. The data query has two correlated subqueries hitting `gene_evidence` per row:
1. `COUNT(*)` subquery (line 478)
2. `array_agg(DISTINCT source_name)` subquery (line 497-501)

These cause N+1 performance issues for every page of results.

**Step 2: Write the fix**

Replace the correlated subqueries with a pre-aggregated CTE that JOINs once:

Replace lines 469-507 in `backend/app/api/endpoints/genes.py`:

```sql
-- BEFORE (N+1 subqueries):
SELECT g.id, ...,
    COALESCE((SELECT COUNT(*) FROM gene_evidence WHERE gene_id = g.id), 0) as evidence_count,
    COALESCE((SELECT array_agg(DISTINCT source_name ...) FROM gene_evidence WHERE gene_id = g.id), ...) as sources
FROM genes g LEFT JOIN gene_scores gs ON gs.gene_id = g.id

-- AFTER (single CTE + JOIN):
WITH evidence_agg AS (
    SELECT gene_id,
           COUNT(*) as evidence_count,
           array_agg(DISTINCT source_name ORDER BY source_name) as sources
    FROM gene_evidence
    GROUP BY gene_id
)
SELECT g.id, ...,
    COALESCE(ea.evidence_count, 0) as evidence_count,
    COALESCE(ea.sources, ARRAY[]::text[]) as sources
FROM genes g
LEFT JOIN gene_scores gs ON gs.gene_id = g.id
LEFT JOIN evidence_agg ea ON ea.gene_id = g.id
```

The full replacement query string:

```python
    data_query = f"""
        WITH evidence_agg AS (
            SELECT gene_id,
                   COUNT(*) as evidence_count,
                   array_agg(DISTINCT source_name ORDER BY source_name) as sources
            FROM gene_evidence
            GROUP BY gene_id
        )
        SELECT
            g.id,
            g.hgnc_id,
            g.approved_symbol,
            g.aliases,
            g.created_at,
            g.updated_at,
            COALESCE(ea.evidence_count, 0) as evidence_count,
            gs.percentage_score as evidence_score,
            gs.evidence_tier,
            gs.evidence_group,
            CASE gs.evidence_tier
                WHEN 'comprehensive_support' THEN 1
                WHEN 'multi_source_support' THEN 2
                WHEN 'established_support' THEN 3
                WHEN 'preliminary_evidence' THEN 4
                WHEN 'minimal_evidence' THEN 5
                ELSE 999
            END as tier_sort_order,
            CASE gs.evidence_group
                WHEN 'well_supported' THEN 1
                WHEN 'emerging_evidence' THEN 2
                ELSE 999
            END as group_sort_order,
            COALESCE(ea.sources, ARRAY[]::text[]) as sources
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        LEFT JOIN evidence_agg ea ON ea.gene_id = g.id
        WHERE {where_clause}
        {sort_clause}
    """
```

**Step 3: Run existing tests**

Run: `cd backend && uv run pytest tests/test_genes_api.py -v`
Expected: All existing gene API tests PASS

**Step 4: Manual API check**

Run: `curl -s http://localhost:8000/api/genes?page=1&size=10 | python3 -m json.tool | head -50`
Verify: Response structure unchanged, evidence_count and sources fields populated correctly.

**Step 5: Commit**

```bash
git add backend/app/api/endpoints/genes.py
git commit -m "perf: replace N+1 subqueries with CTE in gene listing endpoint"
```

---

### Task 4: Thread Safety — ARQ Pool Lock

**Files:**
- Modify: `backend/app/core/arq_client.py:20-34`

**Step 1: Read the current code**

Read `backend/app/core/arq_client.py`. The `_arq_pool` global at line 20 has no lock around initialization (lines 30-33). Under concurrent async calls, two event loops could both see `_arq_pool is None` and create duplicate pools.

**Step 2: Add asyncio.Lock**

```python
# backend/app/core/arq_client.py - Replace lines 19-34
import asyncio

# Global pool instance (lazy initialized)
_arq_pool: ArqRedis | None = None
_arq_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    """
    Get or create the ARQ Redis connection pool.

    Thread-safe: uses asyncio.Lock to prevent duplicate pool creation.

    Returns:
        ArqRedis connection pool
    """
    global _arq_pool
    if _arq_pool is None:
        async with _arq_pool_lock:
            if _arq_pool is None:
                logger.sync_info("Creating ARQ Redis connection pool", redis_url=settings.REDIS_URL)
                _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool
```

**Step 3: Run existing tests**

Run: `cd backend && uv run pytest tests/ -k "arq" -v`
Expected: Any existing ARQ tests still pass.

**Step 4: Commit**

```bash
git add backend/app/core/arq_client.py
git commit -m "fix: add asyncio.Lock to ARQ pool singleton to prevent duplicate creation"
```

---

### Task 5: Thread Pool / Connection Pool Alignment

**Files:**
- Modify: `backend/app/core/database.py:45-46` (thread pool)
- Modify: `backend/app/core/database.py:66-67` (connection pool)

**Step 1: Adjust pool sizes**

In `backend/app/core/database.py`:

1. Line 46: Change `max_workers=4` to `max_workers=10`
2. Line 66: Change `pool_size=20` to `pool_size=10`
3. Line 67: Change `max_overflow=30` to `max_overflow=15`

This aligns the thread pool (10 workers) with the connection pool (10+15=25 max) so workers can always get a connection.

**Step 2: Run existing tests**

Run: `cd backend && uv run pytest tests/ -v --timeout=60`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add backend/app/core/database.py
git commit -m "perf: align thread pool (10) with connection pool (10+15) to prevent deadlocks"
```

---

### Task 6: Replace `inspect.stack()` with `asyncio.get_running_loop()`

**Files:**
- Modify: `backend/app/pipeline/sources/unified/base.py` (find `inspect.stack()` usage)

**Step 1: Find and read the usage**

Run: `cd backend && grep -n "inspect.stack\|inspect\.currentframe" app/pipeline/sources/unified/base.py`

Locate the `_invalidate_api_cache_sync` or similar method that uses stack inspection to detect async context.

**Step 2: Replace with zero-cost async detection**

```python
# Replace any inspect.stack() based async detection with:
import asyncio

def _is_async_context() -> bool:
    """Detect whether we're running inside an async event loop."""
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False
```

**Step 3: Remove `import inspect` if no longer used**

**Step 4: Run tests**

Run: `cd backend && uv run pytest tests/ -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/app/pipeline/sources/unified/base.py
git commit -m "perf: replace inspect.stack() with asyncio.get_running_loop() for async detection"
```

---

### Task 7: Functional Index for Gene Symbol Lookups

**Files:**
- Create: `backend/alembic/versions/xxxx_add_upper_symbol_index.py`

**Step 1: Generate migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "add functional index on upper approved_symbol"`

**Step 2: Edit migration to add the functional index**

```python
from alembic import op

def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS idx_gene_symbol_upper ON genes (UPPER(approved_symbol))")

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_gene_symbol_upper")
```

**Step 3: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Verify index exists**

Run: `psql -c "SELECT indexname FROM pg_indexes WHERE tablename = 'genes' AND indexname = 'idx_gene_symbol_upper'"`
Expected: One row returned

**Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "perf: add functional index on UPPER(approved_symbol) for gene lookups"
```

---

### Task 8: Export Baseline Golden Snapshot

**Files:**
- Uses: `backend/app/pipeline/golden_file.py` (from Task 1)

**Prerequisites:** Pipeline must have run at least once with current code. Database must contain annotations.

**Step 1: Run the export**

```bash
cd backend && uv run python -c "
from app.core.database import SessionLocal
from app.pipeline.golden_file import export_golden_snapshot
from pathlib import Path

db = SessionLocal()
try:
    snapshot = export_golden_snapshot(db, Path('data/golden_snapshots/baseline_before_optimization.json'))
    print(f'Exported {len(snapshot)} genes')
finally:
    db.close()
"
```

**Step 2: Verify the snapshot**

```bash
python3 -c "
import json
data = json.load(open('backend/data/golden_snapshots/baseline_before_optimization.json'))
print(f'Genes: {len(data)}')
for gene in list(data.keys())[:3]:
    print(f'  {gene}: sources={list(data[gene].keys())}')
"
```

**Step 3: Add to .gitignore (snapshots are large, not committed)**

Add `data/golden_snapshots/` to `backend/.gitignore`

**Step 4: Commit**

```bash
git add backend/.gitignore
git commit -m "chore: add golden snapshot directory to gitignore"
```

---

## Phase 1: P0 Source Migrations

### Task 9: gnomAD — Bulk TSV Download

**Files:**
- Create: `backend/app/pipeline/sources/unified/gnomad.py` (or modify existing if it exists)
- Test: `backend/tests/pipeline/test_gnomad_bulk.py`

**Step 1: Research — check which gnomAD source exists**

Run: `find backend/app/pipeline -name "*gnomad*" -o -name "*gnomAD*"`

Check `backend/app/pipeline/annotation_pipeline.py` for how gnomAD is currently registered (around lines 51-76).

**Step 2: Research — count X-linked genes in our dataset**

```sql
-- Run against the database to determine API fallback need:
SELECT COUNT(*) FROM genes g
JOIN gene_annotations ga ON ga.gene_id = g.id
WHERE ga.source = 'gnomAD'
AND ga.annotations->>'chromosome' IN ('X', 'Y');
```

Also check the bulk TSV to see if X/Y genes are included:
```bash
curl -s "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/constraint/gnomad.v4.1.constraint_metrics.tsv" | head -1
# Check for chromosome column, then:
curl -s "..." | awk -F'\t' '$1 == "chrX" || $1 == "X"' | head -5
```

**Decision point:** If the TSV covers X/Y genes → drop API fallback. If not → keep API fallback for those genes only.

**Step 3: Write failing test**

```python
# backend/tests/pipeline/test_gnomad_bulk.py
"""Tests for gnomAD bulk TSV source."""

import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
class TestGnomADBulkParsing:
    """Test TSV parsing and gene lookup."""

    @pytest.mark.asyncio
    async def test_parse_constraint_tsv(self):
        """Parse gnomAD constraint TSV extracts pLI, LOEUF, z-scores."""
        from app.pipeline.sources.unified.gnomad import GnomADUnifiedSource

        # Create a minimal TSV fixture
        tsv_content = (
            "gene\ttranscript\tcanonical\tlof.pLI\tlof.oe_ci.upper\t"
            "lof.z_score\tmis.z_score\tsyn.z_score\tlof.oe\n"
            "PKD1\tENST00000262304\ttrue\t0.999\t0.152\t5.23\t3.45\t-0.12\t0.05\n"
            "PKD2\tENST00000237596\ttrue\t0.500\t0.450\t1.23\t0.45\t0.32\t0.35\n"
        )
        tsv_file = Path(tempfile.mktemp(suffix=".tsv"))
        tsv_file.write_text(tsv_content)

        source = GnomADUnifiedSource.__new__(GnomADUnifiedSource)
        data = await source.parse_bulk_file(tsv_file)

        assert "PKD1" in data
        assert data["PKD1"]["pLI"] == pytest.approx(0.999)
        assert data["PKD1"]["LOEUF"] == pytest.approx(0.152)
        assert "PKD2" in data

    @pytest.mark.asyncio
    async def test_lookup_returns_none_for_missing_gene(self):
        """Genes not in bulk data return None."""
        from app.pipeline.sources.unified.gnomad import GnomADUnifiedSource

        source = GnomADUnifiedSource.__new__(GnomADUnifiedSource)
        source._bulk_data = {"PKD1": {"pLI": 0.99}}
        result = await source.lookup_gene("NONEXISTENT")
        assert result is None
```

**Step 4: Implement the gnomAD bulk source**

```python
# backend/app/pipeline/sources/unified/gnomad.py
"""
Unified gnomAD data source with bulk TSV download.

Downloads the gnomAD v4.1 constraint metrics TSV (~91 MB) for fast
gene lookups instead of per-gene GraphQL API calls.
"""

import csv
from pathlib import Path
from typing import Any

from app.core.datasource_config import get_source_cache_ttl, get_source_parameter
from app.core.logging import get_logger
from app.pipeline.sources.unified.base import UnifiedDataSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

# Column mapping: TSV column name -> our annotation field name
CONSTRAINT_FIELD_MAP = {
    "lof.pLI": "pLI",
    "lof.oe_ci.upper": "LOEUF",
    "lof.z_score": "lof_z",
    "mis.z_score": "mis_z",
    "syn.z_score": "syn_z",
    "lof.oe": "oe_lof",
}


class GnomADUnifiedSource(BulkDataSourceMixin, UnifiedDataSource):
    """
    gnomAD constraint metrics source using bulk TSV download.

    Downloads the full constraint metrics TSV file and looks up genes
    locally. Falls back to GraphQL API for genes not in the bulk file
    (e.g., X-linked genes in older gnomAD releases).
    """

    @property
    def source_name(self) -> str:
        return "gnomAD"

    @property
    def namespace(self) -> str:
        return "gnomad"

    bulk_file_url = get_source_parameter(
        "gnomAD",
        "bulk_constraint_url",
        "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/constraint/gnomad.v4.1.constraint_metrics.tsv",
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "tsv"

    # Set based on research in Task 9 Step 2
    api_fallback_enabled = True  # TODO: Set to False if bulk TSV covers all genes

    def _get_default_ttl(self) -> int:
        return get_source_cache_ttl("gnomAD")

    async def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse gnomAD constraint metrics TSV into gene-keyed dict."""
        data: dict[str, dict[str, Any]] = {}

        with open(path, newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # Only use canonical transcripts
                if row.get("canonical", "").lower() != "true":
                    continue

                gene_symbol = row.get("gene", "").strip()
                if not gene_symbol:
                    continue

                annotation: dict[str, Any] = {}
                for tsv_col, our_field in CONSTRAINT_FIELD_MAP.items():
                    val = row.get(tsv_col, "")
                    if val and val != "NA":
                        try:
                            annotation[our_field] = float(val)
                        except ValueError:
                            annotation[our_field] = val

                if annotation:
                    data[gene_symbol] = annotation

        return data

    # NOTE: The full integration with the pipeline (fetch_raw_data, process_data,
    # etc.) requires adapting the existing gnomAD pipeline helper code.
    # This will be done during the actual migration by examining the current
    # gnomAD annotation source code and its integration points.
```

**Step 5: Run tests**

Run: `cd backend && uv run pytest tests/pipeline/test_gnomad_bulk.py -v`
Expected: All tests PASS

**Step 6: Golden file comparison**

After integrating with the pipeline and running a full gnomAD update:
```bash
cd backend && uv run python -c "
from app.core.database import SessionLocal
from app.pipeline.golden_file import export_golden_snapshot, compare_snapshots, generate_parity_report
from pathlib import Path

db = SessionLocal()
try:
    export_golden_snapshot(db, Path('data/golden_snapshots/after_gnomad_bulk.json'))
finally:
    db.close()

result = compare_snapshots(
    Path('data/golden_snapshots/baseline_before_optimization.json'),
    Path('data/golden_snapshots/after_gnomad_bulk.json'),
)
print(generate_parity_report(result))
"
```

**Step 7: Commit**

```bash
git add backend/app/pipeline/sources/unified/gnomad.py backend/tests/pipeline/test_gnomad_bulk.py
git commit -m "feat: add gnomAD bulk TSV download source (285s -> 5s)"
```

---

### Task 10: HGNC — Bulk JSON Download

**Files:**
- Modify: existing HGNC source (find via `grep -r "HGNC" backend/app/pipeline/`)
- Test: `backend/tests/pipeline/test_hgnc_bulk.py`

**Step 1: Research — find current HGNC source**

Run: `grep -rn "class.*HGNC\|hgnc" backend/app/pipeline/ --include="*.py" | head -20`

Check `backend/app/pipeline/annotation_pipeline.py` lines 51-76 for how HGNC is registered.

**Step 2: Write failing test**

Test HGNC JSON parsing — the bulk file at `hgnc_complete_set.json` has structure:
```json
{"responseHeader": {...}, "response": {"docs": [{"hgnc_id": "HGNC:5", "symbol": "A1BG", ...}]}}
```

Write a test that parses a minimal fixture and verifies extraction of: `hgnc_id`, `entrez_id`, `ensembl_gene_id`, `locus_type`, `gene_family`.

**Step 3: Implement**

Pattern: Same as gnomAD (Task 9). Add `BulkDataSourceMixin` to HGNC source class. Override `parse_bulk_file` to parse the JSON response format. `lookup_gene` keyed by both `hgnc_id` and `symbol` for flexible lookup.

HGNC has 100% coverage — set `api_fallback_enabled = False`.

**Step 4: Golden file comparison**

Same workflow as Task 9 Step 6.

**Step 5: Commit**

```bash
git commit -m "feat: add HGNC bulk JSON download source (571 API calls -> 1 download)"
```

---

## Phase 2: P1 Source Migrations

### Task 11: GTEx — Bulk GCT Download

**Pattern:** Same as Tasks 9-10.

**Key research:**
- Download `gene_median_tpm.gct.gz` (v8: 7 MB, v10: 9 MB)
- GCT format: header lines, then tab-separated gene × tissue matrix
- Check current API data version — if v8, use v8 GCT. If upgrading to v10, flag as version change.
- 100% coverage expected — likely drop API code

**Parse:** Skip first 2 header lines. Read column names (tissue IDs). For each row, extract gene ID and TPM values for kidney-relevant tissues.

**Commit:** `feat: add GTEx bulk GCT download source (1142 API calls -> 1 download)`

---

### Task 12: HPO — `genes_to_phenotype.txt` Download

**Pattern:** Same as Tasks 9-10.

**Key research:**
- File format: `gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id`
- Check: does the file include the `frequency` and `disease_id` fields we currently extract from API?
- If yes: drop API code. If no: keep API for disease detail enrichment.

**Parse:** Group rows by gene_symbol. For each gene, collect list of HPO terms with phenotype names, frequencies, and disease IDs.

**Commit:** `feat: add HPO bulk file download source (1142 API calls -> 1 download)`

---

### Task 13: ClinVar — Hybrid Bulk + API Key

**Three sub-steps:**

1. **Add NCBI API key support** — Add `NCBI_API_KEY` to settings, pass as `api_key` parameter to all NCBI E-utility calls. Zero code change for 3.4x speedup.

2. **Download `gene_specific_summary.txt`** — Provides aggregate counts (total alleles, pathogenic count, etc.) without any API calls. Parse into gene-keyed dict.

3. **Research: molecular consequences** — Check if any downstream code uses per-variant molecular consequence data. If not, the summary file is sufficient. If yes, keep API for targeted variant queries.

**Commit:** `feat: add ClinVar bulk summary + API key support`

---

## Phase 3: P2 Source Migrations

### Task 14: Ensembl — MANE File for RefSeq xrefs

**Pattern:** Download `MANE.GRCh38.v1.5.summary.txt.gz`. Parse into `{ENST_id: NM_id}` dict. Replace per-transcript `_fetch_refseq_id()` GET calls with dict lookup. Keep existing batch POST for core gene data.

**Commit:** `feat: add MANE file for Ensembl RefSeq xrefs (571 GETs -> 1 download)`

---

### Task 15: UniProt — ID Mapping API

**Pattern:** Replace OR-query batches with single ID Mapping job. `POST /idmapping/run` with all 571 gene names. Poll for results. Parse response.

**Bonus:** Fixes the PKD1/PRKD1 gene name ambiguity bug (the `From` column maps back unambiguously).

**Research:** Verify domain annotations are included in ID Mapping results.

**Commit:** `feat: switch UniProt to ID Mapping API (6 batches -> 1 job)`

---

### Task 16: PubTator — FTP or Gene-Centric Queries

**Research first:**
- Download `gene2pubtator3.gz` (713 MB). Time the download + parse.
- If parse < 30s: use bulk file, filter to 571 genes locally.
- If parse > 60s: use gene-centric API queries (`@GENE_{symbol}`) instead.

**Commit:** `feat: optimize PubTator source (paginated keyword search -> bulk/gene-centric)`

---

## Phase 4: P3 Sources + Polish

### Task 17: MPO/MGI — MouseMine Lists API

Use MouseMine Lists API: upload all 571 genes, query `HGene_MPhenotype` template with `IN` operator. Reduces 571 → ~3 requests.

**Commit:** `feat: switch MPO/MGI to MouseMine Lists API (571 -> 3 requests)`

---

### Task 18: ClinGen — CSV Bulk Download

Download full CSV from `search.clinicalgenome.org/kb/gene-validity/download`. Filter to kidney panels locally. Minor gain (5 → 1 request).

**Commit:** `feat: switch ClinGen to CSV bulk download`

---

### Task 19: Parallelize Statistics Summary Queries

**Files:**
- Modify: `backend/app/api/endpoints/statistics.py:247-261`

Replace sequential queries with `asyncio.gather`:

```python
from starlette.concurrency import run_in_threadpool

overlap_data, composition_data, distribution_data = await asyncio.gather(
    run_in_threadpool(statistics_crud.get_source_overlaps, db),
    run_in_threadpool(statistics_crud.get_evidence_composition, db),
    run_in_threadpool(statistics_crud.get_source_distributions, db),
)
```

**Note:** Each call needs its own DB session since sessions are not thread-safe. Create sessions within the threadpool lambdas or use `get_db()` dependency per call.

**Commit:** `perf: parallelize statistics summary queries (-60% latency)`

---

### Task 20: Progress Tracker Interval

**Files:**
- Modify: `backend/app/core/progress_tracker.py` (find the update interval)

Change default DB write interval from 1 second to 5 seconds. WebSocket updates via event bus are separate and can remain more frequent.

**Commit:** `perf: increase progress tracker DB write interval to 5 seconds`

---

## Phase 5: Final Validation

### Task 21: Full Pipeline Run + Parity Report

**Step 1:** Run full pipeline with all optimizations:
```bash
curl -X POST http://localhost:8000/api/annotations/pipeline/update
```

**Step 2:** Export post-optimization snapshot:
```bash
cd backend && uv run python -c "
from app.core.database import SessionLocal
from app.pipeline.golden_file import export_golden_snapshot
from pathlib import Path
db = SessionLocal()
try:
    export_golden_snapshot(db, Path('data/golden_snapshots/after_all_optimizations.json'))
finally:
    db.close()
"
```

**Step 3:** Compare against baseline:
```bash
cd backend && uv run python -c "
from app.pipeline.golden_file import compare_snapshots, generate_parity_report
from pathlib import Path
result = compare_snapshots(
    Path('data/golden_snapshots/baseline_before_optimization.json'),
    Path('data/golden_snapshots/after_all_optimizations.json'),
)
report = generate_parity_report(result)
Path('data/golden_snapshots/final_parity_report.md').write_text(report)
print(report)
"
```

**Step 4:** Review parity report. Investigate any differences. Flag version-related changes for manual decision.

### Task 22: Performance Benchmarks

Time the full pipeline before and after. Document results:

| Metric | Before | After |
|--------|--------|-------|
| Total pipeline time | ~13-15 min | ~3-4 min |
| Total API calls | ~5,000+ | ~20 |
| Gene listing endpoint (50 genes) | Xms | Xms |
| Statistics summary | Xms | Xms |

**Commit:**
```bash
git commit -m "docs: add pipeline optimization benchmark results"
```

---

## Summary of Commits

| Phase | Task | Commit Message |
|-------|------|---------------|
| 0 | 1 | `feat: add golden file validation framework for pipeline data parity` |
| 0 | 2 | `feat: add BulkDataSourceMixin for bulk file download sources` |
| 0 | 3 | `perf: replace N+1 subqueries with CTE in gene listing endpoint` |
| 0 | 4 | `fix: add asyncio.Lock to ARQ pool singleton` |
| 0 | 5 | `perf: align thread pool (10) with connection pool (10+15)` |
| 0 | 6 | `perf: replace inspect.stack() with asyncio.get_running_loop()` |
| 0 | 7 | `perf: add functional index on UPPER(approved_symbol)` |
| 0 | 8 | `chore: add golden snapshot directory to gitignore` |
| 1 | 9 | `feat: add gnomAD bulk TSV download source` |
| 1 | 10 | `feat: add HGNC bulk JSON download source` |
| 2 | 11 | `feat: add GTEx bulk GCT download source` |
| 2 | 12 | `feat: add HPO bulk file download source` |
| 2 | 13 | `feat: add ClinVar bulk summary + API key support` |
| 3 | 14 | `feat: add MANE file for Ensembl RefSeq xrefs` |
| 3 | 15 | `feat: switch UniProt to ID Mapping API` |
| 3 | 16 | `feat: optimize PubTator source` |
| 4 | 17 | `feat: switch MPO/MGI to MouseMine Lists API` |
| 4 | 18 | `feat: switch ClinGen to CSV bulk download` |
| 4 | 19 | `perf: parallelize statistics summary queries` |
| 4 | 20 | `perf: increase progress tracker DB write interval` |
| 5 | 21-22 | `docs: add pipeline optimization benchmark results` |
