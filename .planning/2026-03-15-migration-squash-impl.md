# Alembic Migration Squash Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate 22 development-phase Alembic migrations into a single clean initial schema migration, preceded by a prerequisite PR to fix SQLAlchemy model-DB drift.

**Architecture:** Two sequential PRs. PR 0 fixes 4 model files so autogenerate produces correct DDL. PR 1 performs the actual squash: backup existing state, delete old migrations, autogenerate against a blank DB, manually add views/indexes/seed data, verify via structured SQL comparison, and stamp the existing dev DB.

**Tech Stack:** Alembic, SQLAlchemy, PostgreSQL, psql CLI, `pg_dump`, Python/uv

---

> **Design Spec Discrepancy (found during plan writing):**
> The design spec at `.planning/2026-03-13-migration-squash-design.md` lists 18 migrations and 21 tables. The actual codebase has **22 migration files** and **22 tables** (including `refresh_tokens`). The 4 missing migrations are:
> - `0834f2555442_add_missing_indexes_for_cache_and_.py`
> - `285000c93ed5_add_refresh_tokens_table.py`
> - `e14a26c1b961_merge_heads_add_refresh_tokens.py`
> - `2c3fbf63d000_fix_gene_distribution_analysis_matview_.py`
>
> The plan below accounts for all 22 files and 22 tables. Autogenerate will capture `refresh_tokens` automatically from the `RefreshToken` model.

---

## Chunk 1: PR 0 — SQLAlchemy Model Fixes

### Task 1: Fix StaticSource model

**Files:**
- Modify: `backend/app/models/static_sources.py:23-49` (StaticSource class)
- Test: `backend/tests/test_models_static_sources.py` (new)

- [ ] **Step 1: Create branch**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
git checkout -b fix/model-schema-alignment
```

- [ ] **Step 2: Write failing test for StaticSource nullable/timezone fixes**

Create `backend/tests/test_models_static_sources.py`:

```python
"""Tests for StaticSource model schema alignment."""
import pytest
from sqlalchemy import BigInteger, inspect
from sqlalchemy.dialects.postgresql import JSONB

from app.models.static_sources import StaticSource, StaticSourceAudit, StaticEvidenceUpload


@pytest.mark.unit
class TestStaticSourceModel:
    """Verify StaticSource columns match design spec."""

    def test_is_active_not_nullable(self):
        col = StaticSource.__table__.columns["is_active"]
        assert col.nullable is False, "is_active should be NOT NULL"

    def test_created_at_has_timezone(self):
        col = StaticSource.__table__.columns["created_at"]
        assert col.type.timezone is True, "created_at should be DateTime(timezone=True)"

    def test_updated_at_has_timezone(self):
        col = StaticSource.__table__.columns["updated_at"]
        assert col.type.timezone is True, "updated_at should be DateTime(timezone=True)"

    def test_created_at_has_server_default(self):
        col = StaticSource.__table__.columns["created_at"]
        assert col.server_default is not None, "created_at should have server_default"

    def test_updated_at_has_server_default(self):
        col = StaticSource.__table__.columns["updated_at"]
        assert col.server_default is not None, "updated_at should have server_default"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py -v`
Expected: FAIL — `is_active` is currently `nullable=True`, timestamps lack timezone.

- [ ] **Step 4: Apply StaticSource model fixes**

In `backend/app/models/static_sources.py`, modify the `StaticSource` class:

```python
from sqlalchemy.sql import func

# Change is_active:
is_active = Column(Boolean, default=True, nullable=False, index=True)

# Change created_at:
created_at = Column(
    DateTime(timezone=True), nullable=False, server_default=func.now()
)

