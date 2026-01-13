# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kidney-Genetics Database**: A modern web platform for curating and exploring kidney disease-related genes. This project modernizes the original R-based pipeline into a scalable Python/FastAPI + Vue.js architecture with PostgreSQL backend.

**Current Status**: Production-ready Alpha (v0.1.0)
- **571+ genes** with comprehensive annotations from 9 sources
- **Unified systems** for logging, caching, and retry logic (MUST be reused)
- **Admin panel** with user management, cache control, and pipeline management
- **Performance**: <10ms cached response times, 95%+ annotation coverage (verified in production)
- **Non-blocking architecture**: Event loop never blocks, all heavy operations use thread pools

## 🚨 CRITICAL: Development Principles

### DRY (Don't Repeat Yourself)
**NEVER recreate existing functionality.** We have robust, tested systems for:
- **Logging**: Use `UnifiedLogger` - DO NOT use `print()` or `logging.getLogger()`
- **Caching**: Use `CacheService` - DO NOT create new cache implementations
- **Retry Logic**: Use `retry_with_backoff` - DO NOT write custom retry loops
- **HTTP Clients**: Use `RetryableHTTPClient` - DO NOT use raw httpx/requests
- **Base Classes**: Extend `BaseAnnotationSource` for new annotation sources

### KISS (Keep It Simple, Stupid)
- Use existing patterns and utilities
- Prefer configuration over code (see `datasource_config`)
- Leverage PostgreSQL features (JSONB, views) over complex application logic
- Use Make commands for all operations
- Thread pools over complex async migrations for blocking operations

### Modularization & Reusability
- **Inheritance hierarchy**: All annotation sources inherit from `BaseAnnotationSource`
- **Composition**: Services composed from smaller utilities (cache + retry + logging)
- **Dependency injection**: Services passed as parameters, not hardcoded
- **Configuration-driven**: Behavior controlled by config files, not code changes

### Non-Blocking Architecture
- **Async/await throughout**: FastAPI endpoints and pipeline operations are async
- **Thread pools for sync operations**: Database operations that block use `ThreadPoolExecutor`
- **Event loop protection**: Never block the event loop (target: <5ms blocking)
- **WebSocket stability**: Real-time updates without disconnections during heavy processing

### 🚨 Pipeline Operations: ALWAYS Use the API
**NEVER run annotation pipelines via manual Python scripts.** Always use the REST API endpoints:
- **Update missing annotations**: `POST /api/annotations/pipeline/update-missing/{source_name}`
- **Full pipeline update**: `POST /api/annotations/pipeline/update`
- **Update failed genes**: `POST /api/annotations/pipeline/update-failed`
- **Update new genes**: `POST /api/annotations/pipeline/update-new`
- **Check status**: `GET /api/annotations/pipeline/status`

These endpoints handle proper session management, connection pooling, progress tracking, and error recovery. Manual scripts cause connection pool exhaustion and session state issues.

## Project Architecture

### Core Components (Implemented)
- **Backend**: FastAPI with PostgreSQL, hybrid relational + JSONB architecture, UV package manager
- **Frontend**: Vue 3 + Vite with Vuetify for Material Design
- **Database**: PostgreSQL 14+ with automated migrations via Alembic
- **Pipeline**: Python-based data ingestion with sources (PanelApp, HPO, ClinGen, PubTator, etc.)
- **Development**: Make-based workflow with hybrid Docker/local development

### Key Directories
- `backend/` - FastAPI application with data pipeline and models
- `frontend/` - Vue.js/Vuetify web interface
- `docs/` - Comprehensive documentation (see Documentation Structure below)
- `scrapers/` - Data scraping utilities for diagnostic panels
- `backups/` - Database and migration backups

## Documentation Structure

**Complete documentation is in `docs/` - organized by role and purpose:**

- **[Getting Started](docs/getting-started/)** - Quick start, installation, development workflow
- **[Guides](docs/guides/)** - By role (developer, administrator, deployment)
- **[Architecture](docs/architecture/)** - System design (backend, frontend, database, data-sources)
- **[Features](docs/features/)** - Feature documentation (annotations, scoring, caching, auth)
- **[API](docs/api/)** - REST API reference and WebSocket documentation
- **[Reference](docs/reference/)** - Technical references (config, logging, style guide)
- **[Implementation Notes](docs/implementation-notes/)** - Development notes (completed, active, planning)
- **[Troubleshooting](docs/troubleshooting/)** - Common issues, fixes, performance tuning
- **[Project Management](docs/project-management/)** - Status, releases, roadmap
- **[Archive](docs/archive/)** - Historical documentation

