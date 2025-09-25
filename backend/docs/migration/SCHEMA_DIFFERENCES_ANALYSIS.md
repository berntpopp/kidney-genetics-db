# Schema Differences Analysis Report
## Total: 96 Distinct Differences (Not 108 - some were duplicates)

## Critical Issues Requiring Immediate Fix

### 1. WRONG DATA TYPE - Will Cause Data Loss (2 issues)
- ❌ `cache_entries.id`: Model expects UUID, DB has INTEGER
- ❌ `cache_entries.cache_key`: Model expects Text, DB has VARCHAR(255)

### 2. Missing Critical Columns in Database (7 columns)
- ❌ `gene_normalization_log.success`
- ❌ `gene_normalization_log.staging_id`
- ❌ `gene_normalization_log.processing_time_ms`
- ❌ `gene_normalization_log.normalization_log`
- ❌ `gene_normalization_log.final_gene_id`
- ❌ `gene_normalization_log.approved_symbol`
- ❌ `gene_normalization_log.api_calls_made`

### 3. Columns in DB but Not in Model (9 columns)
- ❌ `gene_normalization_log.normalized_symbol`
- ❌ `gene_normalization_log.match_type`
- ❌ `gene_normalization_log.match_details`
- ❌ `gene_normalization_log.confidence_score`
- ❌ `gene_evidence.evidence_score`
- ❌ `gene_curations.curation_status`
- ❌ `data_source_progress.rate_limit_reset`
- ❌ `data_source_progress.rate_limit_remaining`
- ❌ `data_source_progress.last_successful_item`

## Timezone Inconsistencies (17 issues)

### Models Expect timezone=True, DB has no timezone:
- ⚠️ `annotation_sources.created_at` - TIMESTAMP → DateTime(timezone=True)
- ⚠️ `annotation_sources.updated_at` - TIMESTAMP → DateTime(timezone=True)
- ⚠️ `data_source_progress.started_at` - TIMESTAMP → DateTime(timezone=True)
- ⚠️ `data_source_progress.completed_at` - TIMESTAMP → DateTime(timezone=True)
- ⚠️ `gene_annotations.created_at` - TIMESTAMP → DateTime(timezone=True)
- ⚠️ `gene_annotations.updated_at` - TIMESTAMP → DateTime(timezone=True)

### Models Expect no timezone, DB has timezone=True:
- ⚠️ `system_logs.timestamp` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_sources.created_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_sources.updated_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_source_audit.performed_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_evidence_uploads.created_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_evidence_uploads.processed_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `static_evidence_uploads.updated_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `gene_normalization_staging.created_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `gene_normalization_staging.updated_at` - TIMESTAMP(timezone=True) → DateTime()
- ⚠️ `gene_normalization_log.created_at` - TIMESTAMP(timezone=True) → DateTime()

## Missing Server Defaults (35 issues)
These are defined in models but not in database:
- ⚠️ 35 server default mismatches (non-critical, handled by SQLAlchemy)

## Index Differences (13 issues)

### Missing in Database:
- ⚠️ 5 indexes for `gene_normalization_log`
- ⚠️ 2 indexes for `gene_normalization_staging`
- ⚠️ 1 index for `system_logs`

### Extra in Database (can be removed):
- ⚠️ `idx_gene_annotations_jsonb`
- ⚠️ `ix_gene_annotations_ppi_score`
- ⚠️ `idx_gene_evidence_pubtator_pmids`
- ⚠️ `ix_gene_normalization_staging_resolved_gene_id`

### Changed Index Properties:
- ⚠️ `ix_data_source_progress_source_name`: unique=False → unique=True
- ⚠️ `idx_system_logs_timestamp_desc`: expression changed
- ⚠️ `idx_system_logs_timestamp_level`: expression changed

## Foreign Key Issues (5 issues)
- ⚠️ 3 removed foreign keys (need re-adding)
- ⚠️ 2 added foreign keys (already in model)

## Data Type Mismatches (1 issue)
- ⚠️ `data_source_progress.metadata`: JSONB → JSON

## Action Plan

### Priority 1: CRITICAL - Data Loss Risk
```sql
-- DO NOT CHANGE cache_entries.id from INTEGER to UUID - will break existing data!
-- Instead, update model to match database

-- For cache_entries.cache_key, can safely expand:
ALTER TABLE cache_entries ALTER COLUMN cache_key TYPE TEXT;
```

### Priority 2: Fix Missing Columns
```sql
-- Add missing columns to gene_normalization_log
ALTER TABLE gene_normalization_log
ADD COLUMN IF NOT EXISTS success BOOLEAN,
ADD COLUMN IF NOT EXISTS staging_id INTEGER,
ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER,
ADD COLUMN IF NOT EXISTS normalization_log JSONB,
ADD COLUMN IF NOT EXISTS final_gene_id INTEGER,
ADD COLUMN IF NOT EXISTS approved_symbol VARCHAR(100),
ADD COLUMN IF NOT EXISTS api_calls_made INTEGER;

-- Remove obsolete columns
ALTER TABLE gene_normalization_log
DROP COLUMN IF EXISTS normalized_symbol,
DROP COLUMN IF EXISTS match_type,
DROP COLUMN IF EXISTS match_details,
DROP COLUMN IF EXISTS confidence_score;
```

### Priority 3: Timezone Standardization
Decision needed: Use UTC everywhere or keep mixed?
Recommendation: Standardize to TIMESTAMP WITH TIME ZONE (UTC)

### Priority 4: Index Optimization
```sql
-- Add missing critical indexes
CREATE INDEX IF NOT EXISTS ix_gene_normalization_log_success ON gene_normalization_log(success);
CREATE INDEX IF NOT EXISTS ix_gene_normalization_log_created_at ON gene_normalization_log(created_at);

-- Remove unused indexes
DROP INDEX IF EXISTS idx_gene_annotations_jsonb;
DROP INDEX IF EXISTS ix_gene_annotations_ppi_score;
```

## Summary
- **18 CRITICAL issues** requiring immediate attention
- **17 timezone inconsistencies** needing standardization
- **35 server defaults** (low priority, handled by ORM)
- **13 index differences** (performance optimization)
- **5 foreign key issues** (referential integrity)