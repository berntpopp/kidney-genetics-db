# Unified Logging System

## Overview

The Kidney Genetics Database backend uses a comprehensive unified logging system that provides structured, searchable logs with both console and database persistence. This system replaces scattered `logging.getLogger()` calls with a consistent, enterprise-grade logging infrastructure.

## Architecture

### Core Components

1. **UnifiedLogger** (`app/core/logging/unified_logger.py`)
   - Drop-in replacement for Python's standard logger
   - Dual sync/async methods for different execution contexts
   - Automatic context binding for request correlation
   - Structured logging with JSON serialization

2. **DatabaseLogger** (`app/core/logging/database_logger.py`)
   - Async database persistence to `system_logs` table
   - JSONB storage for rich metadata
   - Automatic request correlation
   - Sub-5ms performance overhead

3. **LoggingMiddleware** (`app/middleware/logging_middleware.py`)
   - Automatic request/response lifecycle tracking
   - Unique request ID generation (UUID)
   - Performance metrics collection
   - Slow request detection

4. **Performance Monitoring** (`app/core/logging/performance.py`)
   - Decorators for operation timing
   - Automatic threshold-based alerting
   - Batch operation metrics
   - Database query monitoring

## Usage

### Basic Logging

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Async context
async def process_data():
    await logger.info("Processing started", item_count=100)
    await logger.warning("Rate limit approaching", remaining=10)
    await logger.error("Processing failed", error="Invalid data")

# Sync context
def sync_process():
    logger.sync_info("Processing started", item_count=100)
    logger.sync_warning("Rate limit approaching", remaining=10)
    logger.sync_error("Processing failed", error="Invalid data")
```

### Context Binding

```python
# Bind context for all subsequent logs
bound_logger = logger.bind(user_id=123, operation="data_import")
bound_logger.sync_info("Import started")  # Includes user_id and operation
```

### Performance Monitoring

```python
from app.core.logging import timed_operation, database_query, api_endpoint

@timed_operation(warning_threshold_ms=1000)
async def slow_operation():
    # Automatically logs if operation takes > 1 second
    await asyncio.sleep(2)

@database_query(query_type="SELECT")
def get_genes(db: Session):
    # Logs database query performance
    return db.query(Gene).all()

@api_endpoint(endpoint_name="list_genes")
async def list_genes_endpoint():
    # Tracks API endpoint response times
    return {"genes": await get_all_genes()}
```

### Performance Context Manager

```python
from app.core.logging import PerformanceMonitor

# Sync usage
with PerformanceMonitor("data_processing", batch_size=1000):
    process_large_dataset()

# Async usage
async with PerformanceMonitor("api_call", endpoint="external_service"):
    await call_external_api()
```

## Database Schema

The `system_logs` table stores all log entries:

```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    level VARCHAR(20) NOT NULL,
    source VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    request_id UUID,
    user_id INTEGER,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_source ON system_logs(source);
CREATE INDEX idx_system_logs_request_id ON system_logs(request_id);
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX idx_system_logs_extra_data ON system_logs USING gin(extra_data);
```

## Administrative API

### Query Logs
```http
GET /api/admin/logs/?level=ERROR&limit=100
```

Parameters:
- `level`: Filter by log level (INFO, WARNING, ERROR)
- `source`: Filter by source module
- `request_id`: Filter by request ID
- `start_time`: Start time for date range
- `end_time`: End time for date range
- `limit`: Maximum results (1-1000)
- `offset`: Pagination offset

### Log Statistics
```http
GET /api/admin/logs/statistics?hours=24
```

Returns:
- Level distribution (counts by level)
- Top sources (most active modules)
- Error timeline (hourly error rates)
- Storage metrics

### Cleanup Old Logs
```http
DELETE /api/admin/logs/cleanup?days=30
```

Removes logs older than specified days to manage storage.

## Configuration

Configure the logging system in `app/main.py`:

```python
from app.core.logging import configure_logging

