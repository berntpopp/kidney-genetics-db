# PubTator Intelligent Update System

## Executive Summary

### The Problem
Currently, our PubTator integration fetches only 1,000 publications out of 54,593 available kidney disease-related articles. After the initial database population, we need an efficient way to keep the data current without re-fetching all 54,593 publications every time (which takes 8-10 hours).

### The Goal
Build an intelligent update system that:
1. **Initial Load**: Fetches all 54,593 publications once to populate the database (8-10 hours)
2. **Smart Updates**: Subsequently fetches only NEW publications by detecting when we're hitting data we already have (5-15 minutes)
3. **Quality First**: Prioritizes the most relevant kidney disease publications

### The Solution
Two update modes:
- **Full Update** (one-time): Clear database, fetch everything fresh
- **Smart Update** (regular): Check against database, stop when hitting duplicates

This approach increases our literature coverage by **54x** while keeping update times manageable.

## Core Concept: Database Duplicate Detection

**The Key Insight**: Check fetched PMIDs against existing DATABASE entries, not a cache! The database is our source of truth for what publications we already have.

### Critical Design Decision: Consistent Sorting

**Both smart and full updates MUST use the same sorting order (score desc)**

Why use "score desc" (relevance)?
- We want the most relevant kidney disease publications first
- Higher quality, more relevant results get priority
- Less noise from marginally related papers

Why must both modes use the same sorting?
If full update uses "score desc" and smart update uses "date desc":
- Full update fetches: PMID 123, 456, 789 (most relevant)
- Smart update fetches: PMID 999, 888, 777 (most recent)
- Smart update wouldn't find duplicates until much later
- Result: Processing hundreds of pages before detecting existing data

With consistent sorting (score desc for both):
- Full update fetches: PMID 123, 456, 789... (by relevance)
- Smart update fetches: PMID 123, 456, 789... (same order)
- Smart update immediately detects duplicates and stops
- Result: Efficient duplicate detection + best quality data

### Update Modes

#### Smart Update (Default)
- **Keep existing database entries**
- Fetch pages from PubTator API (score desc - relevance)
- Check each page's PMIDs against database
- **Stop when most PMIDs already exist in database**
- Add only new PMIDs to database
- Note: New highly-relevant publications will appear early in results
- Less relevant new publications might be missed (acceptable trade-off)

#### Full Update (Manual)
- **Delete all PubTator entries from database first**
- Fetch all pages from PubTator API
- Insert everything fresh
- No duplicate checking needed

## Implementation: Minimal Changes to Existing Code

### 1. Database Duplicate Detection

```python
class PubTatorUnifiedSource(UnifiedDataSource):
    
    async def _get_existing_pmids_from_db(self) -> Set[str]:
        """Get all PMIDs currently in database for PubTator source"""
        
        # Query gene_evidence table for PubTator entries
        # Note: Adjust based on actual table structure
        staging_records = self.db_session.query(GeneEvidence).filter(
            GeneEvidence.source_name == 'PubTator'
        ).all()
        
        existing_pmids = set()
        for record in staging_records:
            if record.evidence_data and 'pmids' in record.evidence_data:
                existing_pmids.update(record.evidence_data['pmids'])
        
        logger.sync_info(
            "Loaded existing PMIDs from database",
            count=len(existing_pmids)
        )
        
        return existing_pmids
```

### 2. Enhanced Search with Database Checking

