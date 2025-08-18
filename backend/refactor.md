# Refactoring Plan for Kidney Genetics Database Backend

## Overview
This document outlines minimally invasive refactoring strategies to address code review recommendations while maintaining system stability and following DRY, KISS, and modularity principles.

## Current Implementation Status (2025-08-18)

### Summary
- ❌ **Async/Sync Consistency**: Not implemented - CLI still uses sync_wrappers.py with new event loops
- ✅ **Dependency Management**: Partially complete - uv.lock exists but no documentation/CI updates
- ⚠️ **Configuration Centralization**: Partially complete - datasource_config.py created but config.py still has duplicates
- ❌ **Stale Data Fix**: Not implemented - No database trigger for gene_curations updates
- ❌ **Hardcoded Namespaces**: Not fixed - Still hardcoded in multiple files
- ❌ **Evidence Deduplication**: Not improved - Still uses simple "keep newest" approach

### Immediate Action Items

#### Quick Wins (Can be done immediately):
1. **Fix hardcoded namespaces** (15 mins)
   - Add `get_distinct_namespaces()` method to CacheService
   - Update 3 files to use dynamic query
   
2. **Clean up config duplication** (30 mins)
   - Remove lines 36-103 from config.py
   - Update imports to use datasource_config.py
   
3. **Document uv.lock usage** (10 mins)
   - Update README with `uv sync --frozen` instructions
   - Add CI/CD configuration example

#### Medium Priority (1-2 days):
4. **Convert CLI to AsyncClick**
   - Install asyncclick
   - Update pipeline/run.py to use async functions
   - Delete sync_wrappers.py
   
5. **Add gene_curations trigger**
   - Create new Alembic migration
   - Add PostgreSQL trigger for automatic updates

#### Lower Priority (Nice to have):
6. **Improve evidence merging**
   - Create migration with intelligent JSONB merging
   - Preserve historical data in merge_history

## 1. Async/Sync Code Consistency

### Current State (UNCHANGED - Still Needs Implementation)
- Mixed async/sync code: FastAPI (async), Alembic migrations (sync), pipeline/run.py CLI (sync)
- `sync_wrappers.py` bridges async sources to sync CLI using `asyncio.new_event_loop()`
- Creates new event loops for each sync call, which is inefficient
- **Files to update**: backend/app/pipeline/run.py, backend/app/pipeline/sources/sync_wrappers.py

### Proposed Solution: Gradual Async Migration
**Phase 1: Upgrade CLI to AsyncClick (Minimal Change)**
```python
# backend/app/pipeline/run.py
import asyncclick as click  # Drop-in replacement for click
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db

@click.group()
async def cli():
    """Kidney Genetics Pipeline CLI"""
    pass

@cli.command()
@click.option("--source", ...)
async def update(source: str):
    """Update gene data from external sources"""
    async with get_async_db() as db:
        # Direct async calls, no wrappers needed
        if source in ["all", "panelapp"]:
            source = PanelAppUnifiedSource(db_session=db)
            stats = await source.update_data(db)
```

**Benefits:**
- Eliminates `sync_wrappers.py` entirely
- Uses native async/await throughout
- AsyncClick is a drop-in replacement for Click (minimal code changes)
- Alembic migrations remain sync (they're run rarely and don't need async)

**Implementation Steps:**
1. Install `asyncclick` (drop-in replacement for click)
2. Convert CLI commands to async functions
3. Remove `sync_wrappers.py` and `run_async` helper
4. Update imports in `pipeline/run.py`

## 2. Dependency Management

### Current State (PARTIALLY COMPLETE)
- `pyproject.toml` has loose version constraints ✅
- `uv.lock` file exists (good!) ✅
- Risk of non-deterministic builds in CI/CD ⚠️
- **What's done**: uv.lock file exists and is maintained
- **Still needed**: Documentation updates, CI/CD configuration for --frozen flag

### Proposed Solution: Leverage Existing uv.lock
**No code changes needed - just documentation and CI/CD updates:**

1. **Update README/docs:**
```markdown
## Installation
# For production/deployment (uses lock file):
uv sync --frozen

# For development (allows updates):
uv sync
```

2. **Update CI/CD pipelines:**
```yaml
# .github/workflows/test.yml or similar
- name: Install dependencies
  run: uv sync --frozen  # Ensures exact versions from lock file
```

