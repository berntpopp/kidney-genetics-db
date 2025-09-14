# Full Mode Implementation Plan

## Problem Analysis

### Current Issue
The API documentation states that "full" mode "deletes existing entries first" before updating, but this is NOT implemented for most data sources. This causes outdated/incorrect genes to persist in the database even after fixing filtering logic (e.g., TUBA1A brain gene appearing in kidney database).

### Sources Affected

#### Sources WITHOUT deletion logic (broken):
1. **PanelApp** - No `_clear_existing_entries` method, mode parameter not passed
2. **GenCC** - No `_clear_existing_entries` method, mode parameter not passed
3. **HPO** - No `_clear_existing_entries` method, mode parameter not passed
4. **ClinGen** - No `_clear_existing_entries` method, mode parameter not passed
5. **Literature** - No `_clear_existing_entries` method
6. **DiagnosticPanels** - No `_clear_existing_entries` method

#### Sources WITH deletion logic (working):
1. **PubTator** - Has `_clear_existing_entries` method, mode parameter properly passed

## Root Causes

### 1. Task Decorator Not Passing Mode Parameter
In `backend/app/core/task_decorator.py`:
- Only `_run_pubtator` accepts and passes the `mode` parameter
- All other sources (`_run_panelapp`, `_run_gencc`, `_run_hpo`, `_run_clingen`) don't accept mode

### 2. Base Class Doesn't Implement Deletion
In `backend/app/core/data_source_base.py`:
- `update_data()` method accepts `mode` parameter but NEVER uses it
- No call to `_clear_existing_entries()` when mode == "full"
- No default `_clear_existing_entries()` implementation

### 3. Unified Sources Don't Override
Most unified sources inherit from base classes but don't:
- Override `update_data()` to handle mode
- Implement `_clear_existing_entries()` method

## Implementation Plan

### Phase 1: Fix Base Class (Priority: HIGH)
**File**: `backend/app/core/data_source_base.py`

1. Add `_clear_existing_entries()` method to base class:
```python
async def _clear_existing_entries(self, db: Session) -> int:
    """Clear existing entries for this source (for full mode)."""
    deleted = db.query(GeneEvidence)\
        .filter(GeneEvidence.source_name == self.source_name)\
        .delete()
    db.commit()
    logger.sync_info(f"Cleared {deleted} existing {self.source_name} entries")
    return deleted
```

2. Modify `update_data()` to handle full mode:
```python
async def update_data(self, db: Session, tracker: ProgressTracker, mode: str = "smart") -> dict[str, Any]:
    stats = self._initialize_stats()

    try:
        tracker.start(f"Starting {self.source_name} update (mode: {mode})")

        # Clear existing entries if full mode
        if mode == "full":
            tracker.update(operation="Clearing existing entries")
            deleted = await self._clear_existing_entries(db)
            stats["entries_deleted"] = deleted
            logger.sync_info(f"Full mode: deleted {deleted} existing entries")

        # Continue with existing logic...
```

### Phase 2: Fix Task Decorator (Priority: HIGH)
**File**: `backend/app/core/task_decorator.py`

Update ALL source methods to accept and pass mode parameter:

```python
@managed_task("PanelApp")
async def _run_panelapp(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run PanelApp update using the unified template method."""
    source = self._get_source_instance("PanelApp", db)
    return await source.update_data(db, tracker, mode=mode)

@managed_task("GenCC")
async def _run_gencc(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run GenCC update using the unified template method."""
    source = self._get_source_instance("GenCC", db)
    return await source.update_data(db, tracker, mode=mode)

# Repeat for HPO, ClinGen, etc.
```

### Phase 3: Fix Background Task Manager (Priority: HIGH)
**File**: `backend/app/core/background_tasks.py`

Update to pass mode parameter to ALL sources (not just PubTator):

```python
# Line 110-114, replace with:
task = asyncio.create_task(task_method(resume=resume, mode=mode))
```

### Phase 4: Update Unified Sources (Priority: MEDIUM)
For sources that need special handling, override `_clear_existing_entries()`:

**Example for PanelApp**:
```python
async def _clear_existing_entries(self, db: Session) -> int:
    """Clear existing PanelApp entries and invalidate cache."""
    # Clear database entries
    deleted = await super()._clear_existing_entries(db)

    # Clear cache for all regions
    for region in self.regions:
        cache_key = f"panels:{region}"
        await self.cache_service.delete(cache_key)

    return deleted
```

### Phase 5: Testing & Verification (Priority: HIGH)

1. **Manual Testing Protocol**:
   - Add test gene to each source
   - Run full mode update
   - Verify test gene is removed
   - Verify correct genes remain

2. **Specific Test for TUBA1A**:
   - Run full mode for PanelApp
   - Verify TUBA1A is removed
   - Run full mode for GenCC
   - Verify no brain-related genes remain

3. **Add Unit Tests**:
```python
async def test_full_mode_deletes_existing():
    # Add gene via source
    # Run full mode update with different data
    # Assert old gene is deleted
    # Assert new gene exists
```

## Implementation Order

1. **Immediate Fix** (for TUBA1A issue):
   - Fix task_decorator.py for PanelApp and GenCC
   - Fix background_tasks.py to pass mode
   - Add _clear_existing_entries to base class
   - Run full mode update for both sources

2. **Complete Fix** (systematic):
   - Implement base class changes
   - Update all task decorator methods
   - Test each source individually
   - Add comprehensive tests

## Risk Assessment

- **Low Risk**: Changes are additive, won't break existing smart mode
- **Data Loss**: Full mode will delete and re-add all entries (by design)
- **Performance**: Full mode will be slower but more thorough
- **Cache**: May need to clear caches when running full mode

## Success Criteria

1. ✅ "Full" mode actually deletes existing entries before updating
2. ✅ TUBA1A and other incorrect genes are removed after full update
3. ✅ All sources respect the mode parameter
4. ✅ API documentation matches actual behavior
5. ✅ No regression in "smart" mode functionality

## Timeline

- **Day 1**: Implement Phase 1-3 (core fixes)
- **Day 2**: Test with PanelApp and GenCC, verify TUBA1A removal
- **Day 3**: Implement Phase 4-5 (complete all sources)
- **Day 4**: Comprehensive testing and documentation update