```python
async def _search_pubtator3(self, query: str, tracker: "ProgressTracker" = None,
                           mode: str = "smart") -> list[dict]:
    """
    Enhanced search with database duplicate detection.
    
    Args:
        query: Search query
        tracker: Progress tracker
        mode: "smart" (incremental) or "full" (complete refresh)
    """
    
    # For full update: Clear existing entries first
    if mode == "full":
        deleted = self.db_session.query(GeneEvidence).filter(
            GeneEvidence.source_name == 'PubTator'
        ).delete()
        self.db_session.commit()
        logger.sync_info(f"Full update: Deleted {deleted} existing PubTator entries")
        existing_pmids = set()
    else:
        # Smart update: Load existing PMIDs from database
        existing_pmids = await self._get_existing_pmids_from_db()
    
    all_results = []
    page = 1
    total_pages = None
    consecutive_duplicate_pages = 0
    
    # CRITICAL: Must use same sorting for both modes!
    # Use score desc to get most relevant publications first
    # Consistent sorting ensures duplicate detection works
    sort_order = "score desc"  # Always use relevance for best quality + duplicate detection
    
    while True:
        # Existing API call code...
        search_url = f"{self.base_url}/search/"
        params = {
            "text": query,
            "filters": "{}",
            "page": page,
            "sort": sort_order,
        }
        
        response = await self.retry_strategy.execute_async(
            lambda: self.http_client.get(search_url, params=params, timeout=60)
        )
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            break
            
        # Database duplicate checking (only for smart mode)
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
            if duplicate_rate > 0.9:  # 90% already in database
                consecutive_duplicate_pages += 1
                if consecutive_duplicate_pages >= 3:
                    logger.sync_info(
                        "Stopping smart update: High database duplicate rate",
                        consecutive_pages=consecutive_duplicate_pages
                    )
                    break
            else:
                consecutive_duplicate_pages = 0
            
            # Only add results with new PMIDs
            new_results = [r for r in results if str(r.get("pmid")) in new_pmids]
            all_results.extend(new_results)
            
            # Stop after reasonable number of pages for smart update
            if page >= 500:  # Configurable limit
                logger.sync_info("Smart update page limit reached")
                break
        else:
            # Full mode: Add everything
            all_results.extend(results)
            
            # Full mode: No page limit except max_pages config
            if self.max_pages and page >= self.max_pages:
                break
        
        # Rate limiting
        await asyncio.sleep(self.rate_limit_delay)
        page += 1
        
        # Update progress
        if tracker:
            tracker.update(
                current_page=page,
                operation=f"Fetching PubTator page {page}"
            )
    
    logger.sync_info(
        f"{mode.capitalize()} update complete",
        pages_processed=page,
        articles_fetched=len(all_results),
        mode=mode
    )
    
    return all_results
```

### 3. Simple API Endpoint

```python
@router.post("/sources/pubtator/update")
async def update_pubtator(
    mode: str = Query("smart", regex="^(smart|full)$"),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Trigger PubTator update.
    
    Modes:
    - smart: Incremental update, stops when hitting database duplicates
    - full: Complete refresh, deletes existing entries first
    """
    
    source = PubTatorUnifiedSource(
        cache_service=get_cache_service(db),
        http_client=get_cached_http_client(),
        db_session=db
    )
    
    # Start background task
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        run_pubtator_update,
        source=source,
        mode=mode,
        task_id=task_id
    )
    
    return {
        "task_id": task_id,
        "mode": mode,
        "message": f"PubTator {mode} update started"
    }
```

### 4. Configuration Update

```python
# datasource_config.py
"PubTator": {
    # ... existing config ...
    
    # Update behavior
    "smart_update": {
        "max_pages": 500,  # Stop after 500 pages max
        "duplicate_threshold": 0.9,  # Stop at 90% duplicates
        "consecutive_pages": 3,  # Need 3 consecutive high-duplicate pages
        "sort": "score desc",  # Relevance - must match full update!
    },
    "full_update": {
        "max_pages": None,  # No limit (get all 5460 pages)
        "sort": "score desc",  # Relevance - same as smart for duplicate detection
    }
}
```

## Database Query Optimization

### Add Index for Fast PMID Lookups

```sql
-- Add GIN index for JSONB pmids array
CREATE INDEX idx_gene_evidence_pubtator_pmids 
ON gene_evidence USING GIN ((evidence_data->'pmids')) 
WHERE source_name = 'PubTator';

-- This makes checking existing PMIDs much faster
```

