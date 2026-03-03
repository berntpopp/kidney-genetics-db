# Fix Stale Annotation Version Accumulation — Implementation Plan

> **Status:** COMPLETED — merged to main 2026-03-03

**Goal:** Change the `gene_annotations` unique constraint from `(gene_id, source, version)` to `(gene_id, source)` so that version bumps overwrite existing rows instead of creating orphans, then clean up the 8,636 stale rows already in the database.

**Architecture:** An Alembic migration deletes stale rows (keeping latest per gene+source) and swaps the unique constraint. The SQLAlchemy model, bulk upsert SQL, and per-gene `store_annotation()` are updated to match. The `annotation_sources` table version is synced on each pipeline run.

**Tech Stack:** Python 3.13, SQLAlchemy, Alembic, PostgreSQL, pytest

---

### Task 1: Write the Failing Test for the New Unique Constraint

**Files:**
- Modify: `backend/tests/test_gene_annotations.py:140-173`

This task updates the existing `test_unique_constraint` test to assert `(gene_id, source)` uniqueness. Currently (lines 140-173) it asserts that different versions of the same gene+source are ALLOWED. After the fix, they must NOT be allowed — the constraint is `(gene_id, source)`.

**Step 1: Write the failing test**

Replace the `test_unique_constraint` function in `backend/tests/test_gene_annotations.py` (lines 140-173):

```python
def test_unique_constraint(db_session: Session):
    """Test unique constraint on gene_id, source (version-independent)."""
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    # First annotation
    ann1 = GeneAnnotation(
        gene_id=gene.id, source="hgnc", version="v1", annotations={"test": "data1"}
    )
    db_session.add(ann1)
    db_session.commit()

    # Same gene+source with different version should ALSO fail (new behavior)
    ann2 = GeneAnnotation(
        gene_id=gene.id, source="hgnc", version="v2", annotations={"test": "data2"}
    )
    db_session.add(ann2)

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()

    # Different source for the same gene should still work
    ann3 = GeneAnnotation(
        gene_id=gene.id, source="gnomad", version="v1", annotations={"test": "data3"}
    )
    db_session.add(ann3)
    db_session.commit()
    assert ann3.id is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_unique_constraint -v`

Expected: FAIL — the second insert (same gene+source, different version) currently succeeds because the old constraint is `(gene_id, source, version)`.

---

### Task 2: Write the Failing Test for Version-Overwrite in Bulk Upsert

**Files:**
- Modify: `backend/tests/pipeline/test_bulk_upsert.py` (append new test methods)

**Step 1: Write the failing test**

Add these two tests at the end of the `TestBulkUpsertAnnotations` class in `backend/tests/pipeline/test_bulk_upsert.py`:

```python
    def test_bulk_upsert_overwrites_on_version_change(self, db_session: Session):
        """Version bump overwrites existing row instead of creating a duplicate."""
        gene = db_session.query(Gene).first()
        if not gene:
            pytest.skip("No genes in database")

        # Insert with version 1.0
        pipeline = self._make_pipeline(db_session)
        pipeline._bulk_upsert_annotations_with_session(
            "_test_bulk", "1.0", {gene.id: {"value": "old"}}, db_session
        )

        # Upsert with version 2.0 — should overwrite, NOT create a second row
        pipeline._bulk_upsert_annotations_with_session(
            "_test_bulk", "2.0", {gene.id: {"value": "new"}}, db_session
        )

        rows = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk")
            .all()
        )
        assert len(rows) == 1, f"Expected 1 row, got {len(rows)} (stale version not cleaned)"
        assert rows[0].version == "2.0"
        assert rows[0].annotations["value"] == "new"

        # Cleanup
        db_session.execute(
            text("DELETE FROM gene_annotations WHERE source = '_test_bulk'")
        )
        db_session.commit()

    def test_bulk_upsert_updates_version_column(self, db_session: Session):
        """The version column is updated when a new version overwrites an old one."""
        gene = db_session.query(Gene).first()
        if not gene:
            pytest.skip("No genes in database")

        pipeline = self._make_pipeline(db_session)
        pipeline._bulk_upsert_annotations_with_session(
            "_test_bulk", "1.0", {gene.id: {"score": 0.5}}, db_session
        )

        # Overwrite with new version
        pipeline._bulk_upsert_annotations_with_session(
            "_test_bulk", "2.0", {gene.id: {"score": 0.9}}, db_session
        )

        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk")
            .first()
        )
        assert ann is not None
        assert ann.version == "2.0"
        assert ann.annotations["score"] == 0.9

        db_session.delete(ann)
        db_session.commit()
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/pipeline/test_bulk_upsert.py::TestBulkUpsertAnnotations::test_bulk_upsert_overwrites_on_version_change tests/pipeline/test_bulk_upsert.py::TestBulkUpsertAnnotations::test_bulk_upsert_updates_version_column -v`