**Key Documentation Files:**
- [Main Documentation](docs/README.md) - Entry point with role-based navigation
- [Quick Start](docs/getting-started/quick-start.md) - 5-minute setup guide
- [Developer Setup](docs/guides/developer/setup-environment.md) - Complete environment setup
- [Architecture Overview](docs/architecture/README.md) - System design principles
- [Project Status](docs/project-management/status.md) - Current state and metrics

## Development Commands

**IMPORTANT: Always use make commands for development. Do not run services directly.**

### Quick Start - Hybrid Mode (Recommended)
```bash
# Start database in Docker, API/Frontend locally
make hybrid-up

# Then in separate terminals:
make backend   # Start backend API
make frontend  # Start frontend dev server

# Stop everything
make hybrid-down
```

### Full Docker Development
```bash
# Start all services in Docker
make dev-up

# View logs
make dev-logs

# Stop services
make dev-down
```

### Database Management
```bash
# Complete reset (structure + data)
make db-reset

# Clean data only (keep structure)
make db-clean
```

### Monitoring & Maintenance
```bash
# Show system status
make status

# Complete cleanup
make clean-all
```

### Available Make Commands
```bash
make help  # Show all available commands
```

**Key Commands:**
- `make hybrid-up` / `make hybrid-down` - Hybrid development mode
- `make backend` / `make frontend` - Start services locally
- `make dev-up` / `make dev-down` - Full Docker mode
- `make db-reset` - Reset database completely
- `make status` - Check system status


## High-Level Architecture

### Database Design (Hybrid Architecture)
The database uses a hybrid PostgreSQL design combining:
- **Relational columns** for core metrics (fast queries on evidence scores, classification)
- **JSONB columns** for detailed evidence data
- **Gene staging system** for two-stage data ingestion
- **Audit trail** via gene_staging table for normalization attempts

### Data Flow
1. **Data Sources** → Multiple APIs (PanelApp, HPO, ClinGen, GenCC, PubTator) + Diagnostic Panel Scrapers
2. **Staging** → Raw data ingested into gene_staging table with normalization logging
3. **Processing** → Evidence aggregation and scoring algorithms
4. **Storage** → Final curated data in PostgreSQL with computed scores
5. **API** → FastAPI serves JSON:API compliant endpoints
6. **Frontend** → Vue.js interface with real-time progress updates

### Key Features
- **Multi-source data aggregation** from 6+ genomic databases
- **Evidence scoring engine** with weighted calculations
- **Gene staging system** for data validation and normalization
- **Real-time progress tracking** via WebSocket connections
- **REST API** with JSON:API compliant endpoints

## Important Implementation Notes

### Schema Management
- All schema changes go through Alembic migrations (`backend/alembic/versions/`)
- Database views managed via `app.db.views` module with dependency tracking
- Single consolidated migration approach (squashed from 16 previous migrations)
- Use `make db-reset` for complete schema refresh
- Automated backup system via `make db-backup-full`

### Data Pipeline Architecture
Active pipeline implementation in `backend/app/pipeline/sources/unified/`:
- **Base classes**: `base.py` - common data source interface
- **PanelApp**: `panelapp.py` - UK/Australia gene panels
- **HPO**: `hpo.py` - Human Phenotype Ontology integration
- **ClinGen**: `clingen.py` - Clinical Genome Resource
- **GenCC**: `gencc.py` - Gene Curation Coalition
- **PubTator**: `pubtator.py` - Literature mining
- **Diagnostic Panels**: `diagnostic_panels.py` - Commercial panel scraping

Additional components:
- `scrapers/` - Standalone web scraping for diagnostic panels
- Evidence aggregation and scoring in `backend/app/pipeline/aggregate.py`

## Code Quality and Testing

### 🚨 CRITICAL: Commit Requirements
**ALL code must pass lint, typecheck, and tests BEFORE committing.** Never skip these checks or assume issues are "pre-existing":
- **Backend**: Run `make lint` + `uv run mypy <files> --ignore-missing-imports` on all modified files
- **Frontend**: Run `npm run lint` on all modified files
- **Tests**: Run `make test` to verify no regressions
- **Fix ALL warnings**: Even in files you didn't originally create - we maintain clean code throughout
- **No exceptions**: Do not commit code with lint errors, type errors, or failing tests

