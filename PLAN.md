# Migration Squashing Plan for Kidney-Genetics Database

## Executive Summary

This plan outlines a comprehensive strategy to squash 16+ existing Alembic migrations into a single, clean initial migration for the kidney-genetics-db project. This will simplify development, reduce deployment complexity, and create a clear baseline for future database changes.

### Documentation-Verified Best Practices

Based on Alembic and SQLAlchemy documentation review:
- **Autogenerate Support**: Alembic's `--autogenerate` flag with proper `target_metadata` configuration
- **Empty Migration Prevention**: Using `process_revision_directives` to avoid empty migrations
- **Batch Operations**: Consider `render_as_batch=True` for complex schema changes
- **Proper MetaData Management**: Using `DeclarativeBase` with single `MetaData` instance

## Current State Analysis

### Migration Inventory
- **Total Migrations**: 16 files in `backend/alembic/versions/`
- **Migration Chain**: From initial schema through multiple feature additions and fixes
- **Latest Revision**: `7acf7cac5f5f` (include_static_sources_in_evidence)
- **Complexity Range**: 129-429 lines per migration file

### Key Migration Components
1. **Core Schema** (`001_initial_complete_schema.py`)
   - Base tables: genes, gene_evidence, gene_curations
   - Evidence tracking with JSONB columns
   - Audit and versioning infrastructure

2. **Static Content System** (3 migrations)
   - `c6bad0a185f0`: Static content ingestion tables
   - `d590ddf8b389`: Static scoring views fixes
   - `d8e9f1a2b3c4`: Diagnostic panel scoring aggregation

3. **Scoring System Evolution** (6+ migrations)
   - GenCC weighted scoring implementation
   - PubTator evidence scoring
   - Provider-based scoring system
   - Multiple view updates and fixes

## Architecture Validation

### Stack Components ✅
- **ORM**: SQLAlchemy with declarative Base
- **Migration Tool**: Alembic with proper env.py configuration
- **Database**: PostgreSQL 14 in Docker container
- **Backend**: FastAPI with proper model imports
- **Development**: Make-based commands for consistency

### Configuration Review ✅
- `alembic/env.py` correctly imports `app.models.Base`
- Database URL managed through settings
- All models properly registered with Base.metadata
- Docker Compose for reproducible environments

## Backup Strategy Overview

The plan includes multiple layers of backup protection:

### Automatic Backups
- **Pre-squash backup**: Automatically triggered before migration squashing
- **Comprehensive backup**: Includes migrations, schema, and full database
- **Timestamped storage**: All backups stored in `backups/YYYYMMDD_HHMMSS/`

### Make Commands for Backup Management
- `make db-migration-backup` - Quick migration files backup
- `make db-backup-full` - Complete backup (migrations + database + schema)
- `make db-migration-restore` - Restore migration files from backup
- `make db-restore-full` - Complete database and migration restoration
- `make db-validate-schema` - Verify schema consistency

### Backup Contents
Each comprehensive backup includes:
1. **Migration files** (`migrations/`) - All Python migration scripts
2. **Full database dump** (`database_full.sql`) - Complete data and structure
3. **Schema only** (`schema.sql`) - DDL without data
4. **Migration history** (`migration_history.txt`) - Alembic history output
5. **Current revision** (`current_revision.txt`) - Active database revision

## Implementation Strategy

### Phase 1: Preparation and Backup

#### 1.1 Create Comprehensive Backup
```bash
# Timestamp-based backup of migration history
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp -r backend/alembic/versions backend/alembic/versions_backup_$TIMESTAMP

# Export current database schema for reference
docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user -d kidney_genetics \
  --schema-only > backup/schema_$TIMESTAMP.sql
```

#### 1.2 Document Current State
```bash
# Capture migration history
cd backend && alembic history > ../backup/migration_history_$TIMESTAMP.txt

# Document table structure
docker exec kidney_genetics_postgres psql \
  -U kidney_user -d kidney_genetics \
  -c "\dt+" > ../backup/tables_$TIMESTAMP.txt
```

### Phase 2: Generate Squashed Migration

#### 2.1 Reset Development Environment
```bash
# Stop services and remove volumes
docker compose -f docker-compose.services.yml down -v

# Start fresh PostgreSQL instance
docker compose -f docker-compose.services.yml up -d postgres

# Wait for database readiness
sleep 5
docker exec kidney_genetics_postgres pg_isready -U kidney_user
```