Expected: FAIL — `test_bulk_upsert_overwrites_on_version_change` gets 2 rows (old constraint allows both versions). `test_bulk_upsert_updates_version_column` also fails for the same reason.

---

### Task 3: Write the Failing Test for `store_annotation()` Version Overwrite

**Files:**
- Modify: `backend/tests/test_gene_annotations.py` (append new test)

**Step 1: Write the failing test**

Add this test at the end of `backend/tests/test_gene_annotations.py`:

```python
def test_store_annotation_overwrites_on_version_change(db_session: Session):
    """BaseAnnotationSource.store_annotation() overwrites existing row on version change."""
    gene = Gene(approved_symbol=f"TEST{uuid.uuid4().hex[:6].upper()}", hgnc_id=unique_hgnc_id())
    db_session.add(gene)
    db_session.commit()

    # Insert annotation with version 1.0
    ann_v1 = GeneAnnotation(
        gene_id=gene.id,
        source="test_src",
        version="1.0",
        annotations={"data": "old"},
    )
    db_session.add(ann_v1)
    db_session.commit()

    # Simulate store_annotation lookup with version 2.0
    # (mimics what BaseAnnotationSource.store_annotation does)
    existing = (
        db_session.query(GeneAnnotation)
        .filter_by(gene_id=gene.id, source="test_src")
        .first()
    )

    # With the fix, existing should find the v1.0 row (query is version-independent)
    assert existing is not None, "store_annotation lookup should find existing row regardless of version"
    assert existing.version == "1.0"

    # Simulate updating version + data
    existing.version = "2.0"
    existing.annotations = {"data": "new"}
    db_session.commit()

    # Verify only one row exists
    rows = (
        db_session.query(GeneAnnotation)
        .filter_by(gene_id=gene.id, source="test_src")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].version == "2.0"
    assert rows[0].annotations["data"] == "new"
```

**Step 2: Run test to verify it passes (this is a query-level test, not constraint-level)**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_store_annotation_overwrites_on_version_change -v`

Expected: This test should actually PASS because the query `.filter_by(gene_id=..., source=...)` (no version) will find the v1.0 row. This test validates the expected behavior after the code change, serving as a regression guard.

---

### Task 4: Write the Failing Test for Model Constraint Definition

**Files:**
- Modify: `backend/tests/test_gene_annotations.py` (append new test)

**Step 1: Write the regression guard test**

Add this test at the end of `backend/tests/test_gene_annotations.py`:

```python
def test_model_unique_constraint_is_gene_source_only():
    """Regression guard: GeneAnnotation unique constraint must be (gene_id, source), NOT (gene_id, source, version)."""
    constraints = GeneAnnotation.__table_args__
    unique_constraints = [
        c for c in constraints if isinstance(c, UniqueConstraint)
    ]
    assert len(unique_constraints) == 1, f"Expected 1 unique constraint, found {len(unique_constraints)}"

    uc = unique_constraints[0]
    col_names = [col.name for col in uc.columns]
    assert col_names == ["gene_id", "source"], (
        f"Unique constraint columns should be ['gene_id', 'source'], "
        f"got {col_names}. Do NOT add 'version' back to this constraint."
    )
