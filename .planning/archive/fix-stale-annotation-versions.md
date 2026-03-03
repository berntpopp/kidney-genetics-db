# Fix Stale Annotation Version Accumulation

**Date**: 2026-03-03
**Status**: COMPLETED (merged to main 2026-03-03)
**Priority**: High -- stale rows inflate DB size and corrupt aggregate queries

---

## Problem Statement

When an annotation source class bumps its hardcoded `version` attribute (e.g., gnomAD `v4.0.0` -> `v4.1.0`), the pipeline's bulk upsert creates **new** rows instead of updating existing ones. Old-version rows are never updated or deleted, accumulating as orphans.

**Current stale data in production:**

| Source   | Stale Version | Stale Rows | Current Version | Current Rows |
|----------|---------------|------------|-----------------|--------------|
| gnomad   | v4.0.0        | 3,435      | v4.1.0          | 5,045        |
| ensembl  | 1.0           | 5,056      | 2.0             | 1,394        |
| clinvar  | 1.0           | 145        | 2.0             | 5,080        |

Total orphan rows: **8,636** (wasted storage + polluted queries).

---

## Root Cause Analysis

### 1. The Unique Constraint Is Too Narrow

The `gene_annotations` table has a unique constraint on `(gene_id, source, version)`:

```python
# backend/app/models/gene_annotation.py:43
__table_args__ = (
    UniqueConstraint("gene_id", "source", "version", name="unique_gene_source_version"),
)
```

This means a gene can have **multiple rows for the same source** if the version differs. The design intent was presumably to support versioned snapshots, but in practice:
- Only the latest version is ever meaningful
- No consumer ever queries by version
- The API returns ALL versions for a gene, confusing downstream code

### 2. The Bulk Upsert Targets the 3-Column Constraint

```python
# backend/app/pipeline/annotation_pipeline.py:866-873
sql = text(
    f"INSERT INTO gene_annotations "
    f"(gene_id, source, version, annotations, source_metadata, "
    f"created_at, updated_at) VALUES {', '.join(values_clauses)} "
    f"ON CONFLICT (gene_id, source, version) DO UPDATE SET "
    f"annotations = EXCLUDED.annotations, ..."
)
```

When the source class has `version = "v4.1.0"` but the DB row has `version = "v4.0.0"`, the `ON CONFLICT` clause does not match, so PostgreSQL INSERTs a new row.

### 3. `store_annotation()` Also Queries by Version

```python
# backend/app/pipeline/sources/annotations/base.py:200-203
existing = (
    self.session.query(GeneAnnotation)
    .filter_by(gene_id=gene.id, source=self.source_name, version=self.version)
    .first()
)
```

The per-gene `store_annotation()` path has the same bug: it looks for `(gene_id, source, version)`, so when version changes, `existing` is `None` and a new row is inserted.

### 4. No Cleanup Logic Exists Anywhere

Searched the entire codebase for cleanup, delete, stale, or orphan removal logic related to annotations. **None exists.** The only "stale" recovery is for the pipeline lock (`_recover_stale_lock`), not for data rows.

### 5. The `annotation_sources` Table Does NOT Track Per-Row Versions

The `annotation_sources` table has its own `version` column (defaulting to `"1.0"`), but it is never updated by the pipeline when a source class changes its version. It is not linked to `gene_annotations.version` in any way. The `_get_or_create_source()` method queries by `source_name` only and never updates the version.

---

## Investigation Findings

### How Version Is Set Per Source

All versions are hardcoded class attributes in `backend/app/pipeline/sources/annotations/`:

| Source   | File          | Version       | Notes                        |
|----------|---------------|---------------|------------------------------|
| hgnc     | hgnc.py:31    | `"2024.01"`   |                              |
| gnomad   | gnomad.py:59  | `"v4.1.0"`    | Was v4.0.0 previously        |
| gtex     | gtex.py:58    | `"v8"`        |                              |
| descartes| descartes.py  | `"human_gtex"`|                              |
| mpo_mgi  | mpo_mgi.py:34 | `"1.0"`       |                              |
| hpo      | hpo.py:37     | `"1.0"`       |                              |
| clinvar  | clinvar.py:61 | `"2.0"`       | Was 1.0 previously           |
| ensembl  | ensembl.py:69 | `"2.0"`       | Was 1.0 previously           |
| uniprot  | uniprot.py:55 | `"1.0"`       |                              |

