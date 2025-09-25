# Syndromic Assessment Issue - Investigation Report

## Executive Summary

The syndromic assessment feature in the HPO annotation pipeline is returning default/empty values for all genes. Despite a previous fix attempt (commit 2bc69f4), the issue persists. The root cause appears to be a failure in fetching or caching HPO term descendants for syndromic indicator terms.

## Issue Description

**Current Behavior:**
All genes return the following syndromic assessment:
```json
"syndromic_assessment": {
    "is_syndromic": false,
    "category_scores": {},
    "syndromic_score": 0,
    "extra_renal_categories": [],
    "extra_renal_term_counts": {}
}
```

**Expected Behavior:**
Genes with extra-renal phenotypes should be classified as syndromic, with proper scores for growth, skeletal, neurologic, and head/neck abnormalities.

## Investigation Findings

### 1. Code Analysis

#### Current Implementation (Python)
- **Location**: `backend/app/pipeline/sources/annotations/hpo.py`
- **Method**: `_assess_syndromic_features()`
- **Configuration**: Correctly defined in `backend/app/core/datasource_config.py`:
  ```python
  "syndromic_indicators": {
      "growth": "HP:0001507",      # Growth abnormality
      "skeletal": "HP:0000924",    # Skeletal system abnormality
      "neurologic": "HP:0000707",  # Abnormality of the nervous system
      "head_neck": "HP:0000152",   # Head and neck abnormality
  }
  ```

#### Previous R Implementation
- **Location**: `analyses/C_AnnotateMergedTable/C_AnnotateMergedTable.R`
- **Logic**:
  1. Fetches all descendants of the four syndromic indicator terms
  2. Checks ALL phenotypes (not just non-kidney) against these descendants
  3. Calculates proportional scores for each category
  4. Sets syndromic threshold at 30%

### 2. Previous Fix Attempt

Commit 2bc69f4 (Sep 15, 2025) attempted to fix this by:
- Changed from checking only non-kidney phenotypes to checking ALL phenotypes
- Added per-category scoring
- Aligned with R implementation logic

**The fix appears correct in the code**, but the issue persists.

### 3. Root Cause Analysis

The most likely root causes (in order of probability):

1. **HPO Term Descendant Fetching Failure**
   - The `get_classification_term_descendants()` method may be returning empty sets
   - The HPO API endpoints for descendants might be failing or rate-limited
   - Cache might be storing empty results

2. **Caching Issue**
   - Empty results might be cached, preventing proper data fetching
   - Cache TTL (24 hours) might be preserving bad data

3. **HPO Pipeline Initialization**
   - The `HPOPipeline` instance created in the method might not be properly initialized
   - Missing HTTP client or cache service configuration

4. **API Endpoint Issues**
   - HPO API descendants endpoint (`/hp/terms/{id}/descendants`) might have changed
   - Fallback to recursive children traversal might not be working

## Debugging Evidence

### Test Script Created
Created `backend/test_syndromic_debug.py` to:
1. Test HPO API endpoints directly
2. Verify descendant fetching for syndromic terms
3. Test gene syndromic assessment with known syndromic gene (COL4A5 - Alport syndrome)

### Key Observations
- Previous commit message indicates "HPO now properly classifies genes as syndromic"
- But the issue was reported as not fixed by the user
- The fix logic looks correct but execution seems to fail

## Recommended Solution

### Immediate Fix

1. **Add Debug Logging**
   ```python
   async def get_classification_term_descendants(self, classification_type: str) -> dict[str, set[str]]:
       # Add logging to track fetching
       logger.sync_info(f"Fetching descendants for {classification_type}")

       # ... existing code ...

       # Log results
       for group_key, descendants in descendants_map.items():
           logger.sync_info(f"{group_key}: {len(descendants)} descendants fetched")

       return descendants_map
   ```

2. **Force Cache Refresh**
   ```python
   # Add parameter to force cache refresh
   async def get_classification_term_descendants(
       self, classification_type: str, force_refresh: bool = False
   ) -> dict[str, set[str]]:
       # Check cache only if not forcing refresh
       if not force_refresh and self._classification_cache_time is not None:
           # ... existing cache logic ...
   ```

3. **Verify HPO Pipeline Initialization**
   ```python
   async def get_classification_term_descendants(self, classification_type: str) -> dict[str, set[str]]:
       from app.core.hpo.pipeline import HPOPipeline
       from app.core.cache_service import get_cache_service
       from app.core.cached_http_client import CachedHttpClient

       # Ensure proper initialization
       cache_service = get_cache_service(self.session)
       http_client = CachedHttpClient(cache_service=cache_service)
       pipeline = HPOPipeline(cache_service=cache_service, http_client=http_client)
   ```

### Long-term Improvements

1. **Add Unit Tests**
   - Test descendant fetching for each syndromic term
   - Test syndromic assessment with known syndromic and non-syndromic genes
   - Test cache behavior

2. **Add Monitoring**
   - Track success rate of HPO API calls
   - Monitor cache hit/miss rates for descendant fetching
   - Alert on empty descendant sets

3. **Fallback Mechanism**
   - Store static snapshot of descendant terms as fallback
   - Use local ontology file if API fails

## Testing Plan

1. **Clear all caches**
   ```bash
   make db-clean
   ```

2. **Test individual components**
   ```python
   # Test HPO API directly
   curl https://ontology.jax.org/api/hp/terms/HP:0001507/descendants

   # Test descendant fetching
   python test_syndromic_debug.py
   ```

3. **Re-run annotation pipeline**
   ```bash
   make db-reset
   make backend
   # Run annotation update for a known syndromic gene
   ```

4. **Verify results**
   - Check database for non-zero syndromic scores
   - Test API endpoint for syndromic classification

## Conclusion

The syndromic assessment implementation appears logically correct but fails during execution, likely due to issues with fetching HPO term descendants. The recommended solution focuses on:
1. Adding comprehensive logging to identify the exact failure point
2. Ensuring proper initialization of dependencies
3. Implementing cache refresh mechanisms
4. Adding fallback strategies for API failures

The issue requires debugging at runtime to identify why descendant fetching returns empty sets despite correct configuration.

## Next Steps

1. Add debug logging to trace descendant fetching
2. Test HPO API endpoints directly
3. Force cache refresh for syndromic terms
4. Re-run annotation pipeline with monitoring
5. Verify syndromic scores are properly calculated and stored