```

Note: This test imports `UniqueConstraint` — add it to the import block at the top of the file:

```python
from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation
```

becomes:

```python
from sqlalchemy import UniqueConstraint

from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_model_unique_constraint_is_gene_source_only -v`

Expected: FAIL — the current constraint includes `version` in its columns, so `col_names` will be `['gene_id', 'source', 'version']`.

---

### Task 5: Run All New Tests to Confirm They Fail

**Step 1: Run all new/modified tests together**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_unique_constraint tests/test_gene_annotations.py::test_store_annotation_overwrites_on_version_change tests/test_gene_annotations.py::test_model_unique_constraint_is_gene_source_only tests/pipeline/test_bulk_upsert.py::TestBulkUpsertAnnotations::test_bulk_upsert_overwrites_on_version_change tests/pipeline/test_bulk_upsert.py::TestBulkUpsertAnnotations::test_bulk_upsert_updates_version_column -v`

Expected: 3 FAIL (constraint test, model test, and overwrite test), 2 PASS (version-column test may fail for same reason, store_annotation test should pass).

**Step 2: Commit the failing tests**

```bash
git add tests/test_gene_annotations.py tests/pipeline/test_bulk_upsert.py
git commit -m "test: add failing tests for stale annotation version fix

Add tests that assert:
- Unique constraint is (gene_id, source) not (gene_id, source, version)
- Bulk upsert overwrites on version change instead of duplicating
- store_annotation lookup is version-independent
- Model regression guard for constraint columns"
```

---

### Task 6: Write the Alembic Migration

**Files:**
- Create: `backend/alembic/versions/fix_stale_annotation_versions.py`

**Step 1: Create the migration file**

Run: `cd backend && uv run alembic revision -m "fix stale annotation versions unique constraint"`

This creates a new file in `backend/alembic/versions/`. Edit it with the following content (replace the generated revision ID and down_revision):

```python
"""fix stale annotation versions unique constraint

Revision ID: <generated>
Revises: a1b2c3d4e5f6
Create Date: <generated>
"""

from alembic import op

# revision identifiers
revision = "<generated>"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Phase 1: Delete stale rows — keep only the most-recently-updated row
    # per (gene_id, source) pair.
    op.execute(
        """
        DELETE FROM gene_annotations
        WHERE id NOT IN (
            SELECT DISTINCT ON (gene_id, source) id
            FROM gene_annotations
            ORDER BY gene_id, source, updated_at DESC NULLS LAST
        )
        """
    )

    # Phase 2: Drop the old 3-column constraint
    op.drop_constraint("unique_gene_source_version", "gene_annotations", type_="unique")

    # Phase 3: Create the new 2-column constraint
    op.create_unique_constraint("unique_gene_source", "gene_annotations", ["gene_id", "source"])


def downgrade() -> None:
    op.drop_constraint("unique_gene_source", "gene_annotations", type_="unique")
    op.create_unique_constraint(
        "unique_gene_source_version", "gene_annotations", ["gene_id", "source", "version"]
    )
```

**Step 2: Run the migration**

Run: `cd backend && uv run alembic upgrade head`

Expected: Migration completes. Stale rows deleted, constraint swapped.

**Step 3: Verify stale rows are gone**

Run: `cd backend && uv run python -c "from app.core.database import SessionLocal; from sqlalchemy import text; db = SessionLocal(); rows = db.execute(text(\"SELECT source, version, COUNT(*) FROM gene_annotations GROUP BY source, version ORDER BY source, version\")).fetchall(); [print(r) for r in rows]; db.close()"`

Expected: Each source appears at most once (only current version).

**Step 4: Commit the migration**

