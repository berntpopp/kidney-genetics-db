# Alembic Migration Squash Design

**Date**: 2026-03-13
**Status**: Approved
**Goal**: Consolidate 18 development-phase Alembic migrations into a single clean initial schema migration.

---

## Context

The project has accumulated 18 migrations during development, including a branch + merge point, iterative view fixes, and migrations that import from `app.db.views` at runtime (known to break when view definitions change). Squashing produces a faster `alembic upgrade head` on fresh databases and a cleaner foundation for future migrations.

## Approach: Autogenerate + Manual Additions

1. Fix SQLAlchemy model bugs so models are the source of truth (separate PR)
2. Delete old migrations, then autogenerate a new one against a blank database (captures tables, columns, indexes, constraints)
3. Manually add views, materialized views, special indexes, ENUMs, and seed data (inline SQL, no runtime imports)
4. Verify by structured SQL comparison between old and new schemas
5. Stamp existing databases to the new head

## Scope: What This Migration Covers and Does Not Cover

**Included**: All 21 tables, 5 ENUMs, 22 regular views + 1 materialized view (from `app.db.views`), special indexes, and seed data.

**Excluded by design**: 3 runtime materialized views defined in `app.db.materialized_views.py`:
- `source_overlap_statistics`
- `gene_distribution_analysis`
- `upset_plot_data`

These are NOT managed by Alembic migrations. They are created at application startup by `MaterializedViewManager.initialize_all_views()` and will appear in existing DB schema dumps but NOT in the squashed migration output. The schema comparison in Phase 3 must account for this (see expected differences table).

---

## Prerequisites

### PR 1: SQLAlchemy Model Fixes

Fix genuine model-DB drift before squashing so autogenerate produces the correct schema.

#### Bugs to Fix

**`backend/app/models/static_sources.py` — `StaticSource`**:
- `is_active`: Change `nullable=True` to `nullable=False`
- `created_at`: Change `DateTime` to `DateTime(timezone=True)`, use `server_default=func.now()`
- `updated_at`: Change `DateTime` to `DateTime(timezone=True)`, use `server_default=func.now()`, `onupdate=func.now()`

**`backend/app/models/static_sources.py` — `StaticSourceAudit`**:
- `source_id`: Add `ondelete="CASCADE"` to ForeignKey
- `user_id`: Add `ForeignKey("users.id", ondelete="SET NULL")`
- `changes`: Add `server_default=text("'{}'::jsonb")`
- `performed_at`: Change `DateTime` to `DateTime(timezone=True)`, add `server_default=func.now()`

**`backend/app/models/static_sources.py` — `StaticEvidenceUpload`**:
- `source_id`: Change `Integer` to `BigInteger`, add `ondelete="CASCADE"` to ForeignKey
- `uploaded_by`: Add `ondelete="SET NULL"` to ForeignKey
- `processed_at`, `created_at`, `updated_at`: Change `DateTime` to `DateTime(timezone=True)`, use `server_default=func.now()` where applicable

**`backend/app/models/progress.py` — `DataSourceProgress`**:
- `progress_metadata`: Change `JSON` to `JSONB` (import from `sqlalchemy.dialects.postgresql`). Note: the Python attribute is `progress_metadata` but maps to DB column `metadata` via `Column("metadata", JSON, ...)` — preserve this column name mapping when changing the type to `Column("metadata", JSONB, ...)`.

#### Dead Columns to Intentionally Drop

These exist in the current DB but are unused by application code. The squashed migration will not create them. Existing DBs retain them harmlessly after `alembic stamp`.

**`static_sources`**: `version` (TEXT), `metadata` (JSONB)
**`static_evidence_uploads`**: `file_size`, `content_hash`, `processing_status`, `rows_processed`, `rows_failed`, `error_log`

#### Cosmetic Differences to Accept

Type differences like `String(255)` vs `TEXT` and `String(50)` vs `TEXT` are functionally identical in PostgreSQL. The model's length constraints add application-level validation.

#### Workflow

1. Branch: `fix/model-schema-alignment`
2. Apply fixes, run `make lint` + `make test`
3. Merge via PR before starting the squash

### PR 3: Pydantic v2 Migration (Independent)

