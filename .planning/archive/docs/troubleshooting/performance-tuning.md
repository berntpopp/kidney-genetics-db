# Performance Tuning Guide

**Optimization strategies for the Kidney Genetics Database**

## Performance Targets

| Metric | Target | Current (Production) |
|--------|--------|---------------------|
| API Response (cached) | <10ms | 7-10ms ✅ |
| API Response (uncached) | <100ms | 50-100ms ✅ |
| Event Loop Blocking | <5ms | <1ms ✅ |
| Cache Hit Rate | >75% | 75-95% ✅ |
| WebSocket Stability | 100% uptime | 100% ✅ |
| Annotation Coverage | >90% | 95%+ ✅ |

## Database Performance

### Query Optimization

**1. Use Database Views**

Our evidence scoring uses materialized views for fast queries:

```sql
-- Already implemented
SELECT * FROM gene_evidence_summary WHERE symbol = 'PKD1';
-- Fast: Uses pre-computed view
```

**2. Index Strategy**

Key indexes already in place:
- `genes.symbol` (primary lookup)
- `genes.hgnc_id` (normalization)
- `annotations.gene_id` (joins)
- `gene_evidence.gene_id` (evidence queries)

**3. JSONB Queries**

Use GIN indexes for JSONB columns:

```sql
-- Efficient JSONB query
SELECT * FROM annotations
WHERE data @> '{"source": "clinvar"}';
```

### Connection Pooling

SQLAlchemy pool settings (production):

```python
# backend/app/core/database.py
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Concurrent connections
    max_overflow=20,       # Additional connections
    pool_pre_ping=True,    # Health check
    pool_recycle=3600      # Recycle after 1 hour
)
```

### Query Monitoring

```python
# Enable SQL logging (development only)
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Cache Performance

### L1 Cache (Memory)

**Configuration**:
```python
# backend/app/core/cache_service.py
L1_MAX_SIZE = 1000        # Number of items
L1_TTL = 300              # 5 minutes
```

**Optimization**:
- Keep hot data in L1
- Use appropriate TTLs
- Monitor eviction rate

### L2 Cache (PostgreSQL)

**Configuration**:
```python
# Per-namespace TTLs
CACHE_TTL = {
    "annotations": 3600,    # 1 hour
    "genes": 1800,          # 30 minutes
    "hgnc": 86400,          # 24 hours
    "clinvar": 3600,        # 1 hour
}
```

**Optimization**:
- Longer TTL for stable data
- Shorter TTL for dynamic data
- Clear on updates

### Cache Monitoring

```bash
# Via admin panel
http://localhost:5173/admin/cache

# Via API
curl http://localhost:8000/api/admin/cache/stats

# Check hit rates
# Target: >75% hit rate
```

### Cache Strategy

**1. Cache Annotations Aggressively**

```python
from app.core.cache_service import get_cache_service

@cache(namespace="annotations", ttl=3600)
async def fetch_annotation(gene_id: int):
    # Expensive operation
    return await external_api_call(gene_id)
```

**2. Invalidate on Updates**

```python
# After annotation update
await cache_service.clear_namespace("annotations")
```

**3. Pre-warming**

```python
# Pre-load hot data
for gene in hot_genes:
    await fetch_annotation(gene.id)  # Warms cache
```

## API Performance

### Non-Blocking Architecture

**Critical**: Never block the event loop

```python
# ❌ WRONG - Blocks event loop
def slow_sync_function():
    time.sleep(5)  # Blocks!
    return result

# ✅ CORRECT - Use thread pool
async def fast_async_function():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        slow_sync_function  # Runs in thread
    )
    return result
```

### Thread Pool Configuration

```python
# backend/app/services/annotation_pipeline.py
self._executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="pipeline"
)
```

**Sizing**:
- CPU-bound: `cpu_count()`
- I/O-bound: `cpu_count() * 2-4`
- Database: 4-8 workers

### Rate Limiting

External API calls use retry logic with backoff:

```python
from app.core.retry_utils import retry_with_backoff

