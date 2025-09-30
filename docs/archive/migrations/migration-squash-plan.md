# Migration Squash Plan - Fix Double Migration Issue

## Date: 2025-09-26
## Issue: https://github.com/berntpopp/kidney-genetics-db/issues/15
## Branch: fix/database-migration-schema-sync

---

## 🔴 PROBLEM IDENTIFIED

### Current Situation
We have **TWO migrations** when we should have **ONE squashed migration**:
1. `001_modern_complete_schema.py` - The intended squashed migration
2. `002_modern_complete_fixed.py` - Redundant incremental fix

### Root Cause Analysis
1. Initially created `001_modern_complete_schema.py` WITHOUT all AnnotationSource fields
2. Applied migration to database
3. Discovered missing fields (is_active, priority, display_name, etc.)
4. Created `002_modern_complete_fixed.py` to add missing fields
5. Later UPDATED `001_modern_complete_schema.py` to include all fields
6. **Result**: 001 now has everything, making 002 redundant

### Evidence
```python
# 001_modern_complete_schema.py ALREADY contains:
sa.Column('display_name', sa.Text(), nullable=False),
sa.Column('base_url', sa.Text(), nullable=True),
sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')),
sa.Column('update_frequency', sa.Text(), nullable=True),
sa.Column('last_update', sa.DateTime(timezone=True), nullable=True),
sa.Column('next_update', sa.DateTime(timezone=True), nullable=True),
sa.Column('config', sa.dialects.postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
```

---

## ✅ SOLUTION: TRUE SINGLE MIGRATION

### Goals
- **Single migration file**: Only `001_modern_complete_schema.py`
- **Clean history**: No incremental fixes
- **Proper squashing**: All schema changes in one place
- **Match issue #15**: Achieve the original squashing goal

### Action Plan

#### Step 1: Backup Current State
```bash
# Create safety backup
make db-backup-full
git add -A && git commit -m "chore: Backup before migration squash"
```

#### Step 2: Remove Redundant Migration
```bash
# Delete the redundant migration file
rm backend/alembic/versions/002_modern_complete_fixed.py
```

#### Step 3: Clean Database & Alembic History
```bash
# Stop services
make hybrid-down

# Drop and recreate database completely
docker exec kidney_genetics_postgres psql -U postgres -c \
  "DROP DATABASE IF EXISTS kidney_genetics_db; CREATE DATABASE kidney_genetics_db;"
```

#### Step 4: Apply Single Squashed Migration
```bash
# Start services
make hybrid-up

# Apply the ONE migration
cd backend && uv run alembic upgrade head

# Verify we have only one migration
uv run alembic current  # Should show: 001_modern_complete (head)
uv run alembic history  # Should show only ONE migration
```

#### Step 5: Reinitialize Data
```bash
# Initialize annotation sources
cd backend && uv run python -m app.scripts.init_annotation_sources

# Restart backend to pick up changes
make backend
```

#### Step 6: Verify Success
```bash
# Check migration status
cd backend && uv run alembic history --verbose
# Should show ONLY 001_modern_complete as (head)

# Test annotation sources endpoint
curl -s http://localhost:8000/api/annotations/sources | jq length
# Should return 8 sources

# Check database structure
docker exec kidney_genetics_postgres psql -U postgres -d kidney_genetics_db -c \
  "\d annotation_sources"
# Should show all columns including display_name, is_active, etc.
```

#### Step 7: Commit Final State
```bash
git add -A
git commit -m "fix: Achieve true single squashed migration

- Removed redundant 002_modern_complete_fixed migration
- 001_modern_complete_schema now contains complete schema
- Database rebuilt with single migration as intended
- Fixes #15: Database migration schema sync with proper squashing"
```

---

## 📊 VALIDATION CHECKLIST

### Pre-Squash Status
- [ ] Alembic shows TWO migrations (001 and 002)
- [ ] Database at revision 001_modern_complete
- [ ] Annotation sources table has all fields

### Post-Squash Status
- [ ] Alembic shows ONE migration (001_modern_complete only)
- [ ] Database at revision 001_modern_complete (head)
- [ ] No 002_modern_complete_fixed file exists
- [ ] Annotation sources table still has all fields
- [ ] API endpoints functional
- [ ] 8 annotation sources initialized

---

## 🚨 IMPORTANT NOTES

### Why This Matters
1. **Clean history**: Future developers see one comprehensive migration
2. **No confusion**: No redundant migrations to puzzle over
3. **Proper squashing**: Achieves the original goal from issue #15
4. **Maintainability**: Easier to understand and manage

### What We're NOT Doing
- NOT modifying 001 content (it's already complete)
- NOT preserving data (will reinitialize from sources)
- NOT keeping migration 002 (it's redundant)

### Rollback Plan
If issues arise:
```bash
# Restore from backup
git checkout HEAD~1
make db-restore-latest
```

---

## 📈 EXPECTED OUTCOMES

### Before
```
Migrations:
├── 001_modern_complete_schema.py (has all fields)
└── 002_modern_complete_fixed.py (redundant - adds fields already in 001)

Database: Applied both migrations
```

### After
```
Migrations:
└── 001_modern_complete_schema.py (single, complete migration)

Database: Clean application of single migration
```

---

## ⏱️ TIME ESTIMATE

- **Total time**: ~10 minutes
- **Downtime**: ~5 minutes (database rebuild)
- **Risk level**: LOW (clean rebuild, tested approach)

---

## 🎯 SUCCESS CRITERIA

1. ✅ Only ONE migration file exists
2. ✅ Database shows single migration in history
3. ✅ All AnnotationSource fields present
4. ✅ API endpoints functional
5. ✅ Issue #15 can be closed

---

**Status**: READY FOR EXECUTION
**Confidence**: HIGH - 001 already has everything needed
**Impact**: Achieves proper migration squashing as intended