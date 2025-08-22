# Migration Squashing Plan for Kidney-Genetics-DB

## Overview

This document provides a comprehensive plan for squashing database migrations in the Kidney-Genetics-DB project. The project currently has accumulated 15+ migration files between the main branch and feature branches, creating complexity for deployment and maintenance.

## Current Migration State Analysis

### Branch Status
- **Main Branch**: Contains 8 migrations (up to `78f29a992e5d_improve_evidence_merge_logic.py`)
- **Feature Branch** (`feature/static-content-ingestion`): Contains 15 migrations including static content ingestion features
- **Current Head**: `7acf7cac5f5f` (include_static_sources_in_evidence_scoring)

### Migration Complexity Breakdown

| File | Lines | Type | Description |
|------|-------|------|-------------|
| `001_initial_complete_schema.py` | 429 | Foundation | Initial complete database schema with all core tables and views |
| `c6bad0a185f0_add_static_content_ingestion_tables.py` | 184 | Feature | Static content ingestion tables and views |
| `7acf7cac5f5f_include_static_sources_in_evidence_.py` | 264 | Complex View | Complex view updates with static source integration |

### Key Database Components
- **Core Tables**: genes, gene_evidence, gene_curations, pipeline_runs
- **Staging Tables**: gene_normalization_staging, gene_normalization_log
- **Progress Tracking**: data_source_progress
- **Static Content**: static_sources, static_evidence_uploads, static_source_audit
- **Complex Views**: evidence_source_counts, evidence_normalized_scores, gene_scores

## Migration Squashing Strategy

### Phase 1: Preparation
1. **Create Migration Backup**
   ```bash
   # Backup current migrations
   cp -r backend/alembic/versions backend/alembic/versions_backup_$(date +%Y%m%d)
   ```

2. **Document Current Schema**
   ```bash
   # Generate current schema dump for verification
   make services-up
   pg_dump -h localhost -U kidney_user -d kidney_genetics --schema-only > current_schema.sql
   ```

3. **Test Current Migration Chain**
   ```bash
   # Fresh database test
   make db-reset
   # Verify all migrations apply cleanly
   cd backend && uv run alembic upgrade head
   ```

### Phase 2: Create Squashed Migration

#### Approach: Single Comprehensive Migration
Create one migration file that replaces all existing migrations, incorporating:

1. **Complete Schema Definition**
   - All tables from the initial schema
   - All feature additions (static content ingestion)
   - All indexes and constraints
   - All database views and functions

2. **Migration Strategy**
   ```bash
   # Step 1: Generate new migration from current models
   cd backend
   uv run alembic revision --autogenerate -m "squashed_complete_schema"
   
   # Step 2: Manual review and enhancement of generated migration
   # - Add missing views and functions
   # - Add custom indexes
   # - Add triggers and stored procedures
   ```

### Phase 3: Migration File Structure

#### New Squashed Migration Template
```python
"""Squashed complete schema with all features

Revision ID: squashed_complete
Revises: 
Create Date: 2025-08-22
"""

def upgrade() -> None:
    """Create complete database schema with all features."""
    
    # ========== CORE TABLES ==========
    create_core_tables()
    
    # ========== FEATURE TABLES ==========
    create_static_content_tables()
    create_staging_tables()
    create_progress_tables()
    
    # ========== INDEXES ==========
    create_performance_indexes()
    
    # ========== VIEWS ==========
    create_evidence_views()
    create_scoring_views()
    
    # ========== TRIGGERS & FUNCTIONS ==========
    create_triggers_and_functions()

def downgrade() -> None:
    """Drop all database objects."""
    # Complete schema teardown
```

### Phase 4: Implementation Steps

#### 4.1 Create New Migration Structure
```bash
# 1. Create new migration directory structure
mkdir -p backend/alembic/versions_new
mkdir -p backend/alembic/versions_archive

# 2. Move current migrations to archive
mv backend/alembic/versions/* backend/alembic/versions_archive/

# 3. Generate new squashed migration
cd backend
uv run alembic revision -m "complete_squashed_schema"
```

#### 4.2 Build Comprehensive Migration
The new migration should include:

1. **All Core Tables**
   ```python
   def create_core_tables():
       # genes table
       op.create_table('genes', ...)
       
       # gene_evidence table  
       op.create_table('gene_evidence', ...)
       
       # gene_curations table
       op.create_table('gene_curations', ...)
       
       # pipeline_runs table
       op.create_table('pipeline_runs', ...)
   ```

2. **Feature-Specific Tables**
   ```python
   def create_static_content_tables():
       # static_sources table
       op.create_table('static_sources', ...)
       
       # static_evidence_uploads table
       op.create_table('static_evidence_uploads', ...)
       
       # static_source_audit table
       op.create_table('static_source_audit', ...)
   ```