### Backend (Python/FastAPI)
```bash
make lint     # Lint with ruff (100-char line length)
make test     # Run pytest test suite
cd backend && uv run ruff check app/ --fix
cd backend && uv run mypy <file.py> --ignore-missing-imports  # Typecheck modified files
cd backend && uv run pytest -v
```

### Frontend (Vue.js/Vite)
```bash
cd frontend && npm run lint      # ESLint + Prettier
cd frontend && npm run format    # Format code
```

### Package Management
- **Backend**: Uses UV package manager (not pip/poetry)
- **Frontend**: Uses npm standard package management

## Testing

### Backend Testing (Limited)
- Basic unit tests for gene normalization and HGNC client
- Run with: `make test` or `cd backend && uv run pytest -v`
- Test files in `backend/tests/`

### Frontend Testing
- No testing framework currently configured
- Linting and formatting via ESLint and Prettier

### Current Test Coverage
- Minimal test coverage (4 test files total)
- Focus on core gene normalization functionality

## External Dependencies

### APIs and Data Sources (Implemented)
- **PanelApp API**: Gene panel data (UK and Australia)
- **HPO API**: Human Phenotype Ontology
- **PubTator API**: Literature mining
- **ClinGen API**: Clinical Genome Resource data
- **GenCC API**: Gene Curation Coalition data
- **OMIM references**: Disease ID mapping only (not full integration)

### Configuration
- Environment variables for API keys and database credentials
- YAML configuration for diagnostic panel scrapers (`scrapers/diagnostics/config/config.yaml`)
- Basic Docker Compose setup (not production-ready)

## Backend Architecture Details

### API Structure
- **Main entry**: `backend/app/main.py` - FastAPI application setup
- **Endpoints**: `backend/app/api/endpoints/` - REST API routes
- **Models**: `backend/app/models/` - SQLAlchemy database models
- **CRUD**: `backend/app/crud/` - database operations
- **Core**: `backend/app/core/` - shared utilities and services

### Key Features
- **Gene Staging**: Two-stage data ingestion (staging → curated)
- **Evidence Scoring**: Configurable weighted scoring system
- **Progress Tracking**: Real-time WebSocket updates for long-running tasks
- **Caching**: HTTP response caching via `hishel` library
- **Background Tasks**: Async task processing for data updates
- **Unified Logging**: Comprehensive structured logging system with dual output

## Unified System Architecture

### Layered Architecture Pattern
The codebase follows a strict layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)          │  ← JSON:API compliant REST endpoints
├─────────────────────────────────────┤
│      Business Logic (Services)       │  ← Annotation pipeline, scoring engine
├─────────────────────────────────────┤
│     Core Utilities (Shared)          │  ← Cache, Retry, Logging (MUST REUSE)
├─────────────────────────────────────┤
│       Data Access (CRUD/ORM)         │  ← SQLAlchemy models and operations
├─────────────────────────────────────┤
│      Database (PostgreSQL)           │  ← Hybrid relational + JSONB storage
└─────────────────────────────────────┘
```

### Performance Architecture
```
Request → FastAPI (async) → Thread Pool (for sync DB ops) → PostgreSQL
           ↓                      ↓
        WebSocket            Never blocks event loop
        (real-time)          (<5ms target latency)
```

## Logging System (MUST USE)

### Overview
**Unified structured logging** - Never use print() or logging.getLogger()!
- **Dual output**: Console (sync) + Database (async) persistence
- **Request correlation**: Automatic UUID tracking across all operations
- **Performance monitoring**: Built-in decorators for timing
- **Context binding**: Immutable context pattern like structlog

### Usage - Always Use These Patterns
```python
# CORRECT - Using unified logger
from app.core.logging import get_logger

logger = get_logger(__name__)

# Async context (preferred in async functions)
await logger.info("Operation started", user_id=123)

# Sync context (for sync functions)
logger.sync_info("Operation completed", duration_ms=456)

# Context binding for correlated logs
bound_logger = logger.bind(request_id=uuid, user_id=123)
bound_logger.sync_info("All logs will include request_id and user_id")

# WRONG - Don't use standard logging
import logging  # NO!
print("Debug info")  # NO!
logging.getLogger(__name__)  # NO!
```

### Performance Monitoring
```python
from app.core.logging import timed_operation, database_query, api_endpoint