Separate PR, no dependency on the squash. Converts 13 `class Config:` to `ConfigDict`, 12 `.json()` to `.model_dump_json()`, 2 `.dict()` to `.model_dump()`.

---

## Phase 1: Backup & Snapshot

**Preconditions**: PR 1 merged, all tests passing, DB at current head.

### Steps

1. Git tag: `git tag pre-migration-squash`
2. Full backup: `make db-backup-full`
3. Schema baseline via structured SQL queries (saved as CSVs for later comparison):

```sql
-- Columns (exclude alembic_version to avoid false positives)
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns WHERE table_schema = 'public'
  AND table_name != 'alembic_version'
ORDER BY table_name, ordinal_position;

-- Indexes
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' ORDER BY indexname;

-- Constraints
SELECT conname, contype, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint WHERE connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;

-- Views
SELECT viewname, definition FROM pg_views
WHERE schemaname = 'public' ORDER BY viewname;

-- Materialized views
SELECT matviewname, definition FROM pg_matviews
WHERE schemaname = 'public' ORDER BY matviewname;

-- ENUMs
SELECT t.typname, e.enumlabel
FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid
ORDER BY t.typname, e.enumsortorder;
```

4. Archive old migrations:
```bash
mkdir -p .planning/archive/alembic_v1_migrations
cp -r backend/alembic/versions/*.py .planning/archive/alembic_v1_migrations/
```

---

## Phase 2: Generate Squashed Migration

### Step 1: Delete Old Migrations (MUST come before autogenerate)

Remove all 18 `.py` migration files from `backend/alembic/versions/` (keep `__init__.py`). They are already preserved in the git tag and `.planning/archive/alembic_v1_migrations/` from Phase 1.

**Why first**: If old migrations remain when autogenerate runs, Alembic will see the old chain's head AND the new `0001` migration (both with `down_revision=None`), causing a `Multiple heads` error.

```bash
cd backend/alembic/versions
rm -f 001_modern_complete_schema.py ae289b364fa1_*.py be048c9b1b53_*.py \
      68b329da9893_*.py f5ee05ff38aa_*.py 2f6d3f0fa406_*.py \
      15ad8825b8e5_*.py e3528d838498_*.py 02bb6061236e_*.py \
      8f42e6080805_*.py 77c32f88d831_*.py d2f24d1ed798_*.py \
      cc1fbec614ed_*.py df7756c38ecd_*.py 21d650ef9500_*.py \
      a1b2c3d4e5f6_*.py 57009b4faa2c_*.py a9f3b2c1d4e5_*.py
```

### Step 2: Autogenerate Against Blank DB

```bash
createdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test

DATABASE_URL=postgresql://kidneygenetics:<password>@localhost:5432/kidneygenetics_squash_test \
  cd backend && uv run alembic revision --autogenerate -m "initial_schema_v1" --rev-id 0001
```

Autogenerate captures all 21 tables with columns, PKs, FKs, unique constraints, and standard indexes (including those from model `index=True` declarations like the 3 `gene_evidence` performance indexes). It also auto-creates `source_status`, `setting_type`, and `setting_category` ENUMs.

Autogenerate does NOT capture: views, materialized views, `backup_status`/`backup_trigger` ENUMs (`create_type=False`), functional/GiST indexes, partial indexes from raw SQL, or seed data.

**Note**: `alembic/env.py` has `compare_type=True` enabled. Since we are comparing models against an empty database (not an existing one with `TEXT` vs `String(255)` differences), this will not cause issues during autogenerate. It may flag cosmetic differences during future `alembic check` runs against existing stamped databases — this is acceptable.

### Step 3: Edit the Migration

Structure the migration file as:

```python
"""Initial consolidated schema v1

Revision ID: 0001
Revises: None
Create Date: 2026-03-XX

Consolidates 18 development-phase migrations into a single clean schema.
All views inlined as raw SQL (no runtime imports from app.db).
"""

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
```

#### Section A: Manual ENUMs (before tables)

