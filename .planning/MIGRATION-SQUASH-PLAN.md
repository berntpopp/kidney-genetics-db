# Alembic Migration Squash Plan

**Goal**: Consolidate 18 development-phase migrations into a single clean initial migration.

**Date**: 2026-03-13
**Current HEAD**: `a9f3b2c1d4e5` (add_log_retention_days_setting)
**Migration count**: 18 (including 1 merge point)

---

## Why Squash?

- 18 migrations accumulated during development with iterative changes (add view → fix view, add column → modify column)
- Branch + merge point adds unnecessary complexity
- Some migrations import from `app.db.views` at runtime — known to break when view definitions change
- Faster `alembic upgrade head` on fresh databases
- Cleaner history for the production-ready codebase going forward

## Approach: Hybrid (Autogenerate + Manual Views)

Based on Alembic maintainer guidance and community best practices:

1. **Autogenerate** a new migration against a blank database → captures tables, columns, indexes, constraints
2. **Manually add** all views and materialized views (inline SQL, NOT runtime imports)
3. **Verify** by comparing `pg_dump -s` output between old and new schema
4. **Stamp** existing databases to the new head

> **Note**: Alembic has no built-in squash command. The official cookbook recommends this pattern.

---

## Pre-Squash Checklist

- [ ] All tests passing (`make test`)
- [ ] Database is at current head (`alembic current` shows `a9f3b2c1d4e5`)
- [ ] No pending uncommitted model changes
- [ ] No other developers with in-flight migration branches

---

## Step-by-Step Plan

### Phase 1: Backup & Snapshot (CRITICAL — Do First)

```bash
# 1a. Git tag the current state
git tag pre-migration-squash

# 1b. Full database backup (migrations + schema + data)
make db-backup-full

# 1c. Schema-only dump for comparison baseline
cd backend
pg_dump -s --no-owner --no-acl -h localhost -p 5432 -U kidneygenetics kidneygenetics_dev > /tmp/schema_before_squash.sql

# 1d. Archive old migrations (keep in repo history via git tag, move to archive)
mkdir -p .planning/archive/alembic_v1_migrations
cp -r backend/alembic/versions/*.py .planning/archive/alembic_v1_migrations/
```

**Verification**: Confirm backup file exists, git tag created, and archive directory populated.

### Phase 2: Generate Squashed Migration

```bash
# 2a. Create a completely blank database for autogenerate
createdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test

# 2b. Point Alembic at blank DB and autogenerate
# (Temporarily override DATABASE_URL or use env var)
DATABASE_URL=postgresql://kidneygenetics:password@localhost:5432/kidneygenetics_squash_test \
  cd backend && uv run alembic revision --autogenerate -m "initial_schema_v1" --rev-id 0001

# 2c. Review the generated migration — autogenerate will NOT capture:
#   - Views (23 regular views)
#   - Materialized views (gene_scores)
#   - Custom functions (create_system_log, etc.)
#   - Triggers
#   - Data seeding (annotation_sources rows, etc.)
```

### Phase 3: Manually Complete the Migration

Edit the generated migration to add what autogenerate misses:

1. **Views**: Inline all 23 view CREATE statements directly in the migration SQL
   - Use the current SQL from `app.db.views` but as **raw strings**, not imports
   - Respect dependency order (topological sort already defined in `views.py`)
   - Group: INITIAL_VIEWS → TEMPORAL_VIEWS → DASHBOARD_VIEWS → HPO_CLASSIFICATION_VIEWS

2. **Materialized Views**: Inline the `gene_scores` materialized view SQL
   - Include the unique index on `gene_id` for concurrent refresh

3. **Custom Functions**: Add `create_system_log()` and other DB functions

4. **Downgrade**: Drop views (reverse dependency order) → drop materialized views → drop tables

5. **Set metadata**:
   ```python
   revision = '0001'
   down_revision = None  # This is the new base
   branch_labels = None
   depends_on = None
   ```

### Phase 4: Delete Old Migrations

```bash
# Remove all old migration files (they're preserved in git tag + archive)
rm backend/alembic/versions/001_modern_complete_schema.py
rm backend/alembic/versions/ae289b364fa1_*.py
rm backend/alembic/versions/be048c9b1b53_*.py
rm backend/alembic/versions/68b329da9893_*.py
rm backend/alembic/versions/f5ee05ff38aa_*.py
rm backend/alembic/versions/2f6d3f0fa406_*.py
rm backend/alembic/versions/15ad8825b8e5_*.py
rm backend/alembic/versions/e3528d838498_*.py
rm backend/alembic/versions/02bb6061236e_*.py
rm backend/alembic/versions/8f42e6080805_*.py
rm backend/alembic/versions/77c32f88d831_*.py
rm backend/alembic/versions/d2f24d1ed798_*.py
rm backend/alembic/versions/cc1fbec614ed_*.py
rm backend/alembic/versions/df7756c38ecd_*.py
rm backend/alembic/versions/21d650ef9500_*.py
rm backend/alembic/versions/a1b2c3d4e5f6_*.py
rm backend/alembic/versions/57009b4faa2c_*.py
rm backend/alembic/versions/a9f3b2c1d4e5_*.py
```

