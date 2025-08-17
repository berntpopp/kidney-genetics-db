# GenCC Evidence Creation Fix - Comprehensive Refactor Plan

## Problem Summary

**Issue**: GenCC processes 352 kidney-related genes successfully but creates 0 evidence records
**Root Cause**: Schema mismatch between async and sync gene normalization functions
**Impact**: GenCC source provides no evidence data despite successful gene processing

## Technical Analysis

### Schema Mismatch Details

**Working Sources (ClinGen, PanelApp)** use `normalize_gene_for_database()`:
```python
{
  "status": "normalized|requires_manual_review|error",
  "approved_symbol": str,
  "hgnc_id": str, 
  "staging_id": int | None,  # For manual review
  "error": str | None
}
```

**Broken Sources (GenCC async, HPO async)** use `normalize_genes_batch_async()`:
```python
{
  "approved_symbol": str,
  "hgnc_id": str,
  "source": "database|hgnc|not_found",  # NOT "status"!
  "original_data": dict
}
```

### Critical Code Location

**File**: `backend/app/pipeline/sources/gencc_async.py`
**Line 109**: `if result["status"] == "normalized":` 
**Problem**: Field "status" doesn't exist, should be "source"

### Missing Staging Support

The async normalization doesn't implement the staging system:
- Invalid genes should go to staging for manual review
- Only properly normalized genes should create evidence
- Current async version silently drops problematic genes

## Solution Architecture

### Phase 1: Immediate Fix (Schema Alignment)
1. **Update gencc_async.py** to handle both schema types
2. **Map source values to status logic**:
   - `source: "database"` or `source: "hgnc"` → Process as normalized
   - `source: "not_found"` → Handle as staging candidate

### Phase 2: Proper Async Staging Implementation
1. **Enhance normalize_genes_batch_async()** to return proper schema
2. **Add staging support** for genes that can't be normalized
3. **Return status field** compatible with existing pipeline logic

### Phase 3: Architecture Consistency
1. **Standardize all async sources** to use same normalization pattern
2. **Update HPO async** to use fixed normalization (same issue)
3. **Ensure staging workflow** works across all sources

## Implementation Plan

### Step 1: Fix Immediate Schema Issue
```python
# In gencc_async.py, replace:
if result["status"] == "normalized":

# With:
if result.get("status") == "normalized" or result.get("source") in ["database", "hgnc"]:
```

### Step 2: Enhance Async Normalization Function
```python
# In gene_normalization_async.py, update return schema:
results[original_text] = {
    "status": "normalized",  # NEW: Add status field
    "approved_symbol": gene_info["approved_symbol"],
    "hgnc_id": gene_info["hgnc_id"],
    "source": "database",    # Keep for backwards compatibility
    "staging_id": None,      # NEW: Add staging support
    "error": None,           # NEW: Add error field
    "original_data": mapping["original_data"]
}
```

### Step 3: Add Staging Logic for "not_found" Cases
```python
# For genes not found in database or HGNC:
if cleaned in existing_genes or (cleaned in hgnc_results and hgnc_results[cleaned]):
    # Normalized case (existing logic)
else:
    # Create staging record for manual review
    staging_result = _create_staging_record_async(
        db, original_text, source_name, mapping["original_data"],
        reason="Gene not found in database or HGNC"
    )
    results[original_text] = staging_result
```

## Expected Outcomes

### Before Fix
- ✅ 352 genes processed
- ❌ 0 evidence records created
- ❌ No staging for problematic genes
- ❌ GenCC data not contributing to evidence scores

### After Fix
- ✅ ~300-320 genes normalized + evidence created
- ✅ ~30-50 genes staged for manual review  
- ✅ Complete evidence data structure
- ✅ GenCC contributing to percentile scoring
- ✅ Professional curation workflow maintained

## Testing Strategy

### Validation Steps
1. **Database Reset**: Clean start with make db-reset
2. **GenCC Pipeline Test**: Trigger via API and monitor evidence creation
3. **Evidence Verification**: Check gene_evidence table for GenCC records
4. **Staging Verification**: Check gene_normalization_staging table
5. **Score Integration**: Verify GenCC contributes to evidence percentiles

### Success Criteria
- GenCC evidence_created > 0 (target: ~800-1000 evidence records)
- Staging records created for problematic genes
- No schema errors in logs
- Evidence data properly structured in JSONB format

## Risk Assessment

### Low Risk Changes
- ✅ Schema field mapping (backwards compatible)
- ✅ Adding missing fields to return values
- ✅ Database operations already proven in sync version

### Medium Risk Changes
- ⚠️ Staging system integration (new async implementation)
- ⚠️ Return schema changes (need to verify all callers)

### Mitigation
- Thorough testing with database reset
- Incremental changes with validation at each step
- Ability to revert to sync GenCC version if needed

## Implementation Order

1. **Database Reset** - Clean slate for testing
2. **Immediate Schema Fix** - Enable evidence creation
3. **Test Evidence Creation** - Verify core functionality  
4. **Staging Enhancement** - Add manual review workflow
5. **Full Integration Test** - Verify complete pipeline
6. **Performance Validation** - Ensure efficiency maintained

This refactor fixes the core schema mismatch while preserving the professional curation workflow through proper staging system integration.