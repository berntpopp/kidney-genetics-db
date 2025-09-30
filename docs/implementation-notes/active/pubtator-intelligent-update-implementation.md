# PubTator Intelligent Update System - Implementation Plan

## Overview

This document provides the exact implementation steps to add intelligent update modes (smart/full) to the PubTator data source, enabling efficient incremental updates that avoid re-fetching all 54,593 publications.

## Implementation Flow

**Current Flow:**
```
API → task_manager.run_source("PubTator") → _run_pubtator → source.update_data(db, tracker) → fetch_raw_data(tracker) → _search_pubtator3(query, tracker)
```

**Enhanced Flow:**
```
API → task_manager.run_source("PubTator", mode="smart") → _run_pubtator → source.update_data(db, tracker, mode) → fetch_raw_data(tracker, mode) → _search_pubtator3(query, tracker, mode)
```

## Changes Required

### 1. API Endpoint Enhancement

**File:** `/backend/app/api/endpoints/datasources.py`  
**Line:** 411-427 (update_datasource function)

**Current code:**
```python
@router.post("/{source_name}/update")
async def update_datasource(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Trigger update for a specific data source
    """
    if source_name not in DATA_SOURCE_CONFIG:
        raise DataSourceError(source_name, "update", "Unknown data source")

    try:
        await task_manager.run_source(source_name)
        return ResponseBuilder.build_success_response(
            data={"message": f"Update triggered for {source_name}", "status": "started"}
        )
    except Exception as e:
        raise DataSourceError(source_name, "update", f"Failed to start update: {e!s}") from e
```

**Replace with:**
```python
from fastapi import Query
from typing import Literal

@router.post("/{source_name}/update")
async def update_datasource(
    source_name: str, 
    mode: Literal["smart", "full"] = Query("smart", description="Update mode: smart (incremental) or full (complete refresh)"),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Trigger update for a specific data source with mode selection.
    
    Modes:
    - smart: Incremental update, stops when hitting database duplicates (default)
    - full: Complete refresh, deletes existing entries first
    """
    if source_name not in DATA_SOURCE_CONFIG:
        raise DataSourceError(source_name, "update", "Unknown data source")

    try:
        await task_manager.run_source(source_name, mode=mode)
        return ResponseBuilder.build_success_response(
            data={
                "message": f"{mode.capitalize()} update triggered for {source_name}", 
                "status": "started",
                "mode": mode
            }
        )
    except Exception as e:
        raise DataSourceError(source_name, "update", f"Failed to start update: {e!s}") from e
```

### 2. Background Task Manager Enhancement

**File:** `/backend/app/core/background_tasks.py`  
**Line:** 56 (run_source method signature)

**Current:**
```python
async def run_source(self, source_name: str, resume: bool = False):
```

**Replace with:**
```python
async def run_source(self, source_name: str, resume: bool = False, mode: str = "smart"):
```

**Line:** 108 (task method call)

**Current:**
```python
task = asyncio.create_task(task_method(resume=resume))
```

**Replace with:**
```python
task = asyncio.create_task(task_method(resume=resume, mode=mode))
```

### 3. Task Decorator Enhancement

**File:** `/backend/app/core/task_decorator.py`  
**Line:** 30 (managed_task wrapper signature)

**Current:**
```python
async def wrapper(self, resume: bool = False) -> dict[str, Any]:
```

**Replace with:**
```python
async def wrapper(self, resume: bool = False, mode: str = "smart") -> dict[str, Any]:
```

**Line:** 43 (func call)

**Current:**
```python
result = await func(self, db, tracker, resume)
```

**Replace with:**
```python
result = await func(self, db, tracker, resume, mode)
```

**Line:** 128 (_run_pubtator method)

**Current:**
```python
@managed_task("PubTator")
async def _run_pubtator(self, db, tracker, resume: bool = False):
    """Run PubTator update using the unified template method."""
    source = self._get_source_instance("PubTator", db)
    return await source.update_data(db, tracker)
```

**Replace with:**
```python
@managed_task("PubTator")
async def _run_pubtator(self, db, tracker, resume: bool = False, mode: str = "smart"):
    """Run PubTator update using the unified template method."""
    source = self._get_source_instance("PubTator", db)
    return await source.update_data(db, tracker, mode=mode)
```

### 4. Data Source Base Class Enhancement

**File:** `/backend/app/core/data_source_base.py`  
**Line:** 96 (update_data method signature)