### How the API Reads Annotations (No Version Filtering)

`GET /genes/{gene_id}/annotations` (`gene_annotations.py:37-103`):
- Queries `GeneAnnotation` filtered by `gene_id` and optionally `source`
- **Does NOT filter by version** -- returns ALL versions
- Groups results by source, appending each version as a separate entry in an array
- Result: API consumers see duplicate/stale data for sources with version bumps

### How Views/Materialized Views Use Annotations (No Version Filtering)

SQL views in `backend/app/db/views.py` that reference `gene_annotations`:

1. **`string_ppi_percentiles`** (line 319): `FROM gene_annotations ga` -- joins without version filter. If PPI data existed in two versions, percentile calculations would be wrong.

2. **`gene_scores`** (lines 361, 367): `FROM gene_annotations WHERE gene_id = g.id` -- counts `COUNT(DISTINCT source)` which is correct (counts unique sources, not rows), and `array_agg(DISTINCT source)` which also works. But these don't reflect the bloated table size.

3. **`gene_hpo_classifications`** (line 482): `LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'` -- joins by source only, no version filter. If HPO had two versions, this JOIN would produce duplicate rows.

### The INCREMENTAL Strategy Is Broken by Stale Rows

```python
# annotation_pipeline.py:413-419
.having(func.count(GeneAnnotation.id) < len(self.sources))
```

This counts **all** annotation rows (including stale versions) per gene. A gene with both v4.0.0 and v4.1.0 gnomAD rows counts as having 2 annotations. This inflates the count, causing the INCREMENTAL strategy to skip genes that actually need updating.

---

## Fix Options

### Option A: Change Unique Constraint to `(gene_id, source)` [RECOMMENDED]

**Approach**: Each gene gets exactly one annotation row per source. Version bumps overwrite the existing row.

**Changes required:**

1. **Alembic migration**: Drop `unique_gene_source_version`, create `unique_gene_source` on `(gene_id, source)`
2. **Data migration**: Delete stale rows (keep only latest version per gene+source)
3. **Bulk upsert SQL**: Change `ON CONFLICT (gene_id, source, version)` to `ON CONFLICT (gene_id, source)`
4. **`store_annotation()`**: Change `.filter_by(gene_id=..., source=..., version=...)` to `.filter_by(gene_id=..., source=...)`
5. **Model**: Update `__table_args__` UniqueConstraint

**Tradeoffs:**
- (+) Simplest fix, eliminates the problem permanently
- (+) No orphans can ever accumulate
- (+) DB stays lean, views stay correct
- (+) `version` column is preserved for informational purposes (tracks what version produced the data)
- (-) Loses historical version snapshots (but nobody uses them -- the `annotation_history` table already tracks changes)
- (-) Requires careful migration with data cleanup

### Option B: Keep 3-Column Constraint, Add Cleanup Step

**Approach**: After each pipeline run, delete rows where `(gene_id, source)` matches but `version != current_version`.

**Changes required:**

1. Add `_cleanup_stale_versions()` method to `AnnotationPipeline`
2. Call it after each source completes in `_update_source_with_session()`
3. Add one-time migration to clean existing stale rows

**Tradeoffs:**
- (+) Preserves the versioned schema design
- (-) Adds complexity -- cleanup can fail, leaving orphans
- (-) Cleanup runs after every pipeline execution (performance overhead)
- (-) Doesn't fix `store_annotation()` per-gene path
- (-) Must be maintained alongside every code path that writes annotations

### Option C: Version-Aware Queries Everywhere

**Approach**: Keep all rows, but always filter by current version in queries.

**Changes required:**