@timed_operation(warning_threshold_ms=1000)
async def slow_operation():
    # Automatically logs if >1000ms
    await process_data()

@database_query(query_type="SELECT")
def fetch_genes():
    # Tracks DB query performance
    return db.query(Gene).all()
```

### Key Components
- **UnifiedLogger**: Drop-in replacement with sync/async methods
- **DatabaseLogger**: Async persistence to `system_logs` table
- **LoggingMiddleware**: Request lifecycle tracking
- **Performance decorators**: Automatic timing and alerting

For detailed logging documentation, see [docs/reference/logging-system.md](docs/reference/logging-system.md)

## Caching System (MUST USE)

### Overview
**Unified multi-layer cache system** - Never create new cache implementations!
- **L1 Cache**: In-memory LRU (process-local, <10ms)
- **L2 Cache**: PostgreSQL JSONB (persistent, shared)
- **Single source of truth**: `app/core/cache_service.py`

### Usage - Always Use These Patterns
```python
# CORRECT - Using unified cache service
from app.core.cache_service import get_cache_service

cache = get_cache_service(db_session)
await cache.set("key", value, namespace="annotations", ttl=3600)
value = await cache.get("key", namespace="annotations")

# WRONG - Don't create new cache implementations
my_cache = {}  # NO!
redis_cache = Redis()  # NO!
```

### Cache Decorator Pattern
```python
from app.core.cache_decorator import cache

@cache(namespace="annotations", ttl=3600)
async def expensive_operation(gene_id: int):
    return fetch_data(gene_id)
```

### Key Components
- **CacheService**: Main service class with L1/L2 layers
- **get_cache_service()**: Factory function to get cache instance
- **Namespaces**: Use existing ones (annotations, hgnc, clinvar, etc.)
- **TTLs**: Configured per namespace, don't hardcode

## Retry Logic (MUST USE)

### Overview
**Advanced retry system with exponential backoff** - Never write custom retry loops!
- **Location**: `app/core/retry_utils.py`
- **Features**: Exponential backoff, jitter, circuit breaker, rate limit handling

### Usage - Always Use These Patterns
```python
# CORRECT - Using retry utilities
from app.core.retry_utils import retry_with_backoff, RetryConfig, CircuitBreaker

# Simple retry with defaults
@retry_with_backoff()
async def api_call():
    return await client.get(url)

# Custom configuration
config = RetryConfig(
    max_retries=5,
    initial_delay=1.0,
    max_delay=60.0,
    retry_on_status_codes=(429, 500, 502, 503, 504)
)

@retry_with_backoff(config=config)
async def robust_api_call():
    return await client.get(url)

# WRONG - Don't write custom retry loops
for i in range(5):  # NO!
    try:
        result = api_call()
    except:
        time.sleep(i * 2)  # NO!
```

### HTTP Client with Retry
```python
# CORRECT - Using RetryableHTTPClient
from app.core.retry_utils import RetryableHTTPClient

client = RetryableHTTPClient(
    client=httpx.AsyncClient(),
    retry_config=RetryConfig(max_retries=5),
    circuit_breaker=CircuitBreaker()
)

# WRONG - Don't use raw httpx
client = httpx.AsyncClient()  # NO! Use RetryableHTTPClient
```

### Key Components
- **RetryConfig**: Configuration for retry behavior
- **CircuitBreaker**: Prevents calls to failing services
- **retry_with_backoff**: Decorator for any function
- **RetryableHTTPClient**: HTTP client with built-in retry

## Annotation Sources (REUSE BASE CLASS)

### Overview
All annotation sources MUST inherit from `BaseAnnotationSource` which provides:
- Caching (via CacheService)
- Retry logic (via retry_utils)
- Rate limiting
- Progress tracking
- Error handling

### Creating New Annotation Source
```python
# CORRECT - Extend base class
from app.pipeline.sources.annotations.base import BaseAnnotationSource

class NewAnnotationSource(BaseAnnotationSource):
    source_name = "new_source"
    cache_ttl_days = 7
    requests_per_second = 5.0
    
    async def fetch_annotation(self, gene: Gene):
        # Base class handles caching, retry, rate limiting
        return await self._make_api_call(gene)