### Phase 5: Test on Blank Database

```bash
# 5a. Drop the test DB and recreate
dropdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test
createdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test

# 5b. Run the squashed migration from scratch
DATABASE_URL=postgresql://kidneygenetics:password@localhost:5432/kidneygenetics_squash_test \
  cd backend && uv run alembic upgrade head

# 5c. Dump the new schema
pg_dump -s --no-owner --no-acl -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test > /tmp/schema_after_squash.sql

# 5d. Compare schemas (should be identical except alembic_version content)
diff <(grep -v 'alembic_version' /tmp/schema_before_squash.sql | sort) \
     <(grep -v 'alembic_version' /tmp/schema_after_squash.sql | sort)
```

**Acceptance criteria**: Zero diff (excluding `alembic_version` row).

### Phase 6: Stamp Existing Development Database

```bash
# On the existing dev database that already has all tables:
cd backend && uv run alembic stamp 0001

# Verify
cd backend && uv run alembic current
# Should show: 0001 (head)
```

> **WARNING**: `alembic stamp` does NOT run any migration code. It only updates the `alembic_version` table. This is safe ONLY because the schema already matches.

### Phase 7: Full Verification

```bash
# 7a. Run all backend tests against the stamped database
make test

# 7b. Run lint and type checks
make lint
cd backend && uv run mypy app/db/ --ignore-missing-imports

# 7c. Verify Alembic state
cd backend && uv run alembic current   # Should show 0001 (head)
cd backend && uv run alembic history   # Should show single migration
cd backend && uv run alembic check     # Should show "No new upgrade operations detected"

# 7d. Start the app and verify functionality
make hybrid-up
make backend  # Verify startup, check /docs
make frontend # Verify UI loads
```

### Phase 8: Cleanup

```bash
# Drop the test database
dropdb -h localhost -p 5432 -U kidneygenetics kidneygenetics_squash_test

# Remove temp files
rm /tmp/schema_before_squash.sql /tmp/schema_after_squash.sql

# Commit
git add -A
git commit -m "squash: consolidate 18 development migrations into single initial schema"
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Schema mismatch after squash | Phase 5 diff comparison catches this |
| Lost data migrations / seed data | Review each old migration for `op.execute(INSERT...)` statements; extract to separate seed script if found |
| Views not captured by autogenerate | Phase 3 manual step; verified by schema diff |
| Runtime imports break future migrations | Inline all SQL — never import from `app.db.views` in migrations |
| Existing DB breaks after stamp | Stamp only changes `alembic_version`; no schema changes |
| Need to rollback | Git tag `pre-migration-squash` + `make db-backup-full` backup |

## Rollback Plan

If anything goes wrong:

```bash
# 1. Restore git state
git checkout pre-migration-squash

# 2. Restore database from backup
make db-restore  # Or manual pg_restore from backup file

# 3. Verify
cd backend && uv run alembic current
make test
```

---

## Key Decisions

1. **Inline SQL for views** (not runtime imports) — prevents the known breakage when `app.db.views` changes
2. **Single migration file** — not a "squash merge" migration; a clean rewrite
3. **Revision ID `0001`** — clean, readable, clearly the new starting point
4. **Keep old files in git history** — `git tag` preserves full history; archive copy for reference
5. **No downgrade support for pre-squash states** — acceptable for a development-phase squash

## Files Affected

- `backend/alembic/versions/*.py` — all 18 files replaced with 1
- `backend/alembic/versions/__init__.py` — unchanged
- `backend/alembic/env.py` — no changes needed
- `backend/alembic.ini` — no changes needed
- `.planning/archive/alembic_v1_migrations/` — archive of old files

## Estimated Effort

- Phase 1 (Backup): ~5 minutes
- Phase 2 (Autogenerate): ~10 minutes
- Phase 3 (Manual views/functions): ~30-45 minutes (most complex step)
- Phase 4 (Delete old): ~2 minutes
- Phase 5 (Test blank DB): ~10 minutes
- Phase 6 (Stamp): ~2 minutes
- Phase 7 (Full verification): ~15 minutes
- Phase 8 (Cleanup): ~5 minutes