1. Add `current_version` column to `annotation_sources` table
2. Update all API queries to join `annotation_sources` and filter by `version`
3. Update all SQL views to filter by current version
4. Add management commands to update `annotation_sources.current_version`

**Tradeoffs:**
- (-) Most complex option
- (-) Every query must be updated (high risk of missing one)
- (-) DB continues to grow with each version bump
- (-) Performance degrades over time
- (+) True versioned history (but `annotation_history` already provides this)

---

## Recommended Approach: Option A

Option A is recommended because:
1. The system has **no use case** for keeping old-version annotations alongside new ones
2. The `annotation_history` table already provides a full audit trail
3. It is the simplest and most maintainable solution
4. It eliminates an entire class of bugs permanently

---

## Implementation Plan

### Step 1: Write Data Cleanup Migration

**File**: `backend/alembic/versions/XXX_fix_stale_annotation_versions.py`

```sql
-- Phase 1: Delete stale rows (keep only the latest version per gene+source)
DELETE FROM gene_annotations
WHERE id NOT IN (
    SELECT DISTINCT ON (gene_id, source) id
    FROM gene_annotations
    ORDER BY gene_id, source, updated_at DESC NULLS LAST
);

-- Phase 2: Drop old constraint
ALTER TABLE gene_annotations DROP CONSTRAINT unique_gene_source_version;

-- Phase 3: Create new constraint
ALTER TABLE gene_annotations ADD CONSTRAINT unique_gene_source
    UNIQUE (gene_id, source);
```

The migration `downgrade()` should reverse this:
```sql
ALTER TABLE gene_annotations DROP CONSTRAINT unique_gene_source;
ALTER TABLE gene_annotations ADD CONSTRAINT unique_gene_source_version
    UNIQUE (gene_id, source, version);
```

### Step 2: Update the SQLAlchemy Model

**File**: `backend/app/models/gene_annotation.py`

Change line 43:
```python
# Before
UniqueConstraint("gene_id", "source", "version", name="unique_gene_source_version"),

# After
UniqueConstraint("gene_id", "source", name="unique_gene_source"),
```

### Step 3: Update Bulk Upsert SQL

**File**: `backend/app/pipeline/annotation_pipeline.py`

Change `_bulk_upsert_annotations_with_session()` (lines 866-873):
```python
# Before
f"ON CONFLICT (gene_id, source, version) DO UPDATE SET "

# After
f"ON CONFLICT (gene_id, source) DO UPDATE SET "
f"annotations = EXCLUDED.annotations, "
f"version = EXCLUDED.version, "  # Also update the version column
f"source_metadata = EXCLUDED.source_metadata, "
f"updated_at = EXCLUDED.updated_at"
```

Note: The `SET` clause must now include `version = EXCLUDED.version` so that the version column gets updated when a new version overwrites an old one.

### Step 4: Update `store_annotation()` in Base Class

**File**: `backend/app/pipeline/sources/annotations/base.py`

Change lines 200-203:
```python
# Before
existing = (
    self.session.query(GeneAnnotation)
    .filter_by(gene_id=gene.id, source=self.source_name, version=self.version)
    .first()
)

# After
existing = (
    self.session.query(GeneAnnotation)
    .filter_by(gene_id=gene.id, source=self.source_name)
    .first()
)
```

Also update the `else` branch (line 222-231) to set `version` on the existing record when it differs:
```python
if existing:
    # Update version if it changed
    if existing.version != self.version:
        existing.version = self.version
    existing.annotations = annotation_data
    ...
```

### Step 5: Update `annotation_sources` Table Version Tracking

**File**: `backend/app/pipeline/sources/annotations/base.py`

In `_get_or_create_source()`, also update the source record's version when it differs:
```python
def _get_or_create_source(self) -> AnnotationSource:
    source = self.session.query(AnnotationSource).filter_by(
        source_name=self.source_name
    ).first()

    if not source:
        source = AnnotationSource(
            source_name=self.source_name,
            display_name=self.display_name or self.source_name,
            version=self.version or "1.0",  # Track current version
            is_active=True,
            config=self.get_default_config(),
        )
        self.session.add(source)
        self.session.commit()
    elif self.version and source.version != self.version:
        # Update tracked version when source code version changes
        source.version = self.version
        self.session.commit()

    return source
```