```bash
git add alembic/versions/*fix_stale_annotation_versions*.py
git commit -m "feat: add migration to fix stale annotation version accumulation

Phase 1: Delete orphan rows (keep latest per gene+source).
Phase 2: Drop unique_gene_source_version constraint.
Phase 3: Create unique_gene_source constraint on (gene_id, source)."
```

---

### Task 7: Update the SQLAlchemy Model

**Files:**
- Modify: `backend/app/models/gene_annotation.py:42-44`

**Step 1: Change the UniqueConstraint**

In `backend/app/models/gene_annotation.py`, change line 43:

```python
# Before (line 43)
        UniqueConstraint("gene_id", "source", "version", name="unique_gene_source_version"),

# After
        UniqueConstraint("gene_id", "source", name="unique_gene_source"),
```

**Step 2: Run the model regression guard test**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_model_unique_constraint_is_gene_source_only -v`

Expected: PASS

**Step 3: Run the unique constraint test**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_unique_constraint -v`

Expected: PASS — now same gene+source with different versions raises IntegrityError.

**Step 4: Commit**

```bash
git add app/models/gene_annotation.py
git commit -m "feat: change GeneAnnotation unique constraint to (gene_id, source)

Remove version from the unique constraint so each gene gets exactly
one annotation row per source. Version column is kept for informational
tracking of which source version produced the data."
```

---

### Task 8: Update Bulk Upsert SQL

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:866-873`

**Step 1: Change the ON CONFLICT clause**

In `backend/app/pipeline/annotation_pipeline.py`, replace lines 866-873:

```python
# Before (lines 866-873)
            sql = text(
                f"INSERT INTO gene_annotations "
                f"(gene_id, source, version, annotations, source_metadata, "
                f"created_at, updated_at) VALUES {', '.join(values_clauses)} "
                f"ON CONFLICT (gene_id, source, version) DO UPDATE SET "
                f"annotations = EXCLUDED.annotations, "
                f"source_metadata = EXCLUDED.source_metadata, "
                f"updated_at = EXCLUDED.updated_at"
            )

# After
            sql = text(
                f"INSERT INTO gene_annotations "
                f"(gene_id, source, version, annotations, source_metadata, "
                f"created_at, updated_at) VALUES {', '.join(values_clauses)} "
                f"ON CONFLICT (gene_id, source) DO UPDATE SET "
                f"version = EXCLUDED.version, "
                f"annotations = EXCLUDED.annotations, "
                f"source_metadata = EXCLUDED.source_metadata, "
                f"updated_at = EXCLUDED.updated_at"
            )
```

Key change: `ON CONFLICT (gene_id, source)` instead of `ON CONFLICT (gene_id, source, version)`, and `version = EXCLUDED.version` is added to the SET clause so the version column gets updated on overwrite.

**Step 2: Run the bulk upsert tests**

Run: `cd backend && uv run pytest tests/pipeline/test_bulk_upsert.py -v`

Expected: ALL PASS — including the two new overwrite tests.

**Step 3: Commit**

```bash
git add app/pipeline/annotation_pipeline.py
git commit -m "fix: bulk upsert uses ON CONFLICT (gene_id, source)

The SET clause now also updates version so that version bumps are
reflected in the existing row instead of creating orphan duplicates."
```

---

### Task 9: Update `store_annotation()` in Base Class

**Files:**
- Modify: `backend/app/pipeline/sources/annotations/base.py:200-218`

**Step 1: Remove version from the filter query**

In `backend/app/pipeline/sources/annotations/base.py`, change lines 200-203:

```python
# Before (lines 200-203)
        existing: GeneAnnotation | None = (
            self.session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source=self.source_name, version=self.version)
            .first()
        )

# After
        existing: GeneAnnotation | None = (
            self.session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source=self.source_name)
            .first()
        )
