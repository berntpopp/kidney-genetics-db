# Issue #12 Investigation Summary: TUBA1A Brain Gene in Kidney Database

## Executive Summary

TUBA1A (a brain tubulin gene) incorrectly appears in the kidney genetics database because:
1. Initial keyword filtering was too broad ("tubul" matched "Tubulinopathies")
2. After fixing keywords, the gene persisted because **"full" mode doesn't actually delete old data**
3. Only PubTator implements deletion; all other sources (PanelApp, GenCC, HPO, ClinGen) are broken

## Investigation Timeline

### 1. Initial Problem Discovery
- **Issue**: TUBA1A appears at http://localhost:5173/genes/TUBA1A
- **Source**: PanelApp "Tubulinopathies" panel (brain disorder)
- **Root Cause**: Keyword "tubul" too broad, matching brain disorders

### 2. Keyword Fix Implementation
Fixed in datasource_config.py:
```python
# BEFORE (hardcoded in source files)
self.kidney_keywords = ["kidney", "renal", "tubul", ...]  # BAD!

# AFTER (in config)
"kidney_keywords": [
    "kidney", "renal", "nephro", "glomerul",
    # "tubul",  # REMOVED - too broad
    "tubulopathy",  # More specific
    "tubulointerstitial",  # More specific
]
```

### 3. Persistence Problem Discovery
After fixing keywords and restarting sources, TUBA1A **still appeared** in database.

**Investigation revealed**:
- API docs claim full mode "deletes existing entries first"
- Reality: Only PubTator actually implements deletion
- Other sources just add/update, never delete

## Code Evidence

### Problem 1: Task Decorator Doesn't Pass Mode
**File**: `backend/app/core/task_decorator.py`
```python
# BROKEN - mode parameter ignored
@managed_task("PanelApp")
async def _run_panelapp(self, db, tracker, resume: bool = False):
    source = self._get_source_instance("PanelApp", db)
    return await source.update_data(db, tracker)  # NO MODE!

# WORKING - mode parameter passed
@managed_task("PubTator")
async def _run_pubtator(self, db, tracker, resume: bool = False, mode: str = "smart"):
    source = self._get_source_instance("PubTator", db)
    return await source.update_data(db, tracker, mode=mode)  # MODE PASSED!
```

### Problem 2: Background Tasks Only Passes Mode to PubTator
**File**: `backend/app/core/background_tasks.py`
```python
# Line 111-114
if source_name.lower() == "pubtator":
    task = asyncio.create_task(task_method(resume=resume, mode=mode))
else:
    task = asyncio.create_task(task_method(resume=resume))  # NO MODE!
```

### Problem 3: Base Class Doesn't Handle Full Mode
**File**: `backend/app/core/data_source_base.py`
```python
async def update_data(self, db: Session, tracker: ProgressTracker, mode: str = "smart"):
    # mode parameter accepted but NEVER USED for deletion!
    # No call to _clear_existing_entries
    # Just fetches, processes, and stores (adds/updates only)
```

### Problem 4: Only PubTator Has Deletion Logic
**Working Example** - `pubtator.py`:
```python
async def _clear_existing_entries(self):
    """Clear existing PubTator entries for full mode."""
    deleted = (
        self.db_session.query(GeneEvidence)
        .filter(GeneEvidence.source_name == "PubTator")
        .delete()
    )
    self.db_session.commit()
    logger.sync_info(f"Cleared {deleted} existing PubTator entries")
```

**Missing in ALL other sources**: PanelApp, GenCC, HPO, ClinGen, Literature, DiagnosticPanels

## Impact Assessment

### Sources Affected
| Source | Has Deletion? | Gets Mode Param? | Full Mode Works? |
|--------|--------------|------------------|------------------|
| PubTator | ✅ Yes | ✅ Yes | ✅ Yes |
| PanelApp | ❌ No | ❌ No | ❌ No |
| GenCC | ❌ No | ❌ No | ❌ No |
| HPO | ❌ No | ❌ No | ❌ No |
| ClinGen | ❌ No | ❌ No | ❌ No |
| Literature | ❌ No | ❌ No | ❌ No |
| DiagnosticPanels | ❌ No | ❌ No | ❌ No |

### Consequences
1. **Data Quality**: Outdated/incorrect genes persist indefinitely
2. **User Trust**: API documentation lies about "full" mode behavior
3. **Maintenance**: Can't cleanly refresh data sources
4. **TUBA1A**: Will remain until manually deleted or code fixed

## Proposed Solution

### Immediate Fix (for TUBA1A)
1. Add `_clear_existing_entries()` to base class
2. Call it when mode == "full" in base `update_data()`
3. Pass mode parameter in task_decorator.py
4. Remove special case in background_tasks.py

### Complete Fix
See [full-mode-implementation-plan.md](./full-mode-implementation-plan.md) for detailed implementation plan.

## Lessons Learned

1. **Configuration > Hardcoding**: Keywords should always be in config
2. **Test Full Mode**: "Full refresh" features need explicit testing
3. **Trust but Verify**: API docs don't always match implementation
4. **Base Class Patterns**: Common functionality (like deletion) belongs in base class
5. **Consistent Parameters**: All sources should accept same parameters

## User Frustration Points
- Multiple attempts to update sources didn't remove TUBA1A
- API claimed to do full refresh but didn't
- Had to trace through multiple abstraction layers to find issue
- Simple "delete old data" feature was missing despite docs

## Resolution Status
- ✅ Keyword filtering fixed
- ✅ Root cause identified
- ✅ Implementation plan created
- ⏳ Code changes pending
- ⏳ TUBA1A removal pending