**Current:**
```python
async def update_data(self, db: Session, tracker: ProgressTracker) -> dict[str, Any]:
```

**Replace with:**
```python
async def update_data(self, db: Session, tracker: ProgressTracker, mode: str = "smart") -> dict[str, Any]:
```

**Line:** 61 (fetch_raw_data abstract method)

**Current:**
```python
async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> Any:
```

**Replace with:**
```python
async def fetch_raw_data(self, tracker: "ProgressTracker" = None, mode: str = "smart") -> Any:
```

**Line:** 123 (fetch_raw_data call)

**Current:**
```python
raw_data = await self.fetch_raw_data(tracker=tracker)
```

**Replace with:**
```python
raw_data = await self.fetch_raw_data(tracker=tracker, mode=mode)
```

### 5. PubTator Source Implementation

**File:** `/backend/app/pipeline/sources/unified/pubtator.py`  
**Line:** 88 (fetch_raw_data method signature)

**Current:**
```python
async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> dict[str, Any]:
```

**Replace with:**
```python
async def fetch_raw_data(self, tracker: "ProgressTracker" = None, mode: str = "smart") -> dict[str, Any]:
```

**Line:** 101 (_search_pubtator3 call)

**Current:**
```python
search_results = await self._search_pubtator3(self.kidney_query, tracker)
```

**Replace with:**
```python
search_results = await self._search_pubtator3(self.kidney_query, tracker, mode)
```

### 6. PubTator Search Method Enhancement

**File:** `/backend/app/pipeline/sources/unified/pubtator.py`  
**Line:** 206 (_search_pubtator3 method signature)

**Current:**
```python
async def _search_pubtator3(self, query: str, tracker: "ProgressTracker" = None) -> list[dict]:
```

**Replace with:**
```python
async def _search_pubtator3(self, query: str, tracker: "ProgressTracker" = None, mode: str = "smart") -> list[dict]:
```

**Line:** 206 (after method signature, replace entire method with enhanced implementation)

**Replace entire _search_pubtator3 method with:**