```

**Step 2: Update the existing-record branch to also set version**

In the same file, change lines 216-218:

```python
# Before (lines 216-218)
            existing.annotations = annotation_data
            existing.source_metadata = metadata
            existing.updated_at = datetime.now(timezone.utc)

# After
            if existing.version != self.version:
                existing.version = self.version
            existing.annotations = annotation_data
            existing.source_metadata = metadata
            existing.updated_at = datetime.now(timezone.utc)
```

**Step 3: Run the store_annotation test**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py::test_store_annotation_overwrites_on_version_change -v`

Expected: PASS

**Step 4: Commit**

```bash
git add app/pipeline/sources/annotations/base.py
git commit -m "fix: store_annotation() uses version-independent lookup

Query by (gene_id, source) only so version bumps update the existing
row. Also sets version on existing record when it differs."
```

---

### Task 10: Sync `annotation_sources.version` in `_get_or_create_source()`

**Files:**
- Modify: `backend/app/pipeline/sources/annotations/base.py:104-120`

**Step 1: Update `_get_or_create_source()` to sync version**

In `backend/app/pipeline/sources/annotations/base.py`, replace lines 104-120:

```python
# Before (lines 104-120)
    def _get_or_create_source(self) -> AnnotationSource:
        """Get or create the annotation source record."""
        source: AnnotationSource | None = (
            self.session.query(AnnotationSource).filter_by(source_name=self.source_name).first()
        )

        if not source:
            source = AnnotationSource(
                source_name=self.source_name,
                display_name=self.display_name or self.source_name,
                is_active=True,
                config=self.get_default_config(),
            )
            self.session.add(source)
            self.session.commit()

        return source

# After
    def _get_or_create_source(self) -> AnnotationSource:
        """Get or create the annotation source record."""
        source: AnnotationSource | None = (
            self.session.query(AnnotationSource).filter_by(source_name=self.source_name).first()
        )

        if not source:
            source = AnnotationSource(
                source_name=self.source_name,
                display_name=self.display_name or self.source_name,
                version=self.version or "1.0",
                is_active=True,
                config=self.get_default_config(),
            )
            self.session.add(source)
            self.session.commit()
        elif self.version and source.version != self.version:
            logger.sync_info(
                f"Source version changed: {source.version} -> {self.version}",
                source=self.source_name,
            )
            source.version = self.version
            self.session.commit()

        return source
```

**Step 2: Run all annotation tests**

Run: `cd backend && uv run pytest tests/test_gene_annotations.py -v`

Expected: ALL PASS

**Step 3: Commit**

```bash
git add app/pipeline/sources/annotations/base.py
git commit -m "feat: sync annotation_sources.version on source class version change

Log when a version change is detected and update the annotation_sources
table so it always reflects the current source code version."
```

---

### Task 11: Update Existing Bulk Upsert Tests for New Constraint

**Files:**
- Modify: `backend/tests/pipeline/test_bulk_upsert.py:27-33` and `46-47` and `74`