@retry_with_backoff(
    max_retries=5,
    initial_delay=1.0,
    max_delay=60.0
)
async def api_call():
    return await client.get(url)
```

## Frontend Performance

### Bundle Size

```bash
# Analyze bundle
cd frontend
npm run build -- --report

# Target: <500KB gzipped
```

### Code Splitting

Already implemented:
```javascript
// Lazy load admin panel
const AdminPanel = () => import('./views/AdminPanel.vue')
```

### Image Optimization

- Use WebP format
- Lazy load images
- Responsive images

## Monitoring Performance

### Backend Metrics

```python
from app.core.logging import timed_operation

@timed_operation(warning_threshold_ms=1000)
async def slow_endpoint():
    # Logs warning if >1000ms
    result = await process()
    return result
```

### Database Queries

```python
from app.core.logging import database_query

@database_query(query_type="SELECT")
def fetch_genes():
    # Tracks query performance
    return db.query(Gene).all()
```

### Real-time Monitoring

```bash
# Watch logs for performance issues
tail -f backend/logs/app.log | grep -i "slow\|warning\|error"

# Check system resources
htop

# Monitor database
docker stats kidney-genetics-db-postgres-1
```

## Load Testing

### Setup

```bash
# Install locust
pip install locust

# Create test file
# tests/load/locustfile.py
```

### Run Load Tests

```bash
# Start load test
locust -f tests/load/locustfile.py

# Open UI
http://localhost:8089

# Set:
# Users: 100
# Spawn rate: 10/second
```

### Targets

- 100 concurrent users
- <100ms p50 response time
- <500ms p95 response time
- <1% error rate

## Optimization Checklist

### Database
- [ ] Indexes on frequently queried columns
- [ ] Materialized views for complex queries
- [ ] Connection pooling configured
- [ ] Query monitoring enabled
- [ ] EXPLAIN ANALYZE on slow queries

### Cache
- [ ] L1 + L2 cache strategy
- [ ] Appropriate TTLs per namespace
- [ ] >75% cache hit rate
- [ ] Clear cache on updates
- [ ] Monitor cache size

### API
- [ ] Thread pools for blocking operations
- [ ] No event loop blocking
- [ ] Retry logic on external APIs
- [ ] Rate limiting configured
- [ ] Response compression enabled

### Frontend
- [ ] Code splitting
- [ ] Lazy loading routes
- [ ] Bundle size optimized
- [ ] Images optimized
- [ ] CDN for static assets (production)

### Monitoring
- [ ] Performance logging enabled
- [ ] Slow query alerts
- [ ] Cache metrics tracked
- [ ] Error rate monitored
- [ ] Resource usage tracked

## Production Optimizations

### When Deploying to Production

**1. Enable Production Mode**

```bash
# .env
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
```

**2. Use Production Server**

```bash
# Use Gunicorn with Uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

**3. Enable Compression**

```python
# backend/app/main.py
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**4. Set Appropriate Cache Headers**

```python
@app.get("/api/genes")
async def get_genes(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    return genes
```

**5. Use CDN**

- Serve static files from CDN
- Use edge caching
- Enable HTTP/2

**6. Database Connection Pooling**

```python
# Production settings
pool_size=20
max_overflow=40
pool_recycle=1800
```

## Troubleshooting Performance Issues

### Slow Queries

```sql
-- Find slow queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
```

### High Memory Usage

```bash
# Check Python memory
py-spy top --pid <python-pid>

# Check cache size
# Admin panel → Cache Statistics
```

### Event Loop Blocking

```python
# Monitor event loop
import asyncio

async def monitor():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)  # Warns on blocking
```

## Resources

- [Architecture - Non-Blocking](../architecture/README.md#non-blocking-architecture)
- [Cache System](../features/caching-system.md)
- [Implementation Notes - Performance Fixes](../implementation-notes/completed/pipeline-performance-fixes.md)

---

**Last Updated**: September 2025
**Target Audience**: Developers, DevOps
**Maintained By**: Development Team