3. **Add pre-commit hook (optional):**
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-lock-file
      name: Ensure uv.lock is updated
      entry: uv lock --check
      language: system
      files: pyproject.toml
```

**Benefits:**
- Zero code changes required
- Leverages existing `uv.lock` file
- Ensures reproducible builds
- Maintains flexibility for development

## 3. Configuration Centralization

### Current State (PARTIALLY COMPLETE)
- Core settings in `app/core/config.py` ✅
- Data source settings split between `config.py` and `datasource_config.py` ⚠️
- Some API URLs defined in both places ⚠️
- **What's done**: datasource_config.py created with centralized configs
- **Still needed**: Remove duplicate settings from config.py (lines 36-103)

### Proposed Solution: Complete Migration to datasource_config.py
**Move remaining source-specific settings from config.py:**

```python
# backend/app/core/datasource_config.py
# Add to existing DATA_SOURCE_CONFIG dict:

DATA_SOURCE_CONFIG = {
    "HGNC": {  # New entry
        "display_name": "HGNC",
        "description": "HUGO Gene Nomenclature Committee",
        "api_url": "http://rest.genenames.org",
        "cache_ttl": 86400,  # 24 hours
    },
    # Update existing entries to include all URLs
    "PanelApp": {
        # ... existing config ...
        "uk_api_url": "https://panelapp.genomicsengland.co.uk/api/v1",  # Already here
        "au_api_url": "https://panelapp-aus.org/api/v1",  # Already here
    },
    # Continue for other sources...
}
```

```python
# backend/app/core/config.py
# Remove duplicate definitions, keep only core app settings:
class Settings(BaseSettings):
    # Keep: Application, Database, Security, CORS settings
    # Remove: All PANELAPP_*, HPO_*, PUBTATOR_*, CLINGEN_*, GENCC_* settings
    # Remove: Individual source API URLs
    
    # Keep generic cache settings:
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600
    # Remove source-specific TTLs (now in datasource_config.py)