# Change updated_at:
updated_at = Column(
    DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py::TestStaticSourceModel -v`
Expected: PASS (all 5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/static_sources.py backend/tests/test_models_static_sources.py
git commit -m "fix(models): align StaticSource nullable/timezone with DB schema"
```

### Task 2: Fix StaticSourceAudit model

**Files:**
- Modify: `backend/app/models/static_sources.py:51-64` (StaticSourceAudit class)
- Test: `backend/tests/test_models_static_sources.py` (append)

- [ ] **Step 1: Write failing test for StaticSourceAudit fixes**

Append to `backend/tests/test_models_static_sources.py`:

```python
@pytest.mark.unit
class TestStaticSourceAuditModel:
    """Verify StaticSourceAudit columns match design spec."""

    def test_source_id_has_cascade_delete(self):
        col = StaticSourceAudit.__table__.columns["source_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE", "source_id FK should CASCADE on delete"

    def test_user_id_has_foreign_key(self):
        col = StaticSourceAudit.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1, "user_id should have a ForeignKey"
        assert fks[0].column.table.name == "users"

    def test_user_id_fk_set_null_on_delete(self):
        col = StaticSourceAudit.__table__.columns["user_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "SET NULL", "user_id FK should SET NULL on delete"

    def test_changes_has_server_default(self):
        col = StaticSourceAudit.__table__.columns["changes"]
        assert col.server_default is not None, "changes should have server_default"

    def test_performed_at_has_timezone(self):
        col = StaticSourceAudit.__table__.columns["performed_at"]
        assert col.type.timezone is True, "performed_at should be DateTime(timezone=True)"

    def test_performed_at_has_server_default(self):
        col = StaticSourceAudit.__table__.columns["performed_at"]
        assert col.server_default is not None, "performed_at should have server_default"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py::TestStaticSourceAuditModel -v`
Expected: FAIL — missing FK, missing cascade, no timezone, no server_default.

- [ ] **Step 3: Apply StaticSourceAudit model fixes**

In `backend/app/models/static_sources.py`, modify the `StaticSourceAudit` class:

```python
source_id = Column(
    BigInteger,
    ForeignKey("static_sources.id", ondelete="CASCADE"),
    nullable=False, index=True,
)
action = Column(String(50), nullable=False)
user_id = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
changes = Column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
performed_at = Column(
    DateTime(timezone=True), nullable=True, server_default=func.now()
)
```

Also add these imports at the top of the file (if not already present):
```python
from sqlalchemy import text
from sqlalchemy.sql import func
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py::TestStaticSourceAuditModel -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/static_sources.py backend/tests/test_models_static_sources.py
git commit -m "fix(models): align StaticSourceAudit FK constraints and timestamps"
```

### Task 3: Fix StaticEvidenceUpload model

**Files:**
- Modify: `backend/app/models/static_sources.py:67-95` (StaticEvidenceUpload class)
- Test: `backend/tests/test_models_static_sources.py` (append)

- [ ] **Step 1: Write failing test for StaticEvidenceUpload fixes**

Append to `backend/tests/test_models_static_sources.py`:

```python
@pytest.mark.unit
class TestStaticEvidenceUploadModel:
    """Verify StaticEvidenceUpload columns match design spec."""

    def test_source_id_is_biginteger(self):
        col = StaticEvidenceUpload.__table__.columns["source_id"]
        # BigInteger in SQLAlchemy compiles to BIGINT
        assert isinstance(col.type, BigInteger) or col.type.__class__.__name__ == "BigInteger"

    def test_source_id_has_cascade_delete(self):
        col = StaticEvidenceUpload.__table__.columns["source_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE", "source_id FK should CASCADE on delete"

    def test_uploaded_by_has_set_null_delete(self):
        col = StaticEvidenceUpload.__table__.columns["uploaded_by"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "SET NULL", "uploaded_by FK should SET NULL on delete"

    def test_processed_at_has_timezone(self):
        col = StaticEvidenceUpload.__table__.columns["processed_at"]
        assert col.type.timezone is True

    def test_created_at_has_timezone_and_server_default(self):
        col = StaticEvidenceUpload.__table__.columns["created_at"]
        assert col.type.timezone is True
        assert col.server_default is not None

    def test_updated_at_has_timezone_and_server_default(self):
        col = StaticEvidenceUpload.__table__.columns["updated_at"]
        assert col.type.timezone is True
        assert col.server_default is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py::TestStaticEvidenceUploadModel -v`
Expected: FAIL — `source_id` is `Integer` not `BigInteger`, missing ondelete, no timezone.

- [ ] **Step 3: Apply StaticEvidenceUpload model fixes**

In `backend/app/models/static_sources.py`, modify the `StaticEvidenceUpload` class:

```python
source_id = Column(
    BigInteger,
    ForeignKey("static_sources.id", ondelete="CASCADE"),
    nullable=False, index=True,
)
# ... (other columns unchanged) ...
processed_at = Column(DateTime(timezone=True), nullable=True)
uploaded_by = Column(
    BigInteger,
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)
created_at = Column(
    DateTime(timezone=True), nullable=False, server_default=func.now()
)
updated_at = Column(
    DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_models_static_sources.py::TestStaticEvidenceUploadModel -v`
Expected: PASS (all 6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/static_sources.py backend/tests/test_models_static_sources.py
git commit -m "fix(models): align StaticEvidenceUpload types and FK constraints"
```

### Task 4: Fix DataSourceProgress model (JSON → JSONB)

**Files:**
- Modify: `backend/app/models/progress.py:54`
- Test: `backend/tests/test_models_progress.py` (new)

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_models_progress.py`:

```python
"""Tests for DataSourceProgress model schema alignment."""
import pytest
from sqlalchemy.dialects.postgresql import JSONB

from app.models.progress import DataSourceProgress


@pytest.mark.unit
class TestDataSourceProgressModel:
    def test_progress_metadata_is_jsonb(self):
        col = DataSourceProgress.__table__.columns["metadata"]
        assert isinstance(col.type, JSONB), (
            f"metadata column should be JSONB, got {type(col.type).__name__}"
        )

    def test_progress_metadata_maps_to_metadata_column(self):
        col = DataSourceProgress.__table__.columns["metadata"]
        assert col.name == "metadata", "Python attr progress_metadata should map to DB column 'metadata'"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_models_progress.py -v`
Expected: FAIL — column type is `JSON`, not `JSONB`.

- [ ] **Step 3: Apply fix**

In `backend/app/models/progress.py`, change the import and column:

```python
# Add to imports:
from sqlalchemy.dialects.postgresql import JSONB

# Change line 54:
progress_metadata = Column("metadata", JSONB, default={})
```

Remove `JSON` from the existing import line (if it becomes unused).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_models_progress.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 6: Lint and typecheck**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
make lint
cd backend && uv run mypy app/models/static_sources.py app/models/progress.py --ignore-missing-imports
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/progress.py backend/tests/test_models_progress.py
git commit -m "fix(models): change DataSourceProgress.metadata from JSON to JSONB"
```

### Task 5: Create PR for model fixes

**Files:** None (git operations only)

- [ ] **Step 1: Push and create PR**

```bash
git push -u origin fix/model-schema-alignment
gh pr create --title "fix: align SQLAlchemy models with DB schema" --body "$(cat <<'EOF'
## Summary
- Fix `StaticSource.is_active` nullable, add timezone to timestamps, add server_default
- Fix `StaticSourceAudit` FK constraints (CASCADE/SET NULL), add timezone, add server_default
- Fix `StaticEvidenceUpload.source_id` type (Integer → BigInteger), add FK ondelete, add timezone
- Fix `DataSourceProgress.metadata` type (JSON → JSONB)

Prerequisite for migration squash (see `.planning/2026-03-13-migration-squash-design.md`).

## Test plan
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] New unit tests in `test_models_static_sources.py` and `test_models_progress.py` verify each fix
EOF
)"
```

- [ ] **Step 2: Wait for PR approval and merge**

Do not proceed to Chunk 2 until this PR is merged to `main`.

---

## Chunk 2: Backup, Archive, and Delete Old Migrations

### Task 6: Prepare workspace for squash

**Files:** None (git operations only)

- [ ] **Step 1: Switch to main and pull**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
git checkout main && git pull
```

