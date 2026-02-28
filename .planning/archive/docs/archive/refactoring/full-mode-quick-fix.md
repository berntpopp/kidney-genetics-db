# Quick Fix Guide: Implementing Full Mode Deletion

## Files to Modify (4 files total)

### 1. `backend/app/core/data_source_base.py`

Add deletion method and call it in update_data:

```python
# Add this method to DataSourceBase class
async def _clear_existing_entries(self, db: Session) -> int:
    """Clear existing entries for this source (for full mode)."""
    from app.models.gene_evidence import GeneEvidence

    deleted = db.query(GeneEvidence)\
        .filter(GeneEvidence.source_name == self.source_name)\
        .delete()
    db.commit()
    logger.sync_info(f"Cleared {deleted} existing {self.source_name} entries")
    return deleted

# Modify update_data method (around line 100)
async def update_data(
    self, db: Session, tracker: ProgressTracker, mode: str = "smart"
) -> dict[str, Any]:
    stats = self._initialize_stats()

    try:
        tracker.start(f"Starting {self.source_name} update (mode: {mode})")
        logger.sync_info("Starting data update", source_name=self.source_name, mode=mode)

        # ADD THIS BLOCK
        # Clear existing entries if full mode
        if mode == "full":
            tracker.update(operation="Clearing existing entries")
            deleted = await self._clear_existing_entries(db)
            stats["entries_deleted"] = deleted
            logger.sync_info(f"Full mode: deleted {deleted} existing entries")

        # Rest of existing code continues...
```

### 2. `backend/app/core/task_decorator.py`

Add mode parameter to ALL source methods:

```python
# Update these methods (lines 139-161)

@managed_task("GenCC")
async def _run_gencc(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run GenCC update using the unified template method."""
    source = self._get_source_instance("GenCC", db)
    return await source.update_data(db, tracker, mode=mode)

@managed_task("PanelApp")
async def _run_panelapp(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run PanelApp update using the unified template method."""
    source = self._get_source_instance("PanelApp", db)
    return await source.update_data(db, tracker, mode=mode)

@managed_task("HPO")
async def _run_hpo(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run HPO update using the unified template method."""
    source = self._get_source_instance("HPO", db)
    return await source.update_data(db, tracker, mode=mode)

@managed_task("ClinGen")
async def _run_clingen(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run ClinGen update using the unified template method."""
    source = self._get_source_instance("ClinGen", db)
    return await source.update_data(db, tracker, mode=mode)
```

### 3. `backend/app/core/background_tasks.py`

Remove PubTator special case (around line 110):

```python
# REPLACE lines 110-114
# OLD CODE:
# if source_name.lower() == "pubtator":
#     task = asyncio.create_task(task_method(resume=resume, mode=mode))
# else:
#     task = asyncio.create_task(task_method(resume=resume))

# NEW CODE:
task = asyncio.create_task(task_method(resume=resume, mode=mode))
```

### 4. `backend/app/pipeline/sources/unified/pubtator.py`

Update PubTator to use the base class method:

```python
# Modify _clear_existing_entries to call super() (line 742)
async def _clear_existing_entries(self):
    """Clear existing PubTator entries for full mode."""
    # Use base class implementation
    return await super()._clear_existing_entries(self.db_session)
```

## Testing the Fix

### 1. Restart the backend
```bash
cd /home/bernt-popp/development/kidney-genetics-db
make backend
```

### 2. Run full mode update for PanelApp
```bash
curl -X POST "http://localhost:8000/api/datasources/PanelApp/update?mode=full" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Run full mode update for GenCC
```bash
curl -X POST "http://localhost:8000/api/datasources/GenCC/update?mode=full" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Verify TUBA1A is gone
```bash
# Check if TUBA1A still exists
curl "http://localhost:8000/api/genes?filter[symbol]=TUBA1A"

# Should return empty or no results
```

## Validation Checklist

- [ ] Base class has `_clear_existing_entries` method
- [ ] Base class `update_data` calls deletion when mode == "full"
- [ ] All sources in task_decorator.py accept mode parameter
- [ ] All sources in task_decorator.py pass mode to update_data
- [ ] background_tasks.py passes mode to all sources (not just PubTator)
- [ ] Full mode update for PanelApp removes TUBA1A
- [ ] Full mode update for GenCC removes outdated genes
- [ ] Smart mode still works (incremental updates)

## Expected Behavior After Fix

| Action | Before Fix | After Fix |
|--------|------------|-----------|
| Run full mode | Adds new genes, keeps old | Deletes all, adds new |
| TUBA1A after full mode | Still present | Removed |
| API docs accuracy | Incorrect | Correct |
| Mode parameter | Ignored | Respected |

## Rollback Plan

If issues occur, revert these 4 files to previous version:
```bash
git checkout HEAD~1 backend/app/core/data_source_base.py
git checkout HEAD~1 backend/app/core/task_decorator.py
git checkout HEAD~1 backend/app/core/background_tasks.py
git checkout HEAD~1 backend/app/pipeline/sources/unified/pubtator.py
```