```python
async def _search_pubtator3(self, query: str, tracker: "ProgressTracker" = None, mode: str = "smart") -> list[dict]:
    """
    Search PubTator3 with intelligent duplicate detection.

    Args:
        query: Search query
        tracker: Progress tracker
        mode: Update mode - "smart" (incremental) or "full" (complete refresh)

    Returns:
        List of article results with annotations
    """
    
    # Handle full mode: Clear existing entries first
    if mode == "full":
        deleted = self.db_session.query(GeneEvidence).filter(
            GeneEvidence.source_name == 'PubTator'
        ).delete()
        self.db_session.commit()
        logger.sync_info(f"Full update: Deleted {deleted} existing PubTator entries")
        existing_pmids = set()
    else:
        # Smart mode: Get existing PMIDs from database
        existing_pmids = await self._get_existing_pmids_from_db()
        logger.sync_info(f"Smart update: Found {len(existing_pmids)} existing PMIDs in database")
    
    all_results = []
    page = 1
    total_pages = None
    consecutive_duplicate_pages = 0
    max_consecutive_failures = 3
    consecutive_failures = 0
    
    # Smart update limits
    smart_max_pages = 500
    duplicate_threshold = 0.9  # 90%
    consecutive_duplicate_limit = 3
    
    while True:
        # Use PubTator3's native search endpoint
        search_url = f"{self.base_url}/search/"
        params = {
            "text": query,
            "filters": "{}",
            "page": page,
            "sort": self.sort_order,  # Always "score desc" for consistent ordering
        }

        # Log progress
        max_pages_display = smart_max_pages if mode == "smart" else (self.max_pages or "ALL")
        logger.sync_info(
            f"PubTator3 search page (mode: {mode})", 
            current_page=page, 
            max_pages=max_pages_display,
            total_pages=total_pages if total_pages else "?"
        )

        try:
            logger.sync_info("Starting request to PubTator API", page=page, mode=mode)
            
            # Use existing retry strategy
            response = await self.retry_strategy.execute_async(
                lambda url=search_url, p=params: self.http_client.get(url, params=p, timeout=60)
            )

            logger.sync_info("Request completed successfully", page=page)
            consecutive_failures = 0

            if response.status_code != 200:
                logger.sync_error(
                    "PubTator3 search failed", page=page, status_code=response.status_code
                )
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.sync_error("Stopping after consecutive errors", consecutive_failures=consecutive_failures)
                    break
                continue

            try:
                data = response.json()
                logger.sync_debug("JSON parsed successfully", page=page, keys=list(data.keys()))
            except Exception as json_err:
                logger.sync_error("Failed to parse JSON", page=page, error=str(json_err))
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.sync_error("Stopping after consecutive parse errors", consecutive_failures=consecutive_failures)
                    break
                continue

            results = data.get("results", [])
            logger.sync_debug("Found results", page=page, result_count=len(results))

            # Get total pages from API response
            if total_pages is None:
                total_pages = data.get("total_pages", 0)
                total_available = data.get("count", 0)
                logger.sync_info(
                    "Total available data",
                    total_articles=total_available,
                    total_pages=total_pages,
                )

                # Initialize tracker with actual limit we'll process
                if tracker:
                    if mode == "smart":
                        actual_pages = min(smart_max_pages, total_pages)
                        actual_items = min(smart_max_pages * 10, total_available)
                    else:
                        actual_pages = min(self.max_pages, total_pages) if self.max_pages else total_pages
                        actual_items = min(self.max_pages * 10, total_available) if self.max_pages else total_available
                    tracker.update(total_pages=actual_pages, total_items=actual_items)

            if not results:
                logger.sync_info("No more results", page=page)
                break

            # Smart mode: Database duplicate checking
            if mode == "smart":
                page_pmids = {str(r.get("pmid")) for r in results if r.get("pmid")}
                new_pmids = page_pmids - existing_pmids
                duplicate_rate = 1 - (len(new_pmids) / len(page_pmids)) if page_pmids else 0
                
                logger.sync_info(
                    "Database duplicate check",
                    page=page,
                    total_on_page=len(page_pmids),
                    already_in_db=len(page_pmids) - len(new_pmids),
                    new=len(new_pmids),
                    duplicate_rate=f"{duplicate_rate:.1%}"
                )
                
                # Stop if high duplicate rate
                if duplicate_rate > duplicate_threshold:
                    consecutive_duplicate_pages += 1
                    if consecutive_duplicate_pages >= consecutive_duplicate_limit:
                        logger.sync_info(
                            "Stopping smart update: High database duplicate rate",
                            consecutive_pages=consecutive_duplicate_pages,
                            duplicate_rate=f"{duplicate_rate:.1%}"
                        )
                        break
                else:
                    consecutive_duplicate_pages = 0
                
                # Only add results with new PMIDs
                new_results = [r for r in results if str(r.get("pmid")) in new_pmids]
                all_results.extend(new_results)
                
                logger.sync_info(
                    f"Smart mode: Added {len(new_results)} new results from page {page}"
                )
            else:
                # Full mode: Add everything
                all_results.extend(results)
                logger.sync_info(f"Full mode: Added {len(results)} results from page {page}")

            # Update progress
            if tracker:
                total_fetched = len(all_results)
                if mode == "smart":
                    actual_pages = min(smart_max_pages, total_pages)
                else:
                    actual_pages = min(self.max_pages, total_pages) if self.max_pages else total_pages
                    
                tracker.update(
                    current_page=page,
                    current_item=total_fetched,
                    operation=f"Fetching PubTator data ({mode} mode): page {page}/{actual_pages} ({total_fetched} articles)",
                )

            # Check stopping conditions
            if mode == "smart":
                # Smart mode: Stop after reasonable number of pages
                if page >= smart_max_pages:
                    logger.sync_info("Smart update page limit reached", max_pages=smart_max_pages)
                    break
            else:
                # Full mode: Use configured max_pages or get all
                if self.max_pages is not None and page >= self.max_pages:
                    logger.sync_info("Reached configured max pages limit", max_pages=self.max_pages)
                    break

            # Check if we've reached the last page available from API
            if page >= total_pages:
                logger.sync_info(
                    "Reached last available page", current_page=page, total_pages=total_pages
                )
                break

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            page += 1

            # Progress indicator every 100 pages
            if page % 100 == 0:
                logger.sync_info(
                    "Progress update", total_fetched=len(all_results), pages_completed=page - 1
                )

        except Exception as e:
            logger.sync_error(
                "Error on page", page=page, error_type=type(e).__name__, error=str(e)
            )
            consecutive_failures += 1
            
            if consecutive_failures >= max_consecutive_failures:
                logger.sync_warning(
                    "Stopping after consecutive failures",
                    consecutive_failures=consecutive_failures,
                )
                break
            
            page += 1
            continue

    logger.sync_info(
        f"PubTator3 search complete ({mode} mode)",
        total_articles=len(all_results),
        pages_processed=page - 1,
        mode=mode
    )
    return all_results

async def _get_existing_pmids_from_db(self) -> set[str]:
    """
    Get all PMIDs currently in database for PubTator source.
    
    Returns:
        Set of existing PMIDs
    """
    logger.sync_info("Loading existing PMIDs from database")
    
    # Query gene_evidence table for PubTator entries
    staging_records = self.db_session.query(GeneEvidence).filter(
        GeneEvidence.source_name == 'PubTator'
    ).all()
    
    existing_pmids = set()
    for record in staging_records:
        if record.evidence_data and 'pmids' in record.evidence_data:
            pmids = record.evidence_data['pmids']
            if isinstance(pmids, list):
                existing_pmids.update(str(pmid) for pmid in pmids)
    
    logger.sync_info(
        "Loaded existing PMIDs from database",
        count=len(existing_pmids)
    )
    
    return existing_pmids
```