```python
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

#### Section B: Tables (autogenerated)

All 21 tables as produced by autogenerate. Tables:
genes, users, annotation_sources, gene_annotations, annotation_history, gene_curations, gene_evidence, gene_normalization_staging, gene_normalization_log, pipeline_runs, data_source_progress, static_sources, static_source_audit, static_evidence_uploads, cache_entries, system_logs, backup_jobs, data_releases, schema_versions, system_settings, setting_audit_log.

**Key constraints to verify in autogenerate output**:
- `unique_gene_source` on gene_annotations(gene_id, source) — 2-column unique, NOT the old 3-column version
- `gene_evidence_source_idx` on gene_evidence(gene_id, source_name, source_detail)
- `uq_cache_entries_cache_key` on cache_entries(cache_key)
- All `ondelete` behaviors on foreign keys match models

#### Section C: Special Indexes (after tables)

5 indexes not captured by autogenerate:

1. `idx_gene_symbol_upper` — functional: `UPPER(approved_symbol)` on genes
2. `idx_genes_valid_time` — GiST: `tstzrange(valid_from, valid_to)` on genes
3. `idx_gene_evidence_source_detail` — partial: `(source_name, source_detail) WHERE source_name IN ('DiagnosticPanels', 'Literature')`
4. `idx_gene_evidence_providers_gin` — GIN partial: `(evidence_data->'providers') WHERE source_name = 'DiagnosticPanels'`
5. `idx_gene_evidence_publications_gin` — GIN partial: `(evidence_data->'publications') WHERE source_name = 'Literature'`

#### Section D: Views (inline SQL, dependency order)

All 23 views inlined as raw SQL strings. Never import from `app.db.views`.

Creation order:

| # | View | Type | Depends On |
|---|------|------|------------|
| 1 | cache_stats | VIEW | — |
| 2 | evidence_source_counts | VIEW | — |
| 3 | evidence_classification_weights | VIEW | — |
| 4 | string_ppi_percentiles | VIEW | — |
| 5 | admin_logs_filtered | VIEW | — |
| 6 | datasource_metadata_panelapp | VIEW | — |
| 7 | datasource_metadata_gencc | VIEW | — |
| 8 | v_diagnostic_panel_providers | VIEW | — |
| 9 | v_literature_publications | VIEW | — |
| 10 | source_distribution_hpo | VIEW | — |
| 11 | source_distribution_gencc | VIEW | — |
| 12 | source_distribution_clingen | VIEW | — |
| 13 | source_distribution_diagnosticpanels | VIEW | — |
| 14 | source_distribution_panelapp | VIEW | — |
| 15 | source_distribution_pubtator | VIEW | — |
| 16 | gene_hpo_classifications | VIEW | — |
| 17 | genes_current | VIEW | — |
| 18 | evidence_count_percentiles | VIEW | #2 |
| 19 | evidence_normalized_scores | VIEW | #18, #3 |
| 20 | combined_evidence_scores | VIEW | #19 |
| 21 | evidence_summary_view | VIEW | #20 |
| 22 | gene_scores | MATERIALIZED | #20 |
| 23 | gene_list_detailed | VIEW | #22 |

After gene_scores creation:
```python
op.execute("CREATE UNIQUE INDEX idx_gene_scores_gene_id ON gene_scores (gene_id)")
op.execute("CREATE INDEX idx_gene_scores_percentage_score ON gene_scores (percentage_score)")
op.execute("CREATE INDEX idx_gene_scores_evidence_tier ON gene_scores (evidence_tier)")
op.execute("REFRESH MATERIALIZED VIEW gene_scores")
```

#### Section E: Seed Data (17 rows)

**system_settings** (14 rows via `op.bulk_insert`):

The `op.bulk_insert` must include ALL NOT NULL columns: `key`, `value`, `value_type`, `category`, `default_value`, `requires_restart`, `is_sensitive`, `is_readonly`. The `description` column is nullable but should be included for documentation. Summary of rows:

| key | value | value_type | category | default_value | description |
|-----|-------|------------|----------|---------------|-------------|
| cache.default_ttl | 3600 | number | cache | 3600 | Default cache TTL in seconds |
| cache.max_memory_size | 1000 | number | cache | 1000 | Maximum L1 cache entries |
| cache.cleanup_interval | 3600 | number | cache | 3600 | Cache cleanup interval in seconds |
| security.jwt_expire_minutes | 30 | number | security | 30 | JWT token expiration in minutes |
| security.max_login_attempts | 5 | number | security | 5 | Max failed login attempts before lockout |
| security.account_lockout_minutes | 15 | number | security | 15 | Account lockout duration in minutes |
| security.jwt_secret_key | "***PLACEHOLDER***" | string | security | "***PLACEHOLDER***" | JWT signing secret key (is_sensitive=true) |
| pipeline.hgnc_batch_size | 50 | number | pipeline | 50 | HGNC API batch size |
| pipeline.hgnc_retry_attempts | 3 | number | pipeline | 3 | HGNC API retry attempts |
| pipeline.hgnc_cache_enabled | true | boolean | pipeline | true | Enable HGNC response caching |
| backup.retention_days | 7 | number | backup | 7 | Backup retention period in days |
| backup.compression_level | 6 | number | backup | 6 | pg_dump compression level (0-9) |
| features.auto_update_enabled | true | boolean | features | true | Enable automatic source updates |
| logging.log_retention_days | 30 | number | logging | 30 | Days to retain system logs before cleanup |

All rows have `requires_restart=false`, `is_sensitive=false`, `is_readonly=false` except `security.jwt_secret_key` which has `is_sensitive=true`.

**static_sources** (2 rows via `INSERT ... ON CONFLICT DO NOTHING`):

The INSERT must include all NOT NULL columns: `source_type`, `source_name`, `display_name`, `scoring_metadata` (JSONB, NOT NULL).

| source_name | source_type | display_name | scoring_metadata | description |
|-------------|-------------|--------------|------------------|-------------|
| DiagnosticPanels | hybrid | Diagnostic Panels | `{"type": "count_based", "weight": 1.0}` | Commercial diagnostic panel evidence from providers |
| Literature | hybrid | Literature Evidence | `{"type": "count_based", "weight": 1.0}` | Manually curated literature evidence |

Both rows also include `is_active=true`, `created_by='system'`.

**schema_versions** (1 row):

| version | alembic_revision | description |
|---------|-----------------|-------------|
| 0.1.0 | 0001 | Initial consolidated schema |

#### Downgrade Function

Reverse order: drop views (23→1) → drop materialized view indexes → drop special indexes (5) → drop tables (21) → drop ENUMs (5: backup_trigger, backup_status, setting_category, setting_type, source_status).

### Note on Migration Deletion

Old migrations were already deleted in Step 1 (required before autogenerate to avoid multiple-heads error). They are preserved in the git tag `pre-migration-squash` and in `.planning/archive/alembic_v1_migrations/`.

---

## Phase 3: Verification

### Step 1: Test on Blank Database

```bash
dropdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test
createdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test
DATABASE_URL=postgresql://kidneygenetics:<password>@localhost:5432/kidneygenetics_squash_test \
  cd backend && uv run alembic upgrade head
