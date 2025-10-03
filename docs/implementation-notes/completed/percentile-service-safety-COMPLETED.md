# STRING PPI Percentile Service - Safety & Regression Prevention

## Critical Safety Considerations

### 1. NO BLOCKING OPERATIONS

#### Problem Areas:
- Database view calculation could take seconds with 30k+ genes
- Thread pool could be exhausted
- Cache operations could timeout

#### Solutions:

**Async with timeout:**
```python
async def calculate_global_percentiles(self, source: str, score_field: str):
    try:
        # Set aggressive timeout
        async with asyncio.timeout(5.0):  # 5 second max
            return await self._calculate_with_fallback(source, score_field)
    except asyncio.TimeoutError:
        await self.logger.error(f"Percentile calculation timed out for {source}")
        return {}  # Return empty, triggers None fallback
```

**Non-blocking thread pool:**
```python
def __init__(self, session):
    # Use separate thread pool to avoid blocking main executor
    self._percentile_executor = ThreadPoolExecutor(
        max_workers=1,  # Only 1 to prevent resource exhaustion
        thread_name_prefix="percentile"
    )
```

### 2. GRACEFUL DEGRADATION

#### Current Behavior Must Continue Working:
```python
# In StringPPIAnnotationSource.fetch_batch()

# SAFE: Try to get percentiles, but don't fail if unavailable
try:
    percentile_service = PercentileService(self.session)
    global_percentiles = await percentile_service.get_cached_percentiles_only(
        "string_ppi"
    )  # Cache-only, no calculation
except Exception as e:
    # Log but don't fail
    await logger.debug(f"Percentile service unavailable: {e}")
    global_percentiles = None

# Apply with fallback
for gene_id in results:
    if global_percentiles and gene_id in global_percentiles:
        results[gene_id]["ppi_percentile"] = global_percentiles[gene_id]
    else:
        # CRITICAL: Don't break existing behavior
        # Return None (not 1.0) to indicate "not calculated"
        results[gene_id]["ppi_percentile"] = None
```

### 3. BACKWARD COMPATIBILITY

#### Existing Data Structure:
```python
# Current structure in gene_annotations:
{
    "string_ppi": [{
        "data": {
            "ppi_score": 21.7,
            "ppi_percentile": 1.0,  # Currently wrong
            "ppi_degree": 5,
            "interactions": [...]
        }
    }]
}

# New structure - SAME, just correct percentile value
{
    "string_ppi": [{
        "data": {
            "ppi_score": 21.7,
            "ppi_percentile": 0.234,  # Now correct
            "ppi_degree": 5,
            "interactions": [...]
        }
    }]
}
```

**No schema changes = No migration needed**

### 4. FRONTEND COMPATIBILITY

The frontend already handles null values:
```vue
<!-- ProteinInteractions.vue line 32-35 -->
{{
  stringPpiData.ppi_percentile
    ? `${(stringPpiData.ppi_percentile * 100).toFixed(0)}th percentile`
    : 'N/A'
}}
```

**No frontend changes needed**

### 5. DEPLOYMENT SAFETY

#### Rolling Deployment Strategy:

**Phase 1: Deploy code (no breaking changes)**
```bash
# Deploy new code with percentile service
# Existing behavior continues (returns None for percentiles)
# No user impact
```

**Phase 2: Create view (non-blocking)**
```sql
-- Run as separate migration
CREATE OR REPLACE VIEW string_ppi_percentiles AS ...
-- Takes <1 second, doesn't lock tables
```

**Phase 3: Calculate percentiles (background)**
```bash
# Run after deployment
curl -X POST /api/annotations/percentiles/refresh?source=string_ppi
# Runs in background, doesn't block API
```

### 6. ERROR SCENARIOS & HANDLING

#### Scenario 1: View doesn't exist
```python
def _calculate_sync(self, source: str):
    try:
        result = self.session.execute(
            text(f"SELECT * FROM {source}_percentiles")
        )
    except Exception as e:
        # View doesn't exist - not an error, just no percentiles yet
        self.logger.sync_debug(f"View {source}_percentiles not found")
        return {}
```

#### Scenario 2: All scores are zero
```python
# In view SQL
WHERE ga.annotations->'string_ppi'->0->'data'->>'ppi_score' != '0'
-- Excludes zero scores from percentile calculation
```