### Optimized PMID Query

```python
async def _get_existing_pmids_from_db_optimized(self) -> Set[str]:
    """Optimized query using JSONB operations"""
    
    # Use raw SQL for better performance
    query = text("""
        SELECT DISTINCT jsonb_array_elements_text(evidence_data->'pmids') as pmid
        FROM gene_evidence
        WHERE source_name = 'PubTator'
        AND evidence_data ? 'pmids'
    """)
    
    result = self.db_session.execute(query)
    existing_pmids = {row[0] for row in result}
    
    logger.sync_info(f"Found {len(existing_pmids)} existing PMIDs in database")
    return existing_pmids
```

## Usage Patterns

### Initial Database Population
```bash
# One-time full load to populate database
POST /api/admin/sources/pubtator/update?mode=full

# This will:
# 1. DELETE all existing PubTator entries
# 2. Fetch all 54,593 publications
# 3. Insert everything fresh
# Time: 8-10 hours
```

### Regular Smart Updates
```bash
# Regular incremental updates (daily/weekly)
POST /api/admin/sources/pubtator/update?mode=smart

# This will:
# 1. Keep existing database entries
# 2. Fetch publications (score desc - relevance, same as full update)
# 3. Check each page against database
# 4. Stop when hitting 90% duplicates
# 5. Add only new publications
# Time: 5-15 minutes
```

## Key Differences from Cache Approach

| Aspect | Cache Approach (Wrong) | Database Approach (Correct) |
|--------|------------------------|----------------------------|
| Duplicate Check | Against cached PMID list | Against actual database records |
| Smart Update | Would still process duplicates | Stops when database has the data |
| Full Update | Unclear purpose | Clears database, fresh start |
| Memory Usage | Loads all PMIDs in memory | Database query (scalable) |
| Persistence | Cache expires | Database is source of truth |

## Performance Considerations

### Smart Update Performance
- First pages: Mostly new PMIDs (fast processing)
- Later pages: Mostly duplicates (triggers stop)
- Typical pattern: Process 50-200 pages before stopping
- Time: 5-15 minutes

### Full Update Performance  
- No duplicate checking (faster per page)
- Processes all 5,460 pages
- Clean slate approach
- Time: 8-10 hours

### Database Performance
- GIN index on JSONB makes PMID lookups fast
- Batch inserts for new records
- Transaction management for consistency

## Implementation Timeline

### Day 1: Core Changes
- Modify `_search_pubtator3` with mode parameter
- Add database duplicate detection
- Implement full mode with deletion

### Day 2: Testing
- Test smart mode duplicate detection
- Verify full mode clears correctly
- Check performance with index

### Day 3: Integration
- Add API endpoint
- Test with progress tracker
- Deploy to staging

## Why This Approach is Correct

1. **Database as Source of Truth**: Checks against actual stored data
2. **True Incremental Updates**: Only adds genuinely new data
3. **Clean Full Updates**: Complete refresh when needed
4. **Efficient**: Stops fetching when data exists
5. **Simple**: One mode parameter, clear behavior
6. **Quality First**: Score desc ensures most relevant publications prioritized

## Final Summary

### The Solution in a Nutshell
- **Problem**: Currently fetching only 1,000 of 54,593 available publications
- **Solution**: Add duplicate detection against database with smart stopping
- **Implementation**: ~200 lines of code changes to existing system
- **Sorting**: Always use "score desc" for both modes (relevance + consistency)
- **Smart Update**: Fetches until hitting duplicates (5-15 minutes)
- **Full Update**: Deletes all, fetches everything (8-10 hours, manual only)
- **Result**: 54x coverage increase with minimal complexity

This approach correctly checks against the database to avoid processing data we already have, prioritizing the most relevant kidney disease publications.