# STRING PPI Percentile Service - Integration & Triggering

## Critical Integration Points

### 1. When Percentiles Are Calculated

#### Automatic Triggers:
1. **After STRING PPI batch completes** in annotation pipeline
2. **On first system deployment** (bootstrap)
3. **After bulk gene updates** via admin API

#### Manual Triggers:
1. Admin API endpoint for forced refresh
2. CLI command for maintenance

### 2. Triggering in Annotation Pipeline

The percentiles MUST be calculated AFTER all STRING PPI scores are computed, not during.

#### Location: `app/pipeline/annotation_pipeline.py`
```python
# Line 216-220 (after source completion)
if source_name == "string_ppi" and source_name in sources_completed:
    # STRING PPI needs global percentile recalculation
    from app.pipeline.tasks.percentile_updater import update_percentiles_for_source
    await logger.info("Triggering STRING PPI percentile recalculation")
    await update_percentiles_for_source(self.db, "string_ppi")
```

### 3. Fallback Behavior

#### Three-tier fallback strategy:

**Tier 1: Use cached percentiles**
```python
# In PercentileService
cached = await self.cache_service.get(
    key=f"percentiles:{source}:global",
    namespace="statistics"
)
if cached:
    return cached
```

**Tier 2: Calculate from database view**
```python
# If cache miss, calculate from view
result = self.session.execute(
    text("SELECT * FROM string_ppi_percentiles")
)
if result.rowcount > 0:
    # Process and cache
    return percentiles
```

**Tier 3: Return None (not misleading 100th)**
```python
# In StringPPIAnnotationSource.fetch_batch()
if gene_id in global_percentiles:
    results[gene_id]["ppi_percentile"] = global_percentiles[gene_id]
else:
    # Don't mislead - no percentile is better than wrong percentile
    results[gene_id]["ppi_percentile"] = None
    await logger.warning(
        f"No percentile available for gene {gene_id} - returning None"
    )
```

### 4. Bootstrap/First Run Initialization

#### Problem: On first deployment, no STRING PPI scores exist yet

#### Solution: Two-phase initialization

**Phase 1: Initial annotation run**
```python
# STRING PPI calculates raw scores only
# Sets ppi_percentile to None for all genes
```

**Phase 2: Post-processing percentile calculation**
```python
# After ALL genes have scores, trigger percentile calculation
# This updates all ppi_percentile values globally
```

#### Bootstrap Command:
```bash
# Add to Makefile
bootstrap-percentiles:
	cd backend && uv run python -c "
	from app.core.database import get_db
	from app.pipeline.tasks.percentile_updater import update_all_percentiles
	import asyncio
	db = next(get_db())
	asyncio.run(update_all_percentiles(db))
	"
```

### 5. Modified StringPPIAnnotationSource

```python
async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
    """
    Fetch annotations with proper fallback handling.
    """
    # ... calculate raw scores ...

    # Try to get global percentiles
    try:
        from app.core.percentile_service import PercentileService
        percentile_service = PercentileService(self.session)
        global_percentiles = await percentile_service.calculate_global_percentiles(
            "string_ppi", "ppi_score"
        )
    except Exception as e:
        await logger.warning(
            f"Failed to get global percentiles: {e}. Using None for all."
        )
        global_percentiles = {}

    # Apply percentiles with fallback
    for gene_id in results:
        if global_percentiles and gene_id in global_percentiles:
            results[gene_id]["ppi_percentile"] = global_percentiles[gene_id]
        else:
            # CRITICAL: Return None, not 100th percentile
            results[gene_id]["ppi_percentile"] = None

            # Only warn once per batch to avoid log spam
            if not hasattr(self, '_percentile_warning_shown'):
                await logger.warning(
                    "No global percentiles available - returning None. "
                    "Run percentile calculation after all genes processed."
                )
                self._percentile_warning_shown = True

    return results
```

### 6. PercentileService with Proper Error Handling

```python
class PercentileService:
    async def calculate_global_percentiles(
        self, source: str, score_field: str
    ) -> Dict[int, float]:
        """
        Calculate with multiple fallback levels.
        """
        # Check cache
        cache_key = f"percentiles:{source}:global"
        cached = await self.cache_service.get(
            key=cache_key, namespace="statistics"
        )
        if cached:
            return cached

        # Try database view
        try:
            percentiles = await self._calculate_from_view(source)
            if percentiles:
                # Cache for 1 hour
                await self.cache_service.set(
                    key=cache_key, value=percentiles,
                    namespace="statistics", ttl=3600
                )
                return percentiles
        except Exception as e:
            await self.logger.error(f"Failed to calculate percentiles: {e}")

        # Return empty dict (triggers None fallback)
        return {}

    async def _calculate_from_view(self, source: str) -> Dict[int, float]:
        """Calculate from PostgreSQL view."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._calculate_sync,
            source
        )

    def _calculate_sync(self, source: str) -> Dict[int, float]:
        """Sync calculation for thread pool."""
        result = self.session.execute(
            text(f"""
                SELECT gene_id, percentile_rank
                FROM {source}_percentiles
                WHERE ppi_score > 0
            """)
        )

        if result.rowcount == 0:
            self.logger.sync_warning(
                f"No data in {source}_percentiles view. "
                "Percentiles will be None until calculated."
            )
            return {}

        percentiles = {
            row[0]: round(row[1], 3)
            for row in result
        }

        self.logger.sync_info(
            f"Calculated {len(percentiles)} percentiles from view"
        )

        return percentiles
```

### 7. Monitoring & Validation

```python
# Add to PercentileService
async def validate_percentiles(self, source: str) -> dict:
    """Validate percentile distribution is reasonable."""
    percentiles = await self.calculate_global_percentiles(source, "score")

    if not percentiles:
        return {"status": "error", "message": "No percentiles found"}

    values = list(percentiles.values())

    # Basic sanity checks
    checks = {
        "has_data": len(values) > 0,
        "has_variance": len(set(values)) > 1,  # Not all same
        "median_reasonable": 0.4 < sorted(values)[len(values)//2] < 0.6,
        "min_near_zero": min(values) < 0.1,
        "max_near_one": max(values) > 0.9
    }

    if not all(checks.values()):
        await self.logger.error(
            f"Percentile validation failed for {source}",
            checks=checks
        )

    return {"status": "ok" if all(checks.values()) else "warning", "checks": checks}
```

## Summary

### Key Changes from Original Plan:
1. **Trigger point**: After STRING PPI completes in pipeline, not during batch processing
2. **Fallback**: Returns `None` instead of misleading 100th percentile
3. **Bootstrap**: Handles first-run scenario gracefully
4. **Error handling**: Multiple fallback levels with proper logging
5. **Validation**: Sanity checks to detect calculation issues

### Testing the Integration:
```bash
# 1. Clear existing data
make db-clean

# 2. Run annotation pipeline
curl -X POST http://localhost:8000/api/admin/annotations/update-all

# 3. Check that percentiles are None initially
curl http://localhost:8000/api/genes/HNF1B | jq '.data.attributes.ppi_percentile'
# Should return: null

# 4. Trigger percentile calculation
curl -X POST http://localhost:8000/api/annotations/percentiles/refresh?source=string_ppi

# 5. Check that percentiles are now calculated
curl http://localhost:8000/api/genes/HNF1B | jq '.data.attributes.ppi_percentile'
# Should return: 0.234 (or similar, not 1.0)
```