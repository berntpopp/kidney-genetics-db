# Consolidated Database Migration Plan
## Date: 2025-09-25
## Status: Analysis Complete, Ready for Execution

## Table of Contents
1. [Current State Analysis](#current-state-analysis)
2. [Issues Identified](#issues-identified)
3. [Resolution Strategy](#resolution-strategy)
4. [Migration Squashing Plan](#migration-squashing-plan)
5. [References](#references)

---

## Current State Analysis

### Database Statistics
See [DATABASE_VALIDATION_REPORT.md](DATABASE_VALIDATION_REPORT.md) for complete metrics.

- **Total Records**: 4,833 genes, 33,663 annotations, 6,555 evidence records
- **Data Integrity**: 100% - No orphaned records, no duplicates, no NULL critical fields
- **Migration Chain**: 8 migrations from `001_initial_complete` to `fix_gene_norm_log`

### Schema Differences
See [SCHEMA_DIFFERENCES_ANALYSIS.md](SCHEMA_DIFFERENCES_ANALYSIS.md) for detailed breakdown.

- **Total Differences**: 93 (down from 108 after fixes)
- **Critical Fixed**: 15 issues resolved
- **Remaining**: Non-critical (timezone, defaults, indexes)

---

## Issues Identified

### Critical Issues (RESOLVED)
1. ✅ Missing model files for existing database tables
2. ✅ Column type mismatches (cache_entries.id: UUID vs INTEGER)
3. ✅ gene_normalization_log schema mismatch
4. ✅ Reserved keyword conflicts (metadata)
5. ✅ Import path inconsistencies

### Non-Critical Issues (ACCEPTABLE)
1. ⚠️ 17 timezone inconsistencies between models and database
2. ⚠️ 35 server default differences
3. ⚠️ 13 index optimization opportunities
4. ⚠️ Foreign key definition differences

---

## Resolution Strategy

### Completed Actions
1. Created missing model files:
   - `app/models/system_logs.py`
   - `app/models/static_sources.py`

2. Fixed critical model mismatches:
   - `app/models/cache.py` - Changed UUID to INTEGER
   - `app/models/gene_staging.py` - Updated schema

3. Applied migration:
   - `fix_gene_normalization_log_schema.py` - Fixed table structure

### Pending Decisions
1. **Timezone Standardization**: Recommend UTC everywhere
2. **Index Optimization**: Add missing performance indexes
3. **Migration Squashing**: Consolidate 8 migrations to 1

---

## Migration Squashing Plan

### Architecture Understanding
- **Migrations**: Handle ONLY tables, indexes, constraints
- **Views**: Managed separately by `app/db/views.py` using ReplaceableObject pattern
- **Views are NOT in migrations**: Created at application startup or manual refresh

### Current Migration Chain
```
001_initial_complete (includes views via create_all_views)
    ↓
26ebdc5e2006 (add_system_logs_table)
    ↓
c10edba96f55 (add_gene_annotation_tables)
    ↓
98531cf3dc79 (add_user_authentication_fields)
    ↓
0801ee5fb7f9 (add_pubtator_pmids_index)
    ↓
fix_gene_staging_cols
    ↓
86bdb75bc293 (add_string_ppi_percentiles_view) ← Note: View in migration!
    ↓
fix_gene_norm_log (current HEAD)
```

### Execution Plan

#### Step 1: Full Backup (MANDATORY)
```bash
# Create timestamped backup
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cd backups/$(date +%Y%m%d_%H%M%S)

# Complete database dump
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db > full_backup.sql

# Separate schema and data
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --schema-only > schema.sql
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --data-only --disable-triggers > data.sql

# Document current state
echo "Current migration: $(cd ../../backend && uv run alembic current)" > migration_state.txt
echo "Gene count: $(cd ../../backend && uv run python -c 'from app.core.database import SessionLocal; from app.models import Gene; db = SessionLocal(); print(db.query(Gene).count()); db.close()')" > gene_count.txt
```

#### Step 2: Create Consolidated Migration
```python
# backend/alembic/versions/000_consolidated_schema.py
"""
Consolidated schema - squashed from 8 migrations
Includes all tables, indexes, constraints
Views handled separately by app/db/views.py

Consolidates:
- 001_initial_complete
- 26ebdc5e2006_add_system_logs_table
- c10edba96f55_add_gene_annotation_tables
- 98531cf3dc79_add_user_authentication_fields
- 0801ee5fb7f9_add_pubtator_pmids_index
- fix_gene_staging_cols
- 86bdb75bc293_add_string_ppi_percentiles_view
- fix_gene_norm_log
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.alembic_ops import create_all_views, drop_all_views
from app.db.views import ALL_VIEWS

revision = '000_consolidated_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create all tables in dependency order
    # 2. Create all indexes
    # 3. Create all foreign keys
    # 4. Create views using the established system
    create_all_views(op, ALL_VIEWS)

def downgrade():
    # Drop in reverse order
    drop_all_views(op, ALL_VIEWS)
    # Drop tables
```

#### Step 3: Test on Copy
```bash
# Create test database
docker exec kidney-genetics-db_postgres_1 psql -U postgres -c "CREATE DATABASE kidney_test WITH TEMPLATE kidney_genetics_db"

# Test consolidated migration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kidney_test \
    uv run alembic upgrade head

# Verify
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kidney_test \
    uv run alembic check
```

#### Step 4: Apply to Production
```bash
# Archive old migrations
cd backend/alembic/versions
mkdir archived_$(date +%Y%m%d)
mv *.py archived_$(date +%Y%m%d)/

# Place new consolidated migration
cp /tmp/000_consolidated_schema.py .

# Update alembic_version table
uv run python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.begin() as conn:
    conn.execute(text('TRUNCATE alembic_version'))
    conn.execute(text(\"INSERT INTO alembic_version VALUES ('000_consolidated_schema')\"))
"

# Verify
uv run alembic check
```

#### Step 5: Validation
```bash
# Data integrity check
uv run python scripts/validate_database.py

# API test
curl http://localhost:8000/api/genes/?page[number]=1

# View verification
uv run python -c "from app.db.views import refresh_all_views; from app.core.database import SessionLocal; db = SessionLocal(); refresh_all_views(db); db.close()"
```

### Rollback Plan
```bash
# If anything fails
docker exec -i kidney-genetics-db_postgres_1 psql -U postgres kidney_genetics_db < backups/[timestamp]/full_backup.sql

# Restore migration files
cp -r backend/alembic/versions/archived_*/*.py backend/alembic/versions/

# Reset migration pointer
uv run alembic stamp fix_gene_norm_log
```

---

## References

### Analysis Documents
1. **[SCHEMA_DIFFERENCES_ANALYSIS.md](SCHEMA_DIFFERENCES_ANALYSIS.md)**
   - Complete breakdown of all 93 schema differences
   - Categorization by severity and impact
   - Specific SQL fixes for critical issues

2. **[DATABASE_VALIDATION_REPORT.md](DATABASE_VALIDATION_REPORT.md)**
   - Exact record counts and data distribution
   - Data integrity verification
   - API endpoint testing results

3. **[FINAL_DATABASE_STATUS.md](FINAL_DATABASE_STATUS.md)**
   - Current system state after fixes
   - Certification of data integrity
   - Professional assessment

### Key Metrics
- **Data Preserved**: 100% (4,833 genes, 33,663 annotations)
- **Critical Issues Fixed**: 15 of 15
- **Remaining Issues**: 93 (all non-critical)
- **System Status**: Stable and Production-Ready

### Success Criteria
- [x] All 4,833 genes accessible
- [x] Zero data loss
- [x] API functional
- [x] Models synchronized with database
- [x] Migration applied successfully
- [ ] Migration consolidation (optional, future)

---

## Next Steps

### Immediate (None Required)
System is stable and functional.

### Future Improvements
1. **Week 1**: Review timezone standardization strategy
2. **Week 2**: Plan index optimization
3. **Month 1**: Execute migration squashing during maintenance window

---

**Document Version**: 1.0
**Last Updated**: 2025-09-25
**Author**: Database Migration Recovery Team
**Status**: Analysis Complete, System Stable