3. **Complex Views**
   ```python
   def create_evidence_views():
       # evidence_source_counts view
       op.execute("""CREATE VIEW evidence_source_counts AS ...""")
       
       # evidence_normalized_scores view
       op.execute("""CREATE VIEW evidence_normalized_scores AS ...""")
       
       # combined_evidence_scores view
       op.execute("""CREATE VIEW combined_evidence_scores AS ...""")
   ```

#### 4.3 Testing Strategy
1. **Fresh Database Test**
   ```bash
   # Test new squashed migration
   make db-reset
   cd backend && uv run alembic upgrade head
   ```

2. **Data Consistency Test**
   ```bash
   # Compare schema with production backup
   pg_dump -h localhost -U kidney_user -d kidney_genetics --schema-only > new_schema.sql
   diff current_schema.sql new_schema.sql
   ```

3. **Application Integration Test**
   ```bash
   # Start services and run integration tests
   make hybrid-up
   make backend &
   make test
   ```

### Phase 5: Deployment Strategy

#### 5.1 Development Environment
```bash
# Makefile additions for migration squashing
squash-migrations:
	@echo "🔄 Squashing migrations..."
	@$(MAKE) db-reset
	@cd backend && uv run alembic upgrade head
	@echo "✅ Migration squashing complete!"

test-squashed:
	@echo "🧪 Testing squashed migrations..."
	@$(MAKE) db-clean
	@cd backend && uv run alembic upgrade head
	@$(MAKE) test
	@echo "✅ Squashed migration tests passed!"
```

#### 5.2 Production Considerations
1. **Backup Strategy**
   ```bash
   # Full database backup before migration
   pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_pre_squash.sql
   ```

2. **Rollback Plan**
   ```bash
   # Keep old migration files available for emergency rollback
   # Document exact rollback procedure
   ```

#### 5.3 CI/CD Integration
```yaml
# Add to CI pipeline
- name: Test Migration Squashing
  run: |
    make services-up
    make test-squashed
    make services-down
```

## Benefits of Squashing

### 1. Simplified Deployment
- Single migration file reduces deployment complexity
- Faster fresh database initialization
- Cleaner migration history

### 2. Improved Maintenance
- Easier to understand complete schema
- Reduced migration file count (15+ → 1)
- Simplified debugging of schema issues

### 3. Performance Benefits
- Faster migration execution for fresh deployments
- Reduced alembic overhead
- Cleaner database metadata

### 4. Developer Experience
- New developers can understand schema from single file
- Reduced cognitive load when working with database
- Easier to reason about database state

## Risks and Mitigation

### Risk 1: Data Loss
**Mitigation**: Comprehensive testing with production data copies

### Risk 2: Migration Failures
**Mitigation**: Maintain rollback capability with archived migrations

### Risk 3: Schema Drift
**Mitigation**: Automated schema comparison tests

### Risk 4: Feature Branch Conflicts
**Mitigation**: Coordinate with all active feature branches

## Timeline and Milestones

### Week 1: Preparation
- [ ] Create migration backups
- [ ] Document current schema
- [ ] Set up testing infrastructure

### Week 2: Implementation
- [ ] Create squashed migration file
- [ ] Implement comprehensive schema creation
- [ ] Add all views and functions

### Week 3: Testing
- [ ] Test fresh database creation
- [ ] Test data migration scenarios
- [ ] Performance testing

### Week 4: Deployment
- [ ] Deploy to staging environment
- [ ] Production deployment
- [ ] Post-deployment monitoring

## Maintenance Commands

### New Make Targets
```makefile
# Add to Makefile
squash-check:
	@echo "🔍 Checking migration squashing readiness..."
	@cd backend && uv run alembic history
	@echo "Current migrations: $(shell ls backend/alembic/versions/*.py | wc -l)"

migrate-fresh:
	@echo "🗄️ Creating fresh database with squashed migration..."
	@$(MAKE) db-reset
	@echo "✅ Fresh database ready!"

schema-compare:
	@echo "📊 Comparing current schema with target..."
	@pg_dump -h localhost -U kidney_user -d kidney_genetics --schema-only > /tmp/current.sql
	@echo "Schema exported for comparison"
```

## Monitoring and Validation

### Post-Squash Checklist
- [ ] All tests pass with new migration
- [ ] Application starts successfully
- [ ] All database views return expected data
- [ ] Performance metrics remain stable
- [ ] No foreign key constraint violations
- [ ] All indexes are present and optimized

### Automated Validation
```python
# Add to test suite
def test_squashed_migration_completeness():
    """Verify squashed migration creates complete schema."""
    # Test all expected tables exist
    # Test all expected indexes exist
    # Test all expected views exist
    # Test all expected functions exist
```

## Conclusion

This migration squashing plan provides a comprehensive approach to consolidating the current 15+ migration files into a single, maintainable migration. The strategy balances safety through extensive testing with the benefits of simplified database management. The phased approach allows for careful validation at each step while maintaining the ability to rollback if issues are discovered.

The resulting single migration file will significantly improve developer experience, deployment reliability, and maintenance overhead while preserving all current functionality and data integrity.