# Migration Squashing Plan
## Database Schema Consolidation Strategy

### Phase 1: Preparation (CRITICAL - NO DATA LOSS)
```bash
# 1.1 Full database backup
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db > backup_$(date +%Y%m%d_%H%M%S).sql

# 1.2 Export current schema structure
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --schema-only > schema_current.sql

# 1.3 Export current data
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db --data-only > data_current.sql

# 1.4 Document current migration state
uv run alembic current > migration_state.txt
```

### Phase 2: View Management
```python
# Views to preserve (from app/db/views.py):
- evidence_summary_view
- combined_evidence_scores
- evidence_source_counts
- evidence_normalized_scores
- evidence_count_percentiles
- evidence_classification_weights
- gene_scores
- string_ppi_percentiles
```

### Phase 3: Create Squashed Migration
```python
# New migration: backend/alembic/versions/000_squashed_complete_schema.py
"""
Squashed complete schema - consolidation of all migrations
Includes:
- All tables with correct column types
- All indexes and constraints
- All views via ReplaceableObject pattern
- Proper foreign keys
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.views import ALL_VIEWS

def upgrade():
    # 1. Create all tables in dependency order

    # Core tables
    op.create_table('genes', ...)
    op.create_table('users', ...)

    # Dependent tables
    op.create_table('gene_annotations', ...)
    op.create_table('gene_curations', ...)
    op.create_table('gene_evidence', ...)

    # Support tables
    op.create_table('cache_entries', ...)
    op.create_table('system_logs', ...)
    op.create_table('static_sources', ...)
    op.create_table('static_source_audit', ...)
    op.create_table('static_evidence_uploads', ...)

    # Staging tables
    op.create_table('gene_normalization_staging', ...)
    op.create_table('gene_normalization_log', ...)

    # Progress tracking
    op.create_table('data_source_progress', ...)
    op.create_table('annotation_sources', ...)
    op.create_table('annotation_history', ...)
    op.create_table('pipeline_runs', ...)

    # 2. Create all indexes
    op.create_index(...)

    # 3. Create all views using ReplaceableObject
    for view in ALL_VIEWS:
        op.create_entity(view)
```

### Phase 4: Migration Execution Strategy

#### Option A: Clean Migration (RECOMMENDED for non-production)
```bash
# 1. Stop services
make hybrid-down

# 2. Backup everything
make db-backup-full  # Create this command

# 3. Reset database completely
make db-reset

# 4. Apply new squashed migration
uv run alembic upgrade head

# 5. Restore data
docker exec -i kidney-genetics-db_postgres_1 psql -U postgres kidney_genetics_db < data_current.sql

# 6. Verify views
uv run python -c "from app.db.views import refresh_all_views; refresh_all_views()"

# 7. Start services
make hybrid-up
```

#### Option B: In-Place Migration (for production)
```bash
# 1. Create backup point
docker exec kidney-genetics-db_postgres_1 pg_dump -U postgres kidney_genetics_db > pre_squash_backup.sql

# 2. Clear alembic_version table
uv run python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.begin() as conn:
    conn.execute(text('TRUNCATE alembic_version'))
    conn.execute(text(\"INSERT INTO alembic_version VALUES ('000_squashed_complete')\"))
"

# 3. Verify schema matches
uv run alembic check
```

### Phase 5: Validation Checklist
- [ ] All 571+ genes present
- [ ] All annotations intact
- [ ] Views functioning (test each view)
- [ ] API endpoints working
- [ ] Admin panel functional
- [ ] WebSocket connections stable
- [ ] Cache working
- [ ] Authentication functional

### Phase 6: Cleanup
```bash
# Remove old migration files (after verification)
cd backend/alembic/versions
mkdir archived
mv *.py archived/  # Keep for reference
mv archived/000_squashed_complete_schema.py ./
```

## Key Decisions Required:
1. **Timing**: When to execute (weekend/maintenance window?)
2. **Approach**: Clean reset vs in-place migration?
3. **Rollback Plan**: Keep backup for how long?
4. **Testing**: Dev environment test first?

## Benefits of Squashing:
- Single source of truth for schema
- Faster initial deployments
- Cleaner migration history
- Easier debugging
- Reduced technical debt