```

Must succeed with zero errors.

### Step 2: Structured Schema Comparison

Run the 6 SQL queries from Phase 1 against the test database, save as CSVs, diff against baseline.

**Expected differences** (all intentional from model fixes):

| Object | Old DB | New DB | Reason |
|--------|--------|--------|--------|
| static_sources.version | EXISTS | MISSING | Dropped (unused) |
| static_sources.metadata | EXISTS | MISSING | Dropped (replaced by source_metadata) |
| static_evidence_uploads.file_size | EXISTS | MISSING | Dropped (unused) |
| static_evidence_uploads.content_hash | EXISTS | MISSING | Dropped (replaced by file_hash) |
| static_evidence_uploads.processing_status | EXISTS | MISSING | Dropped (unused) |
| static_evidence_uploads.rows_processed | EXISTS | MISSING | Dropped (replaced by gene_count) |
| static_evidence_uploads.rows_failed | EXISTS | MISSING | Dropped (replaced by genes_failed) |
| static_evidence_uploads.error_log | EXISTS | MISSING | Dropped (replaced by processing_log) |
| static_evidence_uploads.source_id | integer | bigint | Model fix |
| static_source_audit FK ondelete | RESTRICT | CASCADE/SET NULL | Model fix |
| static_* timestamps | without TZ | with TZ | Model fix |
| data_source_progress.metadata | json | jsonb | Model fix (JSON→JSONB) |
| source_overlap_statistics (matview) | EXISTS | MISSING | Runtime-managed by MaterializedViewManager, not Alembic |
| gene_distribution_analysis (matview) | EXISTS | MISSING | Runtime-managed by MaterializedViewManager, not Alembic |
| upset_plot_data (matview) | EXISTS | MISSING | Runtime-managed by MaterializedViewManager, not Alembic |
| indexes on above 3 matviews | EXISTS | MISSING | Created by MaterializedViewManager at app startup |

Any difference not in this table is a bug. Stop and investigate.

**Note on `alembic check`**: When run against the stamped dev database, `alembic check` may report the 3 runtime materialized views as unrecognized objects. This is expected — they are not in `ALL_VIEWS` (which `env.py`'s `include_object` uses for filtering). If this proves noisy, the `include_object` function in `env.py` can be extended to also exclude materialized views from `MaterializedViewManager.MATERIALIZED_VIEWS`, but this is optional.

### Step 3: Verify Alembic State

```bash
cd backend
uv run alembic current   # Expected: 0001 (head)
uv run alembic history   # Expected: <base> -> 0001 (head), initial_schema_v1
uv run alembic check     # Expected: No new upgrade operations detected
```

### Step 4: Stamp Existing Dev Database

```bash
cd backend && uv run alembic stamp 0001
uv run alembic current  # Expected: 0001 (head)
```

### Step 5: Full Application Verification

```bash
make test
make lint
cd backend && uv run mypy app/db/ app/models/ --ignore-missing-imports
make hybrid-up && make backend  # Verify /docs loads
```

### Step 6: Verify Seed Data

```bash
psql -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test \
  -c "SELECT count(*) FROM system_settings"  # Expected: 14