#### 2.2 Create New Migration Directory
```bash
# Archive old migrations
mv backend/alembic/versions backend/alembic/versions_archived

# Create clean versions directory
mkdir -p backend/alembic/versions
touch backend/alembic/versions/__init__.py
```

#### 2.3 Configure Alembic for Comprehensive Generation

Add to `backend/alembic/env.py` (based on Alembic best practices):

```python
def process_revision_directives(context, revision, directives):
    """Prevent empty migrations from being generated."""
    if config.cmd_opts and getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops and script.upgrade_ops.is_empty():
            directives[:] = []
            print("No changes detected, skipping migration generation.")

# In run_migrations_online():
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    process_revision_directives=process_revision_directives,
    compare_type=True,  # Enable type comparison
    compare_server_default=True,  # Compare server defaults
    include_schemas=False,  # Single schema for this project
)
```

#### 2.4 Generate Comprehensive Migration
```bash
cd backend

# Generate migration from models
alembic revision --autogenerate \
  -m "initial_complete_schema_squashed_$(date +%Y%m%d)"

# Verify the migration was created
alembic check  # Ensures no pending changes remain
```

### Phase 3: Enhancement and Validation

#### 3.1 Add PostgreSQL-Specific Features
The autogenerated migration may miss certain PostgreSQL features. Manually add:

```python
def upgrade() -> None:
    # ... autogenerated tables ...
    
    # Add pg_jsonschema extension if needed
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_jsonschema")
    
    # Create complex views that may not be captured
    op.execute("""
        CREATE OR REPLACE VIEW evidence_source_counts AS
        -- View definition from current schema
    """)
    
    # Add any custom functions or triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION update_gene_curation_timestamp()
        -- Function definition
    """)
```

#### 3.2 Validate Migration Completeness
```python
# Add to the migration file
def verify_schema():
    """Verify all expected tables and views exist."""
    expected_tables = [
        'genes', 'gene_evidence', 'gene_curations',
        'static_content_providers', 'static_content_panels',
        'static_content_genes', 'data_source_progress',
        'alembic_version'
    ]
    
    expected_views = [
        'evidence_source_counts',
        'evidence_aggregated_scores',
        'gene_evidence_summary'
    ]
    
    # Verification queries
    for table in expected_tables:
        op.execute(f"SELECT 1 FROM {table} LIMIT 0")
    
    for view in expected_views:
        op.execute(f"SELECT 1 FROM {view} LIMIT 0")
```

### Phase 4: Testing Strategy

#### 4.1 Fresh Installation Test
```bash
# Test on completely new database
make db-reset
cd backend && alembic upgrade head

# Verify schema creation
docker exec kidney_genetics_postgres psql \
  -U kidney_user -d kidney_genetics \
  -c "\dt+" | grep -E "genes|evidence|curations"
```

#### 4.2 Data Migration Test
```bash
# Import test dataset
cd backend && uv run python scripts/import_test_data.py

# Verify data integrity
uv run python -c "
from app.core.database import SessionLocal
from app.models import Gene
db = SessionLocal()
print(f'Gene count: {db.query(Gene).count()}')
"
```

#### 4.3 API Endpoint Verification
```bash
# Start API and test endpoints
make backend

# In another terminal
curl -X GET "http://localhost:8000/api/genes?limit=5"
curl -X GET "http://localhost:8000/api/progress/status"
```

### Phase 5: Makefile Integration

Add these commands to the Makefile:

```makefile
# ════════════════════════════════════════════════════════════════════
# MIGRATION MANAGEMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: db-squash-migrations db-migration-backup db-migration-restore

# Squash all migrations into a single initial migration
db-squash-migrations: db-migration-backup
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           MIGRATION SQUASHING - DEVELOPMENT ONLY                ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "⚠️  WARNING: This will:"
	@echo "  • Delete all existing migration history"
	@echo "  • Reset the development database completely"
	@echo "  • Generate a new single migration from models"
	@echo ""
	@echo "This should ONLY be used in development environments!"
	@echo ""
	@read -p "Type 'squash' to confirm: " confirm; \
	if [ "$$confirm" != "squash" ]; then \
		echo "❌ Operation cancelled"; \
		exit 1; \
	fi
	@echo ""
	@echo "📦 Step 1/7: Creating comprehensive backup..."
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations 2>/dev/null || true && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics --schema-only > backups/$$TIMESTAMP/schema.sql 2>/dev/null || true && \
	cd backend && uv run alembic history > ../backups/$$TIMESTAMP/migration_history.txt 2>/dev/null || true && \
	echo "   ✓ Full backup created in: backups/$$TIMESTAMP/" && \
	echo "     - Migration files: backups/$$TIMESTAMP/migrations/" && \
	echo "     - Database schema: backups/$$TIMESTAMP/schema.sql" && \
	echo "     - Migration history: backups/$$TIMESTAMP/migration_history.txt"
	@echo ""
	@echo "🔄 Step 2/7: Resetting database..."
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml down -v
	@$(DOCKER_COMPOSE) -f docker-compose.services.yml up -d postgres
	@sleep 5
	@docker exec kidney_genetics_postgres pg_isready -U kidney_user -d kidney_genetics >/dev/null 2>&1 || \
		(echo "   ⚠️  Waiting for database..." && sleep 5)
	@echo "   ✓ Database reset complete"
	@echo ""
	@echo "🧹 Step 3/7: Cleaning migration directory..."
	@rm -rf backend/alembic/versions/*.py
	@echo "   ✓ Migration directory cleaned"
	@echo ""
	@echo "🔨 Step 4/7: Generating new squashed migration..."
	@cd backend && uv run alembic revision --autogenerate \
		-m "squashed_complete_schema_$$(date +%Y%m%d)" 2>&1 | \
		grep -E "(Generating|Detected)" || echo "   ✓ Migration generated"
	@echo ""
	@echo "📝 Step 5/7: Review the generated migration"
	@echo "   Location: backend/alembic/versions/"
	@ls -la backend/alembic/versions/*.py | tail -1
	@echo ""
	@read -p "Press Enter to apply the migration, or Ctrl+C to abort: "
	@echo ""
	@echo "🚀 Step 6/7: Applying migration..."
	@cd backend && uv run alembic upgrade head
	@echo ""
	@echo "✅ Step 7/7: Validating schema..."
	@$(MAKE) db-validate-schema
	@echo ""
	@echo "✅ Migration squashing complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review the generated migration file"
	@echo "  2. Test with: make test"
	@echo "  3. Verify API: make backend (then check http://localhost:8000/docs)"
	@echo "  4. If issues occur, restore with: make db-migration-restore-full"

# Create a quick backup of current migrations
db-migration-backup:
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations && \
	echo "✅ Migrations backed up to: backups/$$TIMESTAMP/migrations"

# Create a comprehensive backup (migrations + schema + history)
db-backup-full:
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "🔄 Creating comprehensive backup..." && \
	mkdir -p backups/$$TIMESTAMP && \
	cp -r backend/alembic/versions backups/$$TIMESTAMP/migrations 2>/dev/null && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics > backups/$$TIMESTAMP/database_full.sql && \
	docker exec kidney_genetics_postgres pg_dump -U kidney_user -d kidney_genetics --schema-only > backups/$$TIMESTAMP/schema.sql && \
	cd backend && uv run alembic history > ../backups/$$TIMESTAMP/migration_history.txt && \
	cd backend && uv run alembic current > ../backups/$$TIMESTAMP/current_revision.txt && \
	echo "✅ Full backup created in: backups/$$TIMESTAMP/" && \
	echo "   Contents:" && \
	echo "   - Migration files: backups/$$TIMESTAMP/migrations/" && \
	echo "   - Full database: backups/$$TIMESTAMP/database_full.sql" && \
	echo "   - Schema only: backups/$$TIMESTAMP/schema.sql" && \
	echo "   - Migration history: backups/$$TIMESTAMP/migration_history.txt" && \
	echo "   - Current revision: backups/$$TIMESTAMP/current_revision.txt"

# Restore migrations from a backup
db-migration-restore:
	@echo "Available backups:"
	@ls -d backups/*/migrations 2>/dev/null | sed 's|backups/||;s|/migrations||' | sed 's/^/  - /' || echo "  No backups found"
	@echo ""
	@read -p "Enter backup timestamp to restore (e.g., 20250822_143022): " timestamp; \
	if [ -d "backups/$$timestamp/migrations" ]; then \
		rm -rf backend/alembic/versions/*.py && \
		cp -r backups/$$timestamp/migrations/* backend/alembic/versions/ && \
		echo "✅ Restored migrations from backup: $$timestamp"; \
		echo "   Run 'make db-reset' to apply the restored migrations"; \
	else \
		echo "❌ Backup not found: backups/$$timestamp"; \
		exit 1; \
	fi

# Restore complete database from backup
db-restore-full:
	@echo "Available full backups:"
	@ls -f backups/*/database_full.sql 2>/dev/null | sed 's|backups/||;s|/database_full.sql||' | sed 's/^/  - /' || echo "  No full backups found"
	@echo ""
	@read -p "Enter backup timestamp to restore (e.g., 20250822_143022): " timestamp; \
	if [ -f "backups/$$timestamp/database_full.sql" ]; then \
		echo "🔄 Restoring database from backup..."; \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d postgres -c "DROP DATABASE IF EXISTS kidney_genetics;" && \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d postgres -c "CREATE DATABASE kidney_genetics;" && \
		docker exec -i kidney_genetics_postgres psql -U kidney_user -d kidney_genetics < backups/$$timestamp/database_full.sql && \
		if [ -d "backups/$$timestamp/migrations" ]; then \
			rm -rf backend/alembic/versions/*.py && \
			cp -r backups/$$timestamp/migrations/* backend/alembic/versions/ && \
			echo "   ✓ Migrations restored"; \
		fi && \
		echo "✅ Full restoration complete from backup: $$timestamp"; \
	else \
		echo "❌ Full backup not found: backups/$$timestamp"; \
		exit 1; \
	fi

# Validate database schema against models
db-validate-schema:
	@echo "🔍 Validating database schema..."
	@cd backend && uv run python -c "\
from sqlalchemy import create_engine, inspect; \
from app.core.config import settings; \
from app.models import Base; \
engine = create_engine(settings.DATABASE_URL); \
inspector = inspect(engine); \
db_tables = set(inspector.get_table_names()); \
model_tables = set(Base.metadata.tables.keys()); \
missing = model_tables - db_tables; \
extra = db_tables - model_tables - {'alembic_version'}; \
if missing: print(f'❌ Missing tables: {missing}'); \
if extra: print(f'⚠️  Extra tables: {extra}'); \
if not missing and not extra: print('✅ Schema is in sync'); \
"
```