```

**Benefits:**
- Clear separation of concerns
- Single source of truth for each data source
- Easy to add new sources
- Backwards compatible (update imports gradually)

## 4. Potential Bugs & Anti-Patterns

### 4.1 Stale Data in gene_curations

### Current State (NOT IMPLEMENTED)
- `gene_curations` updated via separate aggregation step ❌
- Potential for stale data between evidence updates and curation updates ❌
- **Status**: No database trigger implemented
- **Files to create**: New migration file in backend/alembic/versions/

### Proposed Solution: Database Trigger for Real-time Updates
```sql
-- backend/alembic/versions/XXX_add_curation_update_trigger.py
def upgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION update_gene_curation()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Update or insert curation when evidence changes
            INSERT INTO gene_curations (gene_id, evidence_summary, updated_at)
            SELECT 
                COALESCE(NEW.gene_id, OLD.gene_id),
                jsonb_build_object(
                    'sources', array_agg(DISTINCT source_name),
                    'last_evidence_date', max(evidence_date)
                ),
                NOW()
            FROM gene_evidence
            WHERE gene_id = COALESCE(NEW.gene_id, OLD.gene_id)
            ON CONFLICT (gene_id) 
            DO UPDATE SET 
                evidence_summary = EXCLUDED.evidence_summary,
                updated_at = EXCLUDED.updated_at;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_curation_on_evidence_change
        AFTER INSERT OR UPDATE OR DELETE ON gene_evidence
        FOR EACH ROW EXECUTE FUNCTION update_gene_curation();
    """)
```

**Benefits:**
- Curations always in sync with evidence
- No separate aggregation step needed
- Leverages PostgreSQL's power
- Zero application code changes

### 4.2 Hardcoded Namespace List

### Current State (NOT FIXED)
- `/health` endpoint has hardcoded namespace list ❌
- Will become outdated when new sources added ❌
- **Files with hardcoded namespaces**:
  - backend/app/api/endpoints/cache.py:237
  - backend/app/core/monitoring.py:78, 203
- **Status**: Still hardcoded, dynamic query not implemented

### Proposed Solution: Dynamic Namespace Query
```python
# backend/app/core/cache_service.py
class CacheService:
    # Add new method:
    async def get_distinct_namespaces(self) -> list[str]:
        """Get all distinct cache namespaces from database."""
        query = select(CacheEntry.namespace).distinct()
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]

# backend/app/api/endpoints/cache.py
@router.get("/health", response_model=CacheHealthResponse)
async def get_cache_health(db: AsyncSession = Depends(get_db)) -> CacheHealthResponse:
    # ... existing code ...
    
    # Replace hardcoded list:
    # namespaces = ["hgnc", "pubtator", "gencc", "panelapp", "hpo", "clingen", "http", "files"]
    namespaces = await cache_service.get_distinct_namespaces()
    
    # ... rest of function ...
```

**Benefits:**
- Automatically includes new namespaces
- Single line change in endpoint
- Reusable method for other endpoints

### 4.3 Evidence Deduplication Logic

### Current State (NOT IMPROVED)
- Migration `1e0dd188d993` keeps most recent evidence when merging duplicates ❌
- Could lose valuable data from older, higher-quality sources ❌
- **Current implementation**: Simple DELETE keeping newest (line 46 in migration)
- **Status**: Intelligent merging not implemented

### Proposed Solution: Intelligent Evidence Merging
```python
# backend/alembic/versions/XXX_improve_evidence_merge_logic.py
def upgrade():
    op.execute("""
        -- Create function to merge evidence data intelligently
        CREATE OR REPLACE FUNCTION merge_evidence_jsonb(existing jsonb, new_data jsonb)
        RETURNS jsonb AS $$
        BEGIN
            -- Merge JSONB objects, keeping non-null values
            -- Prioritize non-empty arrays and objects
            RETURN existing || new_data || jsonb_build_object(
                'merge_history', COALESCE(existing->'merge_history', '[]'::jsonb) || 
                    jsonb_build_array(jsonb_build_object(
                        'merged_at', NOW(),
                        'source', new_data->'source'
                    ))
            );
        END;
        $$ LANGUAGE plpgsql;
        
        -- Update existing duplicates with merged data
        UPDATE gene_evidence ge1
        SET evidence_data = (
            SELECT merge_evidence_jsonb(ge1.evidence_data, 
                   jsonb_agg(ge2.evidence_data))
            FROM gene_evidence ge2
            WHERE ge2.gene_id = ge1.gene_id 
              AND ge2.source_name = ge1.source_name
              AND ge2.id != ge1.id
        )
        WHERE EXISTS (
            SELECT 1 FROM gene_evidence ge3
            WHERE ge3.gene_id = ge1.gene_id 
              AND ge3.source_name = ge1.source_name
              AND ge3.id != ge1.id
        );
    """)
```

**Benefits:**
- Preserves all evidence data
- Creates audit trail of merges
- More sophisticated than simple "keep newest"
- Can be customized per source if needed

## Implementation Priority

### Phase 1: Quick Wins (1-2 days)
1. **Fix hardcoded namespaces** - Single method addition
2. **Document uv.lock usage** - README update only
3. **Update CI/CD for frozen installs** - Config file change

### Phase 2: Configuration Cleanup (2-3 days)
1. **Centralize data source configs** - Move settings, update imports
2. **Add curation update trigger** - Single migration file

### Phase 3: Async Migration (3-5 days)
1. **Convert CLI to AsyncClick** - Replace click, update functions
2. **Remove sync_wrappers.py** - Delete file, update imports

### Phase 4: Data Quality (2-3 days)
1. **Improve evidence merge logic** - Migration with intelligent merging

## Testing Strategy

### For Each Change:
1. **Unit Tests**: Ensure existing tests pass
2. **Integration Tests**: Test data pipeline end-to-end
3. **Performance Tests**: Verify no degradation
4. **Rollback Plan**: Each change should be reversible

### Specific Test Cases:
- **Async CLI**: Compare output with current sync version
- **Dynamic namespaces**: Add new namespace, verify it appears
- **Evidence merging**: Test with duplicate data scenarios
- **Trigger updates**: Verify curations update on evidence change

## Risk Mitigation

1. **Backwards Compatibility**: All changes maintain existing APIs
2. **Gradual Rollout**: Implement in phases, not all at once
3. **Feature Flags**: Consider flags for major changes (async CLI)
4. **Monitoring**: Add metrics for cache hits, trigger execution time
5. **Documentation**: Update all docs with each change

## Conclusion

This refactoring plan addresses all identified issues while:
- Minimizing code changes
- Maintaining system stability
- Following KISS and DRY principles
- Providing clear rollback paths
- Improving long-term maintainability

The changes are ordered by impact and complexity, allowing for incremental implementation and testing.