# Global Percentile Service Implementation Plan

## Problem Statement
STRING PPI percentile calculations are broken - all genes show 100th percentile when fetched individually because percentiles are calculated within single-gene batches rather than globally across all genes.

## Solution: Reusable Global Percentile Service

### Core Architecture

#### 1. PercentileService (New Core Utility)
A reusable service following existing patterns (CacheService, RetryService) that:
- Calculates percentiles globally using PostgreSQL's `PERCENT_RANK()`
- Stores results in cache for fast retrieval
- Runs calculations in ThreadPoolExecutor to avoid blocking
- Can be extended to any annotation source

#### 2. Database Storage
```sql
-- Store pre-computed percentiles in gene_annotations JSONB
-- No new tables needed - follows existing pattern
UPDATE gene_annotations
SET annotations = jsonb_set(
    annotations,
    '{string_ppi,0,data,ppi_percentile_global}',
    to_jsonb(percentile_value)
)
WHERE annotations ? 'string_ppi';
```

#### 3. PostgreSQL View for Calculation
```sql
-- Add to app/db/views.py
CREATE VIEW string_ppi_percentiles AS
SELECT
    ga.gene_id,
    g.approved_symbol,
    CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT) as ppi_score,
    PERCENT_RANK() OVER (
        ORDER BY CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT)
    ) AS percentile_rank
FROM gene_annotations ga
JOIN genes g ON g.id = ga.gene_id
WHERE ga.annotations->'string_ppi'->0->'data' ? 'ppi_score'
  AND ga.annotations->'string_ppi'->0->'data'->>'ppi_score' != 'null';
```

### Implementation Components

#### Core Service (`app/core/percentile_service.py`)
```python
class PercentileService:
    """Global percentile calculation service for annotation scores."""

    def __init__(self, session):
        self.session = session
        self.logger = get_logger(__name__)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.cache = get_cache_service(session)

    async def calculate_global_percentiles(self, source: str, score_field: str):
        """Calculate percentiles using PostgreSQL PERCENT_RANK()."""
        # Non-blocking execution
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._calculate_percentiles_sync,
            source, score_field
        )

    def _calculate_percentiles_sync(self, source: str, score_field: str):
        """Sync method for thread pool execution."""
        # Use view to calculate percentiles
        result = self.session.execute(
            text(f"SELECT * FROM {source}_percentiles")
        )

        # Store in cache and update gene_annotations
        percentiles = {}
        for row in result:
            gene_id, symbol, score, percentile = row
            percentiles[gene_id] = percentile

            # Update JSONB directly
            self._update_gene_percentile(gene_id, source, percentile)

        return percentiles
```

#### STRING PPI Integration
Modify `StringPPIAnnotationSource` to:
1. Remove inline percentile calculation
2. Use pre-computed global percentiles
3. Trigger global recalculation after batch updates

#### Background Task (`app/pipeline/tasks/percentile_updater.py`)
```python
async def update_percentiles_for_source(db: Session, source: str):
    """Update global percentiles for a specific source."""
    service = PercentileService(db)

    if source == "string_ppi":
        await service.calculate_global_percentiles("string_ppi", "ppi_score")
    # Add other sources as needed
```

### API Integration

#### Admin Endpoint (`app/api/endpoints/gene_annotations.py`)
Add to existing file:
```python
@router.post("/annotations/percentiles/refresh")
async def refresh_percentiles(
    source: str = Query(..., description="Source to refresh (e.g., string_ppi)"),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Trigger global percentile recalculation for a source."""
    background_tasks.add_task(update_percentiles_for_source, db, source)
    return {"status": "scheduled", "source": source}
```

### Testing Strategy

#### Unit Test (`tests/test_percentile_service.py`)
```python
def test_percentile_calculation_with_ties():
    """Test that tied scores get averaged ranks."""
    scores = [10, 20, 20, 30, 40]
    percentiles = calculate_percentiles(scores)
    assert percentiles[1] == percentiles[2]  # Tied scores
    assert 0.3 < percentiles[1] < 0.4  # Average rank
```

#### Integration Test
```python
async def test_string_ppi_global_percentiles():
    """Test that global percentiles are correctly applied."""
    # Create test genes with known scores
    # Calculate global percentiles
    # Verify distribution is correct
    # Check individual gene lookups return global percentiles
```

### Rollback Strategy
- Cache previous percentiles before recalculation
- If validation fails, restore from cache
- Use database transactions for JSONB updates

### Monitoring
- Log percentile distribution statistics after calculation
- Alert if median != ~0.5 or if all values are identical
- Track calculation time and cache hit rates

## Success Criteria
1. **Correctness**: Genes show accurate global percentiles, not batch-relative
2. **Performance**: <100ms percentile lookup from cache
3. **Non-blocking**: API remains responsive during recalculation
4. **Reusability**: Service works for multiple annotation sources

## Future Extensions
- Cross-source percentile comparisons
- Configurable ranking algorithms (weighted, normalized)
- Automated periodic recalculation