# WRONG - Don't create from scratch
class NewSource:  # NO! Always extend BaseAnnotationSource
    def __init__(self):
        self.cache = {}  # NO! Base class handles this
```

## Database Patterns (USE EXISTING)

### Migrations
```bash
# CORRECT - Use Alembic migrations
alembic revision --autogenerate -m "Add new column"
alembic upgrade head

# WRONG - Don't modify schema directly
ALTER TABLE genes ADD COLUMN...  # NO!
```

### JSONB Storage
```python
# CORRECT - Store complex data in JSONB
annotations = Column(JSONB)  # Flexible, queryable

# WRONG - Don't create many columns
pathogenic_count = Column(Integer)  # NO!
likely_pathogenic = Column(Integer)  # NO!
# Use JSONB instead
```

## Frontend Patterns (USE EXISTING)

### API Client
```javascript
// CORRECT - Use existing API service
import api from '@/services/api'
const data = await api.get('/genes')

// WRONG - Don't use fetch directly
fetch('/api/genes')  // NO!
```

### State Management
```javascript
// CORRECT - Use Pinia stores
import { useGenesStore } from '@/stores/genes'
const store = useGenesStore()

// WRONG - Don't use component state for shared data
data() { return { genes: [] } }  // NO for shared data!
```

## Security Notes

- JWT authentication with role-based access (Admin, Curator, Public)
- Bcrypt password hashing with salt (12 rounds)
- Environment-based configuration for secrets
- Never commit secrets or API keys to repository
- Structured logging automatically filters sensitive data
- Public access for all GET endpoints (no auth required for reading)

## Non-Blocking Patterns (CRITICAL)

### Problem: SQLAlchemy sync DB operations block the event loop
The database uses synchronous SQLAlchemy (not async), which would block FastAPI's event loop. The solution: **ThreadPoolExecutor** for all heavy DB operations.

### Pattern: Thread Pool for Blocking Operations
```python
# CORRECT - Non-blocking pattern for sync operations
import asyncio
from concurrent.futures import ThreadPoolExecutor

class Service:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def heavy_operation(self):
        loop = asyncio.get_event_loop()
        # Run sync operation in thread pool
        result = await loop.run_in_executor(
            self._executor,
            self._sync_heavy_operation
        )
        return result

    def _sync_heavy_operation(self):
        # This runs in a thread, doesn't block event loop
        db.execute(text("REFRESH MATERIALIZED VIEW"))
        return "done"

# WRONG - Blocks the event loop
async def bad_operation():
    db.execute(text("REFRESH MATERIALIZED VIEW"))  # BLOCKS!
```

### Real Examples from Codebase
```python
# Cache invalidation without blocking (annotation_pipeline.py)
await loop.run_in_executor(
    self._executor,
    cache_service.clear_namespace_sync,  # Sync method in thread
    "annotations"
)

# Database ping to keep connection alive
self.db.execute(text("SELECT 1"))  # Quick operation, acceptable

# View refresh without blocking
await loop.run_in_executor(
    self._executor,
    self._refresh_views_sync
)
```

## Database Architecture Decision: Hybrid Sync Pattern

### Why Sync SQLAlchemy + ThreadPoolExecutor?

We deliberately chose **sync SQLAlchemy with ThreadPoolExecutor** over async SQLAlchemy because:

1. **Simpler and more mature** - Easier to debug, better ecosystem support
2. **FastAPI explicitly recommends this** for single-database applications
3. **Production-proven** - Metrics show <1ms event loop blocking
4. **Cost-effective** - Async SQLAlchemy would add 60+ hours of work for <10% gain

This architectural decision was validated by:
- [FastAPI Concurrency Guide](https://fastapi.tiangolo.com/async/)
- Production metrics showing <1ms event loop blocking
- Industry best practices for hybrid async/sync architectures

### When to Use Thread Pool Offloading

| Query Time | Pattern | Example |
|------------|---------|---------|
| <10ms | Direct sync call | `db.query(Gene).filter_by(id=1).first()` |
| 10-50ms | Consider offloading | Complex JOINs with small result sets |
| 50-100ms | Should offload | `await run_in_threadpool(heavy_query)` |
| >100ms | MUST offload | `await loop.run_in_executor(executor, long_query)` |

**Monitoring**: Use `log_slow_query()` (threshold: 50ms) to identify queries that need offloading.

### Code Examples

#### ✅ CORRECT: Simple query (no offloading needed)
```python
@router.get("/genes/{gene_id}")
async def get_gene(gene_id: int, db: Session = Depends(get_db)):
    # Simple indexed lookup - <10ms
    gene = db.query(Gene).filter_by(id=gene_id).first()
    return gene