psql -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test \
  -c "SELECT count(*) FROM static_sources WHERE source_name IN ('DiagnosticPanels','Literature')"  # Expected: 2

psql -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test \
  -c "SELECT version, alembic_revision FROM schema_versions"  # Expected: 0.1.0, 0001
```

---

## Phase 4: Cleanup & Commit

```bash
dropdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test
rm -f /tmp/schema_before_*.sql /tmp/kidneygenetics_*_columns.csv
```

### Commits

**Commit 1**: `chore: archive pre-squash Alembic migrations`
**Commit 2**: `refactor: consolidate 18 Alembic migrations into single initial schema`

---

## Rollback Plan

```bash
git checkout pre-migration-squash
make db-restore  # From backup
cd backend && uv run alembic current  # Verify restored state
make test
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Schema mismatch after squash | Structured SQL comparison with expected-differences table |
| Lost seed data | Explicitly included in migration with exact values from audit |
| Views break | All 23 views inlined as SQL; verified by blank-DB test |
| Runtime imports break future migrations | Zero imports from app.db in the new migration |
| Existing DB breaks after stamp | Stamp only changes alembic_version; dead columns remain harmlessly |
| Need to rollback | Git tag + make db-backup-full + documented restore procedure |
| Autogenerate misses objects | Complete manual checklist: 2 ENUMs, 5 indexes, 23 views, 17 seed rows |
| `alembic check` shows drift | Run immediately after squash; any drift = model bug to fix first |

---

## Execution Order

| Step | Action | Depends On |
|------|--------|------------|
| 0 | PR: SQLAlchemy model fixes | Nothing |
| 1 | Backup + schema baseline | PR 0 merged |
| 2 | Autogenerate + manual edits + delete old | Step 1 |
| 3 | Verification (blank DB + structured diff + stamp + tests) | Step 2 |
| 4 | Cleanup + commit + PR | Step 3 |
| — | PR: Pydantic v2 migration (independent) | Nothing |

## Files Affected

- `backend/alembic/versions/*.py` — 18 files replaced with 1
- `backend/alembic/versions/__init__.py` — unchanged
- `backend/alembic/env.py` — unchanged
- `backend/alembic.ini` — unchanged
- `.planning/archive/alembic_v1_migrations/` — archive of old files
- `backend/app/models/static_sources.py` — model fixes (PR 0)
- `backend/app/models/progress.py` — model fix (PR 0)