### 7. Database Index Optimization

**Create new migration file:** `/backend/alembic/versions/XXX_add_pubtator_pmids_index.py`

```python
"""Add GIN index for PubTator PMIDs lookup optimization

Revision ID: XXX_add_pubtator_pmids_index
Revises: [PREVIOUS_REVISION]
Create Date: [DATE]
"""

from alembic import op

# revision identifiers
revision = 'XXX_add_pubtator_pmids_index'
down_revision = '[PREVIOUS_REVISION]'  # Replace with actual previous revision
branch_labels = None
depends_on = None

def upgrade():
    # Add GIN index for fast PMID lookups in PubTator evidence
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gene_evidence_pubtator_pmids 
        ON gene_evidence USING GIN ((evidence_data->'pmids')) 
        WHERE source_name = 'PubTator'
    """)

def downgrade():
    # Remove the index
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_gene_evidence_pubtator_pmids")
```

### 8. Configuration Enhancement

**File:** `/backend/app/core/datasource_config.py`  
**Line:** 41 (max_pages configuration)

**Add after line 41:**
```python
        "max_pages": 100,  # Maximum pages to fetch per run (smart mode default)
        # Update modes configuration
        "smart_update": {
            "max_pages": 500,  # Stop after 500 pages max for smart updates
            "duplicate_threshold": 0.9,  # Stop at 90% duplicates
            "consecutive_pages": 3,  # Need 3 consecutive high-duplicate pages
        },
        "full_update": {
            "max_pages": None,  # No limit (get all pages) for full updates
        },
```

## Testing the Implementation

### 1. Smart Update Test
```bash
# Test smart update (default)
curl -X POST "http://localhost:8000/api/datasources/PubTator/update?mode=smart"

# Should see logs like:
# "Smart update: Found X existing PMIDs in database"
# "Database duplicate check: 90.5% duplicate rate"
# "Stopping smart update: High database duplicate rate"
```

### 2. Full Update Test
```bash
# Test full update
curl -X POST "http://localhost:8000/api/datasources/PubTator/update?mode=full"

# Should see logs like:
# "Full update: Deleted X existing PubTator entries"
# "Full mode: Added Y results from page Z"
```

### 3. Performance Verification
```bash
# Run database migration first
cd backend && alembic upgrade head

# Check index was created
psql -d your_db -c "\d gene_evidence"  # Should show the new GIN index
```

## Expected Results

### Smart Update Performance
- **Initial run**: Fetches 50-200 pages before hitting duplicates (~5-15 minutes)
- **Subsequent runs**: Stops quickly when hitting existing data (~1-5 minutes)
- **Coverage**: Gets most recent high-relevance publications efficiently

### Full Update Performance  
- **Time**: 8-10 hours (processes all 5,460 pages)
- **Coverage**: All 54,593 publications
- **Usage**: One-time initial load or periodic complete refresh

### Database Impact
- **GIN index**: Fast JSONB pmids array lookups
- **Query performance**: <100ms for duplicate checking
- **Storage**: Minimal overhead from index

## Rollback Plan

If issues arise, revert in reverse order:
1. Revert API endpoint changes (remove mode parameter)
2. Revert PubTator source changes (restore original _search_pubtator3)
3. Drop database index if needed: `DROP INDEX idx_gene_evidence_pubtator_pmids`
4. Restart services to clear any cached method signatures

All changes are backward compatible - existing calls without mode parameter will default to "smart" mode.