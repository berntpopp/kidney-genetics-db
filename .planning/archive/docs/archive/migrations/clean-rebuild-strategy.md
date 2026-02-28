# Clean Database Rebuild Strategy
## Date: 2025-09-26
## Purpose: Complete Schema Consolidation Without Data Preservation

## Overview
This document outlines the strategy for rebuilding the Kidney Genetics Database with a consolidated migration schema. Since data will be rebuilt from sources, we can perform a clean migration without complex transformation logic.

---

## Pre-Execution Checklist

### ✅ Completed
- [x] Removed duplicate migration file (002_modern_complete_fixed.py)
- [x] Removed PostgreSQL Identity columns (unnecessary complexity)
- [x] Updated migration to use BIGINT everywhere (consistency)
- [x] Documented UUID vs BIGINT decision (BIGINT wins)

### ⚠️ Required Before Execution
- [ ] Ensure all data sources are accessible
- [ ] Verify pipeline rebuild scripts are ready
- [ ] Test migration on local copy
- [ ] Schedule maintenance window (if production)

---

## Execution Strategy

### Step 1: Backup Current State (Reference Only)
```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cd backups/$(date +%Y%m%d_%H%M%S)

# Export current schema for reference
pg_dump -U postgres -d kidney_genetics_db --schema-only > old_schema.sql

# Export current data counts for validation
psql -U postgres -d kidney_genetics_db -c "
SELECT 'genes' as table_name, COUNT(*) as count FROM genes
UNION ALL
SELECT 'gene_annotations', COUNT(*) FROM gene_annotations
UNION ALL
SELECT 'gene_evidence', COUNT(*) FROM gene_evidence
" > old_counts.txt

# Note current migration state
echo "Old migration: fix_gene_norm_log" > migration_state.txt
```

### Step 2: Clean Database Recreation
```bash
# Stop all services
make hybrid-down

# Drop old database completely
docker exec kidney_genetics_postgres psql -U postgres -c "DROP DATABASE IF EXISTS kidney_genetics_db;"

# Create fresh database
docker exec kidney_genetics_postgres psql -U postgres -c "CREATE DATABASE kidney_genetics_db;"

# Start services
make hybrid-up
```

### Step 3: Apply Consolidated Migration
```bash
# Ensure only consolidated migration exists
cd backend/alembic/versions/
ls -la  # Should only show 001_modern_complete_schema.py

# Archive old migrations (already done)
# They're in archived_20250925_081938/

# Apply new migration
cd ../..
uv run alembic upgrade head

# Verify migration
uv run alembic current
# Should output: 001_modern_complete (head)
```

### Step 4: Rebuild Data From Sources
```bash
# Run complete pipeline rebuild
cd backend

# Step 4.1: Import base genes from HGNC
uv run python -m app.pipeline.sources.hgnc.import_genes

# Step 4.2: Run annotation pipeline for all sources
uv run python -m app.pipeline.run_all_sources

# Step 4.3: Aggregate evidence
uv run python -m app.pipeline.aggregate_evidence

# Step 4.4: Refresh materialized views
uv run python -c "
from app.db.views import refresh_all_views
from app.core.database import SessionLocal
db = SessionLocal()
refresh_all_views(db)
db.close()
"
```

### Step 5: Validation
```bash
# Check record counts
psql -U postgres -d kidney_genetics_db -c "
SELECT 'genes' as table_name, COUNT(*) as count FROM genes
UNION ALL
SELECT 'gene_annotations', COUNT(*) FROM gene_annotations
UNION ALL
SELECT 'gene_evidence', COUNT(*) FROM gene_evidence
"

# Test API endpoints
curl http://localhost:8000/api/v1/genes?page[number]=1
curl http://localhost:8000/api/v1/genes/HGNC:5/annotations

# Verify all tables have BIGINT primary keys
psql -U postgres -d kidney_genetics_db -c "
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE column_name = 'id'
    AND table_schema = 'public'
ORDER BY table_name;
"
# All should show 'bigint'
```

### Step 6: Update Models (Post-Migration)
```bash
# After successful migration, update all models to use BigInteger
# This ensures consistency between database and SQLAlchemy models

# Run the model update script
uv run python scripts/update_models_to_bigint.py

# Or manually update each model file:
# Change: id = Column(Integer, primary_key=True)
# To:     id = Column(BigInteger, primary_key=True)
```

---

## Rollback Strategy (If Needed)

### Quick Rollback
```bash
# If something goes wrong, restore old database
docker exec kidney_genetics_postgres psql -U postgres -c "DROP DATABASE IF EXISTS kidney_genetics_db;"
docker exec kidney_genetics_postgres psql -U postgres -c "CREATE DATABASE kidney_genetics_db;"

# Restore old migrations
cp backend/alembic/versions/archived_20250925_081938/*.py backend/alembic/versions/

# Remove consolidated migration
rm backend/alembic/versions/001_modern_complete_schema.py

# Apply old migrations in sequence
uv run alembic upgrade head

# Rebuild data using old pipeline
```

---

## Benefits of Clean Rebuild

### ✅ Advantages
1. **No Complex Migration Logic**: No need to transform existing data
2. **Clean Schema**: Start fresh with modern best practices
3. **Consistent Types**: BIGINT everywhere, no mismatches
4. **No Legacy Issues**: Eliminates all schema drift
5. **Faster Execution**: Drop/create faster than complex migrations
6. **Guaranteed Success**: No partial migration states

### ⚠️ Considerations
1. **Downtime Required**: ~30-60 minutes for full rebuild
2. **Source Availability**: All data sources must be accessible
3. **Pipeline Ready**: Rebuild scripts must be tested
4. **No History**: Old data variations lost (acceptable)

---

## Timeline Estimate

| Step | Duration | Notes |
|------|----------|-------|
| Backup | 2 min | Schema only, no data |
| Drop/Create DB | 1 min | Clean slate |
| Apply Migration | 1 min | Single consolidated file |
| Import Genes | 5 min | ~30K genes from HGNC |
| Run Annotations | 20-30 min | All sources in parallel |
| Aggregate Evidence | 5 min | Compute scores |
| Refresh Views | 2 min | Materialized views |
| Validation | 5 min | API and count checks |
| **Total** | **~45 minutes** | With buffer |

---

## Success Criteria

- [ ] Database has only one migration: 001_modern_complete
- [ ] All tables use BIGINT for primary keys
- [ ] ~4,800+ genes imported successfully
- [ ] Annotations from all sources present
- [ ] API endpoints return data correctly
- [ ] No foreign key constraint violations
- [ ] Views refresh without errors
- [ ] Frontend displays genes correctly

---

## Post-Migration Tasks

1. **Update Documentation**
   - Update README with new schema
   - Document BIGINT decision
   - Remove references to old migrations

2. **Clean Repository**
   - Remove archived migrations after 30 days
   - Clean up migration documentation

3. **Monitor Performance**
   - Check query performance with BIGINT
   - Monitor index sizes
   - Verify cache hit ratios

---

## Command Summary (Copy-Paste Ready)

```bash
# Complete rebuild sequence
make hybrid-down
docker exec kidney_genetics_postgres psql -U postgres -c "DROP DATABASE IF EXISTS kidney_genetics_db; CREATE DATABASE kidney_genetics_db;"
make hybrid-up
cd backend && uv run alembic upgrade head
uv run python -m app.pipeline.rebuild_all  # This script should orchestrate all imports
```

---

**Status**: Ready for Execution
**Risk Level**: Low (with clean rebuild)
**Estimated Downtime**: 45 minutes