```

#### ✅ CORRECT: Heavy query (offload to thread pool)
```python
from starlette.concurrency import run_in_threadpool

@router.get("/heavy-stats")
async def get_heavy_stats(db: Session = Depends(get_db)):
    # Complex aggregation - >50ms
    def compute_stats():
        return db.execute(text("""
            SELECT source_name, COUNT(*), AVG(score)
            FROM gene_evidence
            GROUP BY source_name
            ORDER BY COUNT(*) DESC
        """)).fetchall()

    result = await run_in_threadpool(compute_stats)
    return result
```

#### ❌ WRONG: Blocking file I/O in async function
```python
# BAD - Blocks event loop
async def load_data(self):
    with open("data.csv") as f:  # ❌ BLOCKS
        data = f.read()

# GOOD - Non-blocking
async def load_data(self):
    def read_file():
        with open("data.csv") as f:
            return f.read()

    data = await asyncio.to_thread(read_file)  # ✅ NON-BLOCKING
```

#### ✅ CORRECT: Using monitor_blocking decorator
```python
from app.core.logging import monitor_blocking

@monitor_blocking(threshold_ms=10.0)
async def potentially_slow_operation():
    # If this takes >10ms, a warning will be logged with recommendations
    result = await some_operation()
    return result
```

### Performance Targets

- **Event loop blocking:** <5ms (current: <1ms ✅)
- **Simple query latency:** <10ms (current: 7-13ms ✅)
- **Cache hit rate:** >70% (current: 75-95% ✅)
- **WebSocket stability:** 100% uptime during heavy processing ✅

### References

- [FastAPI Concurrency Guide](https://fastapi.tiangolo.com/async/)
- Production metrics: See `docs/implementation-notes/active/sync_async_fixes.md`
- Expert review: See `docs/implementation-notes/active/` (archived after implementation)

## Summary: Key Systems to Reuse

### ✅ ALWAYS USE
1. **UnifiedLogger** (`app.core.logging`) - Structured logging with correlation
2. **CacheService** (`app.core.cache_service`) - Multi-layer caching
3. **retry_with_backoff** (`app.core.retry_utils`) - Exponential backoff retry
4. **RetryableHTTPClient** (`app.core.retry_utils`) - HTTP with retry/circuit breaker
5. **BaseAnnotationSource** (`app.pipeline.sources.annotations.base`) - For new sources
6. **ThreadPoolExecutor** - For sync DB operations in async context
7. **Alembic migrations** - For database schema changes
8. **Make commands** - For all development operations

### ❌ NEVER CREATE/DO
- Custom cache implementations (use CacheService)
- Custom retry loops (use retry_with_backoff)
- Raw HTTP clients (use RetryableHTTPClient)
- Direct database schema modifications (use Alembic)
- Console.log/print statements (use UnifiedLogger)
- New annotation sources from scratch (extend BaseAnnotationSource)
- Blocking operations in async functions (use ThreadPoolExecutor)
- Sync database calls without thread pool (will block event loop)

### 📊 Production-Verified Metrics
- **Event Loop Blocking**: <1ms (eliminated with thread pools)
- **API Response During Pipeline**: 7-13ms (was 5-10 seconds)
- **WebSocket Stability**: 100% uptime during heavy processing
- **Annotation Coverage**: 95%+ (retry logic fixed coverage issues)
- **Cache Hit Rate**: 75-95% with unified L1/L2 cache
- **Code Reduction**: 50% after consolidation
- **Error Rate**: <0.1% with circuit breaker

### 📚 Documentation References
- Logging system: `docs/reference/logging-system.md`
- Design system (UI/UX): `docs/reference/design-system.md`
- Performance fixes: `docs/implementation-notes/completed/pipeline-performance-fixes.md`
- Cache refactor: `docs/implementation-notes/completed/cache-refactor.md`
- Project status: `docs/project-management/status.md`
- Architecture: `docs/architecture/README.md`
- Developer guides: `docs/guides/developer/`
- Troubleshooting: `docs/troubleshooting/common-issues.md`

Remember: **DRY + KISS + Non-blocking = Success**. Use what exists, configure don't code, never block the event loop!