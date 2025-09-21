# STRING PPI Percentile Calculation Fix

## Issue Summary
**Date:** September 21, 2025
**Severity:** Critical
**Component:** STRING PPI Annotation Pipeline

All genes were incorrectly showing 100th percentile for STRING PPI scores regardless of their actual scores. This was caused by percentiles being calculated within single-gene batches (batch-relative) rather than across all genes globally.

## Root Cause Analysis

### Primary Issues
1. **Batch-relative percentile calculation**: Percentiles were calculated within each processing batch of 1 gene, making every gene 100th percentile in its own batch
2. **Pipeline creating duplicates**: Annotation pipeline created 28,061 duplicate records instead of updating existing ones
3. **Cache serving stale data**: API was returning cached incorrect values even after database fixes

### Technical Details
- Location: `app/pipeline/sources/annotations/string_ppi.py`
- Issue introduced: During initial STRING PPI implementation
- Discovery: User reported HNF1B (score: 21.7) and PKD1 (score: 120.7) both showing 100th percentile

## Solution Implemented

### 1. Global Percentile Service
Created `app/core/percentile_service.py` with:
- Non-blocking calculation via ThreadPoolExecutor
- Multi-level caching (L1 memory, L2 database)
- Graceful degradation on failures
- Frequency limiting (5-minute minimum between recalculations)
- Comprehensive error handling

### 2. Database View for Percentiles
Added PostgreSQL view (`string_ppi_percentiles`) using PERCENT_RANK():
```sql
CREATE OR REPLACE VIEW string_ppi_percentiles AS
SELECT
    ga.gene_id,
    g.approved_symbol,
    CAST(ga.annotations->'ppi_score' AS FLOAT) as ppi_score,
    PERCENT_RANK() OVER (ORDER BY CAST(ga.annotations->'ppi_score' AS FLOAT)) AS percentile_rank
FROM gene_annotations ga
JOIN genes g ON g.id = ga.gene_id
WHERE ga.annotations ? 'ppi_score'
  AND CAST(ga.annotations->>'ppi_score' AS FLOAT) > 0
```

### 3. Modified STRING PPI Source
Updated `StringPPIAnnotationSource` to:
- Use global percentiles from view
- Return `None` instead of misleading 100th percentile when calculation fails
- Implement `recalculate_global_percentiles()` method

### 4. Background Tasks
Created `app/pipeline/tasks/percentile_updater.py` for:
- Scheduled percentile updates
- Manual recalculation triggers
- Validation of percentile distributions

## Data Cleanup Performed

### Duplicate Annotations
- **Removed:** 28,061 duplicate annotation records
- **Retained:** Most complete record per gene-source combination
- **Final count:** 4,833 unique genes with annotations

### Incorrect Percentiles
- **Updated:** 2,565 string_ppi annotations with correct global percentiles
- **Removed:** ppi_percentile fields from 3,864 non-string_ppi annotations (contamination)
- **Cache cleared:** All annotation namespace caches

## Verification Results

### Before Fix (All showing 100th percentile)
| Gene | Score | Percentile |
|------|-------|------------|
| HNF1B | 27.6 | 100th |
| PKD1 | 105.8 | 100th |
| PKD2 | 81.2 | 100th |

### After Fix (Correct global percentiles)
| Gene | Score | Percentile |
|------|-------|------------|
| HNF1B | 27.6 | 38.0th ✓ |
| PKD1 | 105.8 | 95.4th ✓ |
| PKD2 | 81.2 | 90.1th ✓ |

## Files Changed

### New Files
- `backend/app/core/percentile_service.py`
- `backend/app/pipeline/tasks/percentile_updater.py`
- `backend/alembic/versions/86bdb75bc293_add_string_ppi_percentiles_view.py`

### Modified Files
- `backend/app/pipeline/sources/annotations/string_ppi.py`
- `backend/app/api/endpoints/gene_annotations.py`
- `backend/app/pipeline/tasks/__init__.py`

## Migration Applied
```bash
alembic upgrade head
# Applied: 86bdb75bc293_add_string_ppi_percentiles_view
```

## Performance Impact
- **Percentile calculation**: <5 seconds for 2,565 genes
- **Non-blocking**: Uses ThreadPoolExecutor, doesn't block event loop
- **Cache hit rate**: 75-95% after warm-up
- **API response time**: 7-13ms (maintained)

## Testing Performed
1. Verified percentiles for test genes (HNF1B, PKD1, PKD2)
2. Validated percentile distribution (min near 0, max near 1, median ~0.5)
3. Confirmed API returns correct values after cache clear
4. Tested background task execution
5. Verified no duplicate annotations remain

## Lessons Learned
1. Always calculate percentiles globally, not within processing batches
2. Implement comprehensive validation for statistical calculations
3. Clear caches after data fixes to prevent serving stale data
4. Use database views for complex calculations when possible
5. Monitor for duplicate record creation in pipelines

## Prevention Measures
1. Added validation in `PercentileService.validate_percentiles()`
2. Implemented frequency limiting to prevent calculation storms
3. Added alerts for suspicious percentile distributions
4. Created background tasks for regular recalculation
5. Improved error handling with graceful degradation

## Related Documentation
- [Annotation Pipeline Performance](../implementation/annotation-pipeline-performance-fixes.md)
- [Cache Refactor Summary](../implementation/cache-refactor-summary.md)
- [Logging System](../development/logging-system.md)