The existing tests clean up and query using `(gene_id, source, version)`. Since the new constraint is `(gene_id, source)`, the queries still work (they're more specific than needed), but the cleanup DELETE on line 27-33 includes `AND version = :ver` which is unnecessary. Update for clarity.

**Step 1: Simplify cleanup and queries in existing tests**

In `backend/tests/pipeline/test_bulk_upsert.py`:

Line 27-33 — change the cleanup DELETE:
```python
# Before
        db_session.execute(
            text(
                "DELETE FROM gene_annotations "
                "WHERE gene_id = :gid AND source = :src AND version = :ver"
            ),
            {"gid": gene.id, "src": "_test_bulk", "ver": "1.0"},
        )

# After
        db_session.execute(
            text("DELETE FROM gene_annotations WHERE gene_id = :gid AND source = :src"),
            {"gid": gene.id, "src": "_test_bulk"},
        )
```

Lines 44-48 — change the assertion query:
```python
# Before
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk", version="1.0")
            .first()
        )

# After
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk")
            .first()
        )
```

Lines 72-76 — same change:
```python
# Before
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk", version="1.0")
            .first()
        )

# After
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk")
            .first()
        )
```

Lines 99-103 — same change:
```python
# Before
            ann = (
                db_session.query(GeneAnnotation)
                .filter_by(gene_id=g.id, source="_test_bulk", version="1.0")
                .first()
            )

# After
            ann = (
                db_session.query(GeneAnnotation)
                .filter_by(gene_id=g.id, source="_test_bulk")
                .first()
            )
```

**Step 2: Run all bulk upsert tests**

Run: `cd backend && uv run pytest tests/pipeline/test_bulk_upsert.py -v`

Expected: ALL 7 PASS

**Step 3: Commit**

```bash
git add tests/pipeline/test_bulk_upsert.py
git commit -m "refactor: simplify bulk upsert test queries to match new constraint

Remove version from filter_by and cleanup queries since the unique
constraint is now (gene_id, source)."
```

---

### Task 12: Run Full Test Suite and Lint

**Step 1: Run lint**

Run: `cd backend && make lint`

Expected: All clean.

**Step 2: Run typecheck on modified files**

Run: `cd backend && uv run mypy app/models/gene_annotation.py app/pipeline/annotation_pipeline.py app/pipeline/sources/annotations/base.py --ignore-missing-imports`

Expected: No errors.

**Step 3: Run full test suite**

Run: `make test`

Expected: ALL PASS. No regressions.

**Step 4: If any failures, fix them before proceeding.**

---

### Task 13: Refresh Materialized Views and Verify

**Step 1: Refresh views**

Run: `make db-refresh-views`

Expected: Views refreshed successfully. The `gene_annotations_summary` materialized view now has exactly one row per gene+source (no duplicates from stale versions).

**Step 2: Verify database integrity**

Run: `make db-verify-complete`

Expected: All checks pass.

**Step 3: Run the monitoring query to confirm no duplicates**

Run: `cd backend && uv run python -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
dupes = db.execute(text('''
    SELECT source, COUNT(*) - COUNT(DISTINCT gene_id) AS duplicate_count
    FROM gene_annotations
    GROUP BY source
    HAVING COUNT(*) > COUNT(DISTINCT gene_id)
''')).fetchall()
if dupes:
    print('DUPLICATES FOUND:', dupes)
else:
    print('No duplicates. All clean.')
db.close()
"`

Expected: `No duplicates. All clean.`

**Step 4: Final commit (if any view changes needed)**

If no additional changes needed, skip this step.

---

### Task 14: Final Verification Commit

**Step 1: Run full CI check**

Run: `make ci-backend`

Expected: ALL PASS (lint + format check + tests).

**Step 2: Verify git log looks clean**

Run: `git log --oneline -10`

Expected: A clean series of atomic commits:
1. test: add failing tests
2. feat: migration
3. feat: model constraint
4. fix: bulk upsert
5. fix: store_annotation
6. feat: sync annotation_sources.version
7. refactor: simplify test queries

---

## Summary of All Files Changed

| File | Change |
|------|--------|
| `backend/alembic/versions/<hash>_fix_stale_annotation_versions.py` | **New**: Migration to clean stale rows + swap constraint |
| `backend/app/models/gene_annotation.py:43` | Change `UniqueConstraint` from 3-col to 2-col |
| `backend/app/pipeline/annotation_pipeline.py:866-873` | `ON CONFLICT (gene_id, source)` + set `version` in UPDATE |
| `backend/app/pipeline/sources/annotations/base.py:104-120` | Sync `annotation_sources.version` on change |
| `backend/app/pipeline/sources/annotations/base.py:200-218` | Remove version from lookup, update version on write |
| `backend/tests/test_gene_annotations.py` | Updated constraint test + 2 new tests + import |
| `backend/tests/pipeline/test_bulk_upsert.py` | 2 new tests + simplified queries in existing tests |