# Configure at application startup
configure_logging(
    log_level="INFO",           # Minimum log level
    database_enabled=True,      # Enable database persistence
    console_enabled=True        # Enable console output
)
```

Environment variables:
- `LOG_LEVEL`: Default log level (DEBUG, INFO, WARNING, ERROR)
- `LOG_DATABASE_ENABLED`: Enable/disable database logging
- `LOG_CONSOLE_ENABLED`: Enable/disable console logging

## Best Practices

1. **Use Structured Logging**
   ```python
   # Good - structured data
   logger.sync_info("User action", user_id=123, action="login", ip="192.168.1.1")
   
   # Avoid - unstructured strings
   logger.sync_info(f"User 123 logged in from 192.168.1.1")
   ```

2. **Choose Appropriate Log Levels**
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages for potential issues
   - `ERROR`: Error messages for failures

3. **Use Performance Decorators**
   ```python
   @timed_operation(warning_threshold_ms=500)
   async def critical_operation():
       # Automatically monitored
       pass
   ```

4. **Avoid Logging Sensitive Data**
   ```python
   # Good - log user ID
   logger.sync_info("Authentication", user_id=user.id)
   
   # Avoid - don't log passwords or tokens
   logger.sync_info("Auth", password=password)  # NEVER DO THIS
   ```

5. **Use Context Binding for Request Tracking**
   ```python
   # In API endpoints
   bound_logger = logger.bind(request_id=request_id, user_id=current_user.id)
   bound_logger.sync_info("Processing request")
   ```

## Migration from Standard Logging

The unified logger is a drop-in replacement:

```python
# Old code
import logging
logger = logging.getLogger(__name__)
logger.info("Processing started")

# New code
from app.core.logging import get_logger
logger = get_logger(__name__)
logger.sync_info("Processing started")  # For sync contexts
# or
await logger.info("Processing started")  # For async contexts
```

## Performance Considerations

- Database logging is asynchronous (non-blocking)
- Console logging is synchronous but fast
- Average overhead: < 5ms per log entry
- Automatic batching for high-volume scenarios
- Request correlation adds minimal overhead (UUID generation)

## Troubleshooting

### Circular Import Errors
The logging system uses lazy imports to avoid circular dependencies. If you encounter circular imports:

1. Check that performance.py uses lazy loading
2. Ensure admin_logs.py doesn't import logging
3. Use lazy imports in health.py and maintenance.py

### Database Connection Issues
If database logging fails:
1. System continues with console logging only
2. Check database connectivity
3. Verify system_logs table exists
4. Run migrations: `alembic upgrade head`

### Performance Impact
Monitor logging overhead:
1. Check slow request logs in LoggingMiddleware
2. Review performance metrics in admin API
3. Adjust LOG_LEVEL if needed
4. Consider disabling database logging for high-throughput scenarios

## Examples

### Complete API Endpoint with Logging

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import get_logger, api_endpoint, database_query

router = APIRouter()
logger = get_logger(__name__)

@router.get("/genes/{gene_id}")
@api_endpoint(endpoint_name="get_gene")
async def get_gene(gene_id: int, db: Session = Depends(get_db)):
    """Get gene by ID with comprehensive logging."""
    
    # Log request
    await logger.info("Gene requested", gene_id=gene_id)
    
    # Database query with automatic timing
    @database_query(query_type="SELECT")
    def fetch_gene():
        return db.query(Gene).filter(Gene.id == gene_id).first()
    
    gene = fetch_gene()
    
    if not gene:
        await logger.warning("Gene not found", gene_id=gene_id)
        raise HTTPException(status_code=404, detail="Gene not found")
    
    await logger.info("Gene retrieved successfully", 
                     gene_id=gene_id, 
                     symbol=gene.approved_symbol)
    
    return gene
```

### Batch Processing with Progress Tracking

```python
from app.core.logging import get_logger, batch_operation

logger = get_logger(__name__)

@batch_operation(
    batch_name="gene_import",
    batch_size_getter=lambda genes, **_: len(genes)
)
async def import_genes(genes: list[dict]):
    """Import genes with automatic batch metrics."""
    
    for i, gene in enumerate(genes):
        if i % 100 == 0:  # Log progress every 100 items
            await logger.info("Import progress", 
                            processed=i, 
                            total=len(genes),
                            percentage=round(i/len(genes)*100, 2))
        
        await process_gene(gene)
    
    return {"imported": len(genes)}
```

## Related Documentation

- [Setup Guide](setup-guide.md) - Initial environment setup
- [Hybrid Development](hybrid-development.md) - Development workflow
- [API Documentation](/docs) - FastAPI auto-generated docs