#### Scenario 3: Only one gene has data
```python
def _calculate_sync(self, source: str):
    # ...
    if result.rowcount == 1:
        # Single value gets 0.5 (median) by convention
        row = result.fetchone()
        return {row[0]: 0.5}
```

#### Scenario 4: Cache is corrupted
```python
async def get_cached_percentiles_only(self, source: str):
    try:
        cached = await self.cache_service.get(
            key=f"percentiles:{source}:global",
            namespace="statistics"
        )
        # Validate structure
        if cached and isinstance(cached, dict):
            return cached
    except Exception:
        pass  # Cache error - return None
    return None
```

### 7. PERFORMANCE SAFEGUARDS

#### Limit calculation frequency:
```python
class PercentileService:
    def __init__(self, session):
        self._last_calculation = {}
        self._min_interval = 300  # 5 minutes

    async def calculate_global_percentiles(self, source: str, score_field: str):
        # Check if recently calculated
        last_calc = self._last_calculation.get(source, 0)
        if time.time() - last_calc < self._min_interval:
            # Use cache only
            return await self.get_cached_percentiles_only(source)

        # Proceed with calculation
        self._last_calculation[source] = time.time()
```

### 8. MONITORING & ALERTS

#### Add metrics:
```python
async def calculate_global_percentiles(self, source: str, score_field: str):
    start_time = time.time()
    try:
        result = await self._calculate_with_fallback(source, score_field)

        # Log success metrics
        await self.logger.info(
            "Percentile calculation completed",
            source=source,
            duration_ms=(time.time() - start_time) * 1000,
            gene_count=len(result)
        )

        # Alert if suspicious
        if result and all(v == 1.0 for v in result.values()):
            await self.logger.error(
                "ALERT: All percentiles are 1.0 - calculation may be broken"
            )

        return result
    except Exception as e:
        await self.logger.error(
            "Percentile calculation failed",
            source=source,
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000
        )
        return {}
```

### 9. TESTING CHECKLIST

Before deployment, verify:

```python
# tests/test_percentile_regression.py

def test_api_continues_without_percentiles():
    """API must work even if percentile service fails."""
    # Disable percentile service
    # Fetch gene
    # Assert API returns data with ppi_percentile=None

def test_annotation_pipeline_continues():
    """Pipeline must complete even if percentile calc fails."""
    # Mock percentile service to raise exception
    # Run annotation pipeline
    # Assert pipeline completes successfully

def test_frontend_handles_null_percentiles():
    """Frontend must display 'N/A' for null percentiles."""
    # Return null percentile
    # Assert frontend shows 'N/A' not error

def test_no_blocking_on_large_dataset():
    """Percentile calc must not block API."""
    # Start percentile calculation for 30k genes
    # Immediately call API endpoint
    # Assert API responds in <100ms

def test_backward_compatibility():
    """Existing data structure must remain unchanged."""
    # Load gene with old structure
    # Apply percentile update
    # Assert only ppi_percentile value changed
```

### 10. ROLLBACK PLAN

If issues arise:

```bash
# 1. Disable percentile calculation (immediate)
# Set environment variable
DISABLE_PERCENTILE_CALCULATION=true

# 2. Clear bad cache (if needed)
redis-cli DEL "cache:statistics:percentiles:*"

# 3. Revert view (if needed)
DROP VIEW IF EXISTS string_ppi_percentiles;

# 4. Reset percentiles to null (safe state)
UPDATE gene_annotations
SET annotations = jsonb_set(
    annotations,
    '{string_ppi,0,data,ppi_percentile}',
    'null'::jsonb
)
WHERE annotations ? 'string_ppi';
```

## Summary

### Key Safety Features:
1. **Non-blocking**: All calculations in thread pool with timeout
2. **Graceful degradation**: Returns None if unavailable, never fails
3. **Backward compatible**: Same data structure, only value changes
4. **No schema changes**: No migrations needed
5. **Cache-first**: Prefer cached values to avoid recalculation
6. **Frequency limiting**: Prevents calculation storms
7. **Comprehensive monitoring**: Alerts for anomalies
8. **Easy rollback**: Can disable instantly via environment variable

### The system will:
- ✅ Continue working if percentile service fails
- ✅ Not block the API during calculation
- ✅ Handle edge cases (0 genes, 1 gene, all zeros)
- ✅ Work with existing frontend without changes
- ✅ Preserve all existing functionality
- ❌ NOT return misleading 100th percentile anymore