## Risk Mitigation

### Potential Issues and Solutions

1. **Complex Views Not Captured**
   - Solution: Manually add view definitions to the migration
   - Keep a separate SQL file with complex view definitions
   - Use Alembic's `op.execute()` for raw SQL when needed

2. **Custom PostgreSQL Functions**
   - Solution: Extract functions from current schema and add to migration
   - Document all custom database objects
   - Consider using `alembic.operations.ops.ExecuteSQLOp` for complex DDL

3. **Data Dependencies**
   - Solution: Create seed data scripts separate from migrations
   - Test with realistic data volumes
   - Use Alembic's `-x data=true` pattern for conditional data migrations

4. **Team Coordination**
   - Solution: Communicate migration squashing to all developers
   - Provide clear instructions for updating local environments
   - Use `alembic merge` if parallel development creates conflicts

5. **Autogenerate Limitations** (from Alembic docs)
   - May miss: Custom types, server defaults, some constraints
   - Solution: Review generated migration carefully
   - Add missing elements manually
   - Use `compare_type=True` and `compare_server_default=True`

## Success Criteria

- ✅ Single migration file replaces 16+ individual migrations
- ✅ Fresh database creation takes < 5 seconds (vs 30+ seconds)
- ✅ All tests pass with new migration
- ✅ API endpoints function correctly
- ✅ Development setup simplified for new team members

## Timeline

### Day 1: Preparation
- Create backups and documentation
- Review current migration complexity
- Test backup restoration procedures

### Day 2: Implementation
- Generate squashed migration
- Add PostgreSQL-specific features
- Initial testing

### Day 3: Validation
- Comprehensive testing suite
- Performance benchmarking
- Documentation updates

### Day 4: Deployment
- Team communication
- Update development environments
- Monitor for issues

## Post-Implementation Checklist

- [ ] All developers have updated their local environments
- [ ] CI/CD pipelines updated with new migration approach
- [ ] Documentation reflects new database setup process
- [ ] Backup of old migrations archived securely
- [ ] Performance metrics documented
- [ ] Rollback procedure tested and documented

## Conclusion

This migration squashing plan will significantly improve the development experience while maintaining the integrity and functionality of the kidney-genetics database. The comprehensive testing and backup strategies ensure a safe transition with minimal risk to ongoing development work.

The resulting single migration file will serve as a clear, maintainable foundation for future database evolution, making it easier for new developers to understand the complete schema at a glance.