- [ ] **Step 2: Create squash branch and tag**

```bash
git tag pre-migration-squash
git checkout -b refactor/migration-squash
```

- [ ] **Step 3: Verify DB is at current head**

```bash
cd backend && uv run alembic current
```

Expected: Shows the latest revision as `(head)`.

### Task 7: Full backup and schema baseline

**Files:**
- Create: `.planning/archive/alembic_v1_migrations/` (22 .py files)
- Create: `/tmp/kidneygenetics_baseline_columns.csv` (and 5 more CSVs)

- [ ] **Step 1: Run full backup**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
make db-backup-full
```

Expected: Backup file created successfully.

- [ ] **Step 2: Capture schema baseline as CSVs**

```bash
# Columns
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema = 'public'
  AND table_name != 'alembic_version'
ORDER BY table_name, ordinal_position;
" > /tmp/kidneygenetics_baseline_columns.csv

# Indexes
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' ORDER BY indexname;
" > /tmp/kidneygenetics_baseline_indexes.csv

# Constraints
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT conname, contype, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;
" > /tmp/kidneygenetics_baseline_constraints.csv

# Views
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT viewname, definition FROM pg_views
WHERE schemaname = 'public' ORDER BY viewname;
" > /tmp/kidneygenetics_baseline_views.csv

# Materialized views
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT matviewname, definition FROM pg_matviews
WHERE schemaname = 'public' ORDER BY matviewname;
" > /tmp/kidneygenetics_baseline_matviews.csv

# ENUMs
psql -h localhost -p 5432 -U kidney_user kidney_genetics -A -F',' -c "
SELECT t.typname, e.enumlabel
FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid
ORDER BY t.typname, e.enumsortorder;
" > /tmp/kidneygenetics_baseline_enums.csv
```

- [ ] **Step 3: Verify baseline files exist and are non-empty**

```bash
wc -l /tmp/kidneygenetics_baseline_*.csv
```

Expected: Each file has >1 line (header + data).

- [ ] **Step 4: Archive old migrations**

```bash
mkdir -p .planning/archive/alembic_v1_migrations
cp backend/alembic/versions/*.py .planning/archive/alembic_v1_migrations/
# Don't copy __init__.py to archive (it stays in place)
rm .planning/archive/alembic_v1_migrations/__init__.py 2>/dev/null || true
```

- [ ] **Step 5: Commit archive**

```bash
git add .planning/archive/alembic_v1_migrations/
git commit -m "chore: archive pre-squash Alembic migrations"
```

### Task 8: Delete all old migration files

**Files:**
- Delete: All 22 `.py` files in `backend/alembic/versions/` (keep `__init__.py`)

- [ ] **Step 1: Delete all migration files (NOT __init__.py)**

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend/alembic/versions
# Delete all .py files except __init__.py
find . -maxdepth 1 -name '*.py' ! -name '__init__.py' -delete
```

- [ ] **Step 2: Verify only __init__.py remains**

```bash
ls /home/bernt-popp/development/kidney-genetics-db/backend/alembic/versions/
```

Expected: Only `__init__.py`.

- [ ] **Step 3: Do NOT commit yet** — the autogenerated migration goes in the same commit.

---

## Chunk 3: Generate and Edit Squashed Migration

### Task 9: Autogenerate base migration

**Files:**
- Create: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Create blank test database**

```bash
createdb -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test
```

- [ ] **Step 2: Autogenerate migration against blank DB**

> **Note**: `alembic/env.py` loads `settings.DATABASE_URL` which requires `JWT_SECRET_KEY` to be set.
> The `.env` file provides it, but when overriding `DATABASE_URL`, ensure the rest of `.env` is still loaded
> (it will be, since pydantic-settings reads `.env` first, then env vars override individual keys).

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics_squash_test \
  uv run alembic revision --autogenerate -m "initial_schema_v1" --rev-id 0001
```

> If this fails with a settings validation error, also export `JWT_SECRET_KEY`:
> ```bash
> JWT_SECRET_KEY=dummy DATABASE_URL=postgresql://... uv run alembic revision ...
> ```

Expected: New file created at `backend/alembic/versions/0001_initial_schema_v1.py`.

- [ ] **Step 3: Verify the autogenerated file exists and has table creates**

```bash
grep -c "op.create_table" backend/alembic/versions/0001_initial_schema_v1.py
```

Expected: 22 (one per table including `refresh_tokens`).

- [ ] **Step 4: Drop the test database (will recreate for verification)**

```bash
dropdb -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test
```

### Task 10: Add manual ENUMs to migration

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Add manual ENUM creation BEFORE the first `op.create_table`**

Insert at the beginning of `upgrade()`, before any table creation:

```python
    # -- Section A: Manual ENUMs not captured by autogenerate --
    # backup_status and backup_trigger use create_type=False in the model
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_status AS ENUM ('pending','running','completed','failed','restored');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_trigger AS ENUM ('manual_api','scheduled_cron','pre_restore_safety');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
```

- [ ] **Step 2: Verify the 3 autogenerated ENUMs are also present**

Check that `source_status`, `setting_type`, and `setting_category` are created by autogenerate (they should be via `sa.Enum(...)` or `postgresql.ENUM(...)`).

### Task 11: Add special indexes to migration

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Add 5 special indexes AFTER all `op.create_table` calls**

Append to `upgrade()`, after all table creation:

```python
    # -- Section C: Special indexes not captured by autogenerate --

    # 1. Functional index on UPPER(approved_symbol)
    op.execute(
        "CREATE INDEX idx_gene_symbol_upper ON genes (UPPER(approved_symbol))"
    )

    # 2. GiST index on temporal range
    op.execute(
        "CREATE INDEX idx_genes_valid_time ON genes "
        "USING GIST (tstzrange(valid_from, valid_to))"
    )

    # 3. Partial index on gene_evidence for DiagnosticPanels + Literature
    op.execute(
        "CREATE INDEX idx_gene_evidence_source_detail ON gene_evidence "
        "(source_name, source_detail) "
        "WHERE source_name IN ('DiagnosticPanels', 'Literature')"
    )

    # 4. GIN partial index on DiagnosticPanels providers
    op.execute(
        "CREATE INDEX idx_gene_evidence_providers_gin ON gene_evidence "
        "USING GIN ((evidence_data->'providers')) "
        "WHERE source_name = 'DiagnosticPanels'"
    )

    # 5. GIN partial index on Literature publications
    op.execute(
        "CREATE INDEX idx_gene_evidence_publications_gin ON gene_evidence "
        "USING GIN ((evidence_data->'publications')) "
        "WHERE source_name = 'Literature'"
    )
```

### Task 12: Add views to migration (inline SQL, dependency order)

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Add all 22 regular views + 1 materialized view as inline SQL**

Append to `upgrade()`, after special indexes. Use the exact SQL from `backend/app/db/views.py` but as raw strings — **NEVER import from app.db**.

The creation order follows the dependency table from the design spec (lines 229-254):

```python
    # -- Section D: Views (inline SQL, dependency order) --
    # Source: backend/app/db/views.py — inlined to avoid runtime imports

    # Tier 1: No dependencies (views 1-17)
    op.execute("""CREATE VIEW cache_stats AS
    SELECT cache_entries.namespace,
        count(*) AS total_entries,
        ...
    FROM cache_entries
    GROUP BY cache_entries.namespace""")

    # ... (repeat for all 22 regular views in dependency order) ...

    # Tier 4: gene_scores MATERIALIZED VIEW
    op.execute("""CREATE MATERIALIZED VIEW gene_scores AS
    WITH source_scores_per_gene AS (...)
    SELECT gene_id, approved_symbol, ...
    FROM source_scores_per_gene
    GROUP BY gene_id, approved_symbol, hgnc_id""")

    # gene_scores indexes
    op.execute("CREATE UNIQUE INDEX idx_gene_scores_gene_id ON gene_scores (gene_id)")
    op.execute("CREATE INDEX idx_gene_scores_percentage_score ON gene_scores (percentage_score)")
    op.execute("CREATE INDEX idx_gene_scores_evidence_tier ON gene_scores (evidence_tier)")
    op.execute("REFRESH MATERIALIZED VIEW gene_scores")

    # Tier 5: Depends on gene_scores
    op.execute("""CREATE VIEW gene_list_detailed AS
    SELECT g.id::bigint AS gene_id, ...
    FROM genes g
    LEFT JOIN gene_scores gs ON g.id = gs.gene_id""")
```

**CRITICAL**: For each view, read the `ReplaceableObject` from `backend/app/db/views.py` and use its `.sqltext` attribute verbatim. The algorithm is:

```python
# For each view in ALL_VIEWS (from views.py):
#   if view.object_type == "MATERIALIZED VIEW":
#       op.execute(f"CREATE MATERIALIZED VIEW {view.name} AS {view.sqltext}")
#   else:
#       op.execute(f"CREATE VIEW {view.name} AS {view.sqltext}")
```

Do NOT import from `app.db.views` in the migration. Copy the SQL text as string literals. The full SQL for all 23 views is in `backend/app/db/views.py` (lines 10-658).

The 23 views in creation order are:
1. `cache_stats` (VIEW)
2. `evidence_source_counts` (VIEW)
3. `evidence_classification_weights` (VIEW)
4. `string_ppi_percentiles` (VIEW)
5. `admin_logs_filtered` (VIEW)
6. `datasource_metadata_panelapp` (VIEW)
7. `datasource_metadata_gencc` (VIEW)
8. `v_diagnostic_panel_providers` (VIEW)
9. `v_literature_publications` (VIEW)
10. `source_distribution_hpo` (VIEW)
11. `source_distribution_gencc` (VIEW)
12. `source_distribution_clingen` (VIEW)
13. `source_distribution_diagnosticpanels` (VIEW)
14. `source_distribution_panelapp` (VIEW)
15. `source_distribution_pubtator` (VIEW)
16. `gene_hpo_classifications` (VIEW)
17. `genes_current` (VIEW)
18. `evidence_count_percentiles` (VIEW) — depends on #2
19. `evidence_normalized_scores` (VIEW) — depends on #18, #3
20. `combined_evidence_scores` (VIEW) — depends on #19
21. `evidence_summary_view` (VIEW) — depends on #20
22. `gene_scores` (MATERIALIZED VIEW) — depends on #20
23. `gene_list_detailed` (VIEW) — depends on #22

### Task 13: Add seed data to migration

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Add system_settings seed data (14 rows)**

Append to `upgrade()`, after views:

```python
    # -- Section E: Seed data --
    system_settings_table = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value", postgresql.JSONB),
        sa.column("value_type", sa.String),
        sa.column("category", sa.String),
        sa.column("description", sa.Text),
        sa.column("default_value", postgresql.JSONB),
        sa.column("requires_restart", sa.Boolean),
        sa.column("is_sensitive", sa.Boolean),
        sa.column("is_readonly", sa.Boolean),
    )
    op.bulk_insert(system_settings_table, [
        {
            "key": "cache.default_ttl",
            "value": 3600,
            "value_type": "number",
            "category": "cache",
            "description": "Default cache TTL in seconds",
            "default_value": 3600,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        # ... (all 14 rows as listed in design spec lines 272-287) ...
    ])
```

- [ ] **Step 2: Add static_sources seed data (2 rows)**

```python
    op.execute("""
        INSERT INTO static_sources
            (source_type, source_name, display_name, description,
             scoring_metadata, is_active, created_by)
        VALUES
            ('hybrid', 'DiagnosticPanels', 'Diagnostic Panels',
             'Commercial diagnostic panel evidence from providers',
             '{"type": "count_based", "weight": 1.0}'::jsonb, true, 'system'),
            ('hybrid', 'Literature', 'Literature Evidence',
             'Manually curated literature evidence',
             '{"type": "count_based", "weight": 1.0}'::jsonb, true, 'system')
        ON CONFLICT (source_name) DO NOTHING
    """)
```

- [ ] **Step 3: Add schema_versions seed data (1 row)**

```python
    op.execute("""
        INSERT INTO schema_versions (version, alembic_revision, description)
        VALUES ('0.1.0', '0001', 'Initial consolidated schema')
    """)
```

### Task 14: Write the downgrade function

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Replace the autogenerated downgrade with full reverse**

```python
def downgrade() -> None:
    # -- Drop views in reverse dependency order --
    op.execute("DROP VIEW IF EXISTS gene_list_detailed CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_summary_view CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_count_percentiles CASCADE")
    op.execute("DROP VIEW IF EXISTS genes_current CASCADE")
    op.execute("DROP VIEW IF EXISTS gene_hpo_classifications CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_pubtator CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_panelapp CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_diagnosticpanels CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_clingen CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_gencc CASCADE")
    op.execute("DROP VIEW IF EXISTS source_distribution_hpo CASCADE")
    op.execute("DROP VIEW IF EXISTS v_literature_publications CASCADE")
    op.execute("DROP VIEW IF EXISTS v_diagnostic_panel_providers CASCADE")
    op.execute("DROP VIEW IF EXISTS datasource_metadata_gencc CASCADE")
    op.execute("DROP VIEW IF EXISTS datasource_metadata_panelapp CASCADE")
    op.execute("DROP VIEW IF EXISTS admin_logs_filtered CASCADE")
    op.execute("DROP VIEW IF EXISTS string_ppi_percentiles CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_classification_weights CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE")
    op.execute("DROP VIEW IF EXISTS cache_stats CASCADE")

    # -- Drop special indexes --
    op.execute("DROP INDEX IF EXISTS idx_gene_symbol_upper")
    op.execute("DROP INDEX IF EXISTS idx_genes_valid_time")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_source_detail")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_providers_gin")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_publications_gin")

    # -- Drop all 22 tables (autogenerate order reversed) --
    # (Keep the autogenerated op.drop_table calls but verify all 22 are present)

    # -- Drop ENUMs --
    op.execute("DROP TYPE IF EXISTS backup_trigger")
    op.execute("DROP TYPE IF EXISTS backup_status")
    op.execute("DROP TYPE IF EXISTS setting_category")
    op.execute("DROP TYPE IF EXISTS setting_type")
    op.execute("DROP TYPE IF EXISTS source_status")
```

### Task 15: Set migration metadata and clean up

**Files:**
- Modify: `backend/alembic/versions/0001_initial_schema_v1.py`

- [ ] **Step 1: Verify migration header**

Ensure the top of the file reads:

```python
"""Initial consolidated schema v1

Revision ID: 0001
Revises:
Create Date: 2026-03-XX

Consolidates 22 development-phase migrations into a single clean schema.
All views inlined as raw SQL (no runtime imports from app.db).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
```

- [ ] **Step 2: Lint the migration file**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
make lint
```

Fix any lint errors in the migration file.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "refactor: consolidate 22 Alembic migrations into single initial schema"
```

---

## Chunk 4: Verification, Stamp, and Cleanup

### Task 16: Test migration on blank database

**Files:** None (database operations only)

- [ ] **Step 1: Create fresh test database**

```bash
createdb -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test
```

- [ ] **Step 2: Run migration from scratch**

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics_squash_test \
  uv run alembic upgrade head
```

Expected: Completes with zero errors.

- [ ] **Step 3: Verify Alembic state on test DB**

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics_squash_test \
  uv run alembic current
```

Expected: `0001 (head)`

### Task 17: Structured schema comparison

**Files:** None (verification only)

- [ ] **Step 1: Capture new schema as CSVs**

Run the same 6 SQL queries from Task 7 Step 2, but against `kidneygenetics_squash_test`, saving to `/tmp/kidneygenetics_new_*.csv`.

```bash
psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema = 'public'
  AND table_name != 'alembic_version'
ORDER BY table_name, ordinal_position;
" > /tmp/kidneygenetics_new_columns.csv

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' ORDER BY indexname;
" > /tmp/kidneygenetics_new_indexes.csv

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT conname, contype, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;
" > /tmp/kidneygenetics_new_constraints.csv

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT viewname, definition FROM pg_views
WHERE schemaname = 'public' ORDER BY viewname;
" > /tmp/kidneygenetics_new_views.csv

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT matviewname, definition FROM pg_matviews
WHERE schemaname = 'public' ORDER BY matviewname;
" > /tmp/kidneygenetics_new_matviews.csv

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test -A -F',' -c "
SELECT t.typname, e.enumlabel
FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid
ORDER BY t.typname, e.enumsortorder;
" > /tmp/kidneygenetics_new_enums.csv
```

- [ ] **Step 2: Diff each CSV pair**

```bash
for kind in columns indexes constraints views matviews enums; do
  echo "=== $kind ==="
  diff /tmp/kidneygenetics_baseline_${kind}.csv /tmp/kidneygenetics_new_${kind}.csv || true
  echo ""
done
```

- [ ] **Step 3: Verify all differences are in the expected list**

Every difference must match the expected-differences table from the design spec (lines 336-353). Specifically:

| Difference | Reason |
|---|---|
| `static_sources.version` / `.metadata` columns missing in new | Intentionally dropped (unused) |
| `static_evidence_uploads` 6 dead columns missing in new | Intentionally dropped (unused) |
| `static_evidence_uploads.source_id` integer→bigint | Model fix |
| `static_source_audit` FK ondelete RESTRICT→CASCADE/SET NULL | Model fix |
| `static_*` timestamps without TZ→with TZ | Model fix |
| `data_source_progress.metadata` json→jsonb | Model fix |
| 3 runtime matviews (`source_overlap_statistics`, `gene_distribution_analysis`, `upset_plot_data`) missing in new | Managed by `MaterializedViewManager`, not Alembic |
| Indexes on above 3 matviews missing in new | Created at app startup |

`refresh_tokens` table should be identical in both schemas (present in old DB from migration `285000c93ed5`, and in new DB from autogenerate). Verify it appears in both column CSVs.

**Any difference NOT in this table is a bug. Stop and investigate.**

### Task 18: Verify seed data

**Files:** None (verification only)

- [ ] **Step 1: Check seed row counts**

```bash
psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test \
  -c "SELECT count(*) FROM system_settings"
# Expected: 14

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test \
  -c "SELECT count(*) FROM static_sources WHERE source_name IN ('DiagnosticPanels','Literature')"
# Expected: 2

psql -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test \
  -c "SELECT version, alembic_revision FROM schema_versions"
# Expected: 0.1.0 | 0001
```

### Task 19: Verify Alembic commands

**Files:** None (verification only)

- [ ] **Step 1: Run alembic check against test DB**

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics_squash_test \
  uv run alembic history
```

Expected: `<base> -> 0001 (head), initial_schema_v1`

```bash
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics_squash_test \
  uv run alembic check
```

Expected: `No new upgrade operations detected` (or minor cosmetic diffs that are acceptable).

### Task 20: Stamp existing dev database

**Files:** None (database operation only)

- [ ] **Step 1: Stamp dev DB to new head**

```bash
cd /home/bernt-popp/development/kidney-genetics-db/backend
uv run alembic stamp 0001
```

- [ ] **Step 2: Verify stamp**

```bash
uv run alembic current
```

Expected: `0001 (head)`

### Task 21: Full application verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
make test
```

Expected: All tests pass.

- [ ] **Step 2: Run lint and typecheck**

```bash
make lint
cd backend && uv run mypy app/db/ app/models/ --ignore-missing-imports
```

Expected: No errors.

- [ ] **Step 3: Smoke test the application**

```bash
make hybrid-up && make backend
# In another terminal: verify http://localhost:8000/docs loads
# Verify: GET /api/genes returns data
```

### Task 22: Cleanup and create PR

**Files:** None (git + cleanup operations)

- [ ] **Step 1: Drop test database**

```bash
dropdb -h localhost -p 5432 -U kidney_user kidney_genetics_squash_test
```

- [ ] **Step 2: Clean up temp files**

```bash
rm -f /tmp/kidneygenetics_baseline_*.csv /tmp/kidneygenetics_new_*.csv
```

- [ ] **Step 3: Push and create PR**

```bash
cd /home/bernt-popp/development/kidney-genetics-db
git push -u origin refactor/migration-squash
gh pr create --title "refactor: consolidate Alembic migrations into single initial schema" --body "$(cat <<'EOF'
## Summary
- Archives 22 development-phase migrations to `.planning/archive/alembic_v1_migrations/`
- Replaces them with a single `0001_initial_schema_v1.py` migration
- All 23 views inlined as raw SQL (no runtime imports from `app.db`)
- 5 special indexes, 5 ENUMs, 17 seed data rows included
- Verified via structured SQL comparison against baseline

Depends on: #XX (model fixes PR)
Design spec: `.planning/2026-03-13-migration-squash-design.md`

## Test plan
- [ ] `alembic upgrade head` succeeds on blank database
- [ ] Schema diff shows only expected differences (dead columns, model fixes, runtime matviews)
- [ ] Seed data verified (14 settings, 2 static sources, 1 schema version)
- [ ] `alembic stamp 0001` works on existing dev DB
- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] Application starts and `/docs` loads
EOF
)"
```

---

## Rollback Plan

If anything goes wrong at any point:

```bash
# Restore git state
git checkout pre-migration-squash

# Restore database from backup
make db-restore

# Verify
cd backend && uv run alembic current
make test
```