### Step 6: Update Tests

**File**: `backend/tests/pipeline/test_bulk_upsert.py`

Update existing bulk upsert tests to:
1. Assert that `ON CONFLICT (gene_id, source)` is used
2. Add test: inserting same gene+source with different version overwrites (not duplicates)
3. Add test: version column is updated on overwrite

### Step 7: Verify Views Are Correct

No changes needed to views -- they already query by `source` without version. With the fix, they will naturally see only one row per gene+source (the latest), which is the correct behavior.

### Step 8: Refresh Materialized Views

After the migration runs, trigger a materialized view refresh:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY gene_scores;
REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary;
```

---

## Prevention Mechanisms

1. **Structural prevention**: The `UNIQUE (gene_id, source)` constraint makes it physically impossible to have duplicate rows for the same gene+source. This is the primary guard.

2. **CI test**: Add a unit test that verifies the `GeneAnnotation` model's unique constraint is `(gene_id, source)` and NOT `(gene_id, source, version)`. This prevents regression if someone adds version back.

3. **Pipeline logging**: Log when a version change is detected in `_get_or_create_source()` so version bumps are visible in operational logs.

4. **Monitoring query** (optional, for periodic checks):
   ```sql
   -- Should always return 0 after the fix
   SELECT source, COUNT(*) - COUNT(DISTINCT gene_id) AS duplicate_count
   FROM gene_annotations
   GROUP BY source
   HAVING COUNT(*) > COUNT(DISTINCT gene_id);
   ```

---

## Migration Rollout Plan

1. **Backup**: `make db-backup-full` before migration
2. **Run migration**: `cd backend && uv run alembic upgrade head`
3. **Verify cleanup**: `SELECT source, version, COUNT(*) FROM gene_annotations GROUP BY source, version ORDER BY source;`
4. **Refresh views**: `make db-refresh-views`
5. **Run pipeline**: Trigger a full pipeline update to verify the new upsert works
6. **Validate**: `make db-verify-complete`

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/alembic/versions/XXX_fix_stale_annotation_versions.py` | New migration: cleanup + constraint change |
| `backend/app/models/gene_annotation.py` | Change UniqueConstraint to `(gene_id, source)` |
| `backend/app/pipeline/annotation_pipeline.py` | Update ON CONFLICT clause in bulk upsert |
| `backend/app/pipeline/sources/annotations/base.py` | Update `store_annotation()` and `_get_or_create_source()` |
| `backend/tests/pipeline/test_bulk_upsert.py` | Update/add tests for new constraint behavior |

---

## Completion Summary (2026-03-03)

**Implemented Option A** — changed unique constraint from `(gene_id, source, version)` to `(gene_id, source)`.

### Commits (merged to main via fast-forward)
1. `c4a7edd` test: add failing tests for stale annotation version fix
2. `0f4de5a` feat: add migration to fix stale annotation version accumulation
3. `3c44cde` feat: change GeneAnnotation unique constraint to (gene_id, source)
4. `cc5d81f` fix: bulk upsert uses ON CONFLICT (gene_id, source)
5. `a9282d8` fix: store_annotation() uses version-independent lookup
6. `470fd33` feat: sync annotation_sources.version on source class version change
7. `3beba12` refactor: simplify bulk upsert test queries to match new constraint
8. `8c69cb2` style: apply ruff formatting to modified files
9. `7fe6d83` style: apply ruff formatting to all changed files

### Verification Results
- DB constraint confirmed: `UNIQUE (gene_id, source)`
- Zero duplicates across all 10 sources
- Total rows: 48,063 (down from ~56,699 — 8,636 stale rows removed)
- Live upsert test: same row overwritten on version bump, no duplicate created
- 523/524 tests pass (1 pre-existing unrelated failure)
- Lint + typecheck clean
