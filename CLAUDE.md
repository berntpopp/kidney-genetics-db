# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kidney-Genetics Database**: A modern web platform for curating and exploring kidney disease-related genes. This project modernizes the original R-based pipeline into a scalable Python/FastAPI + Vue.js architecture with PostgreSQL backend.

**Current Status**: Alpha version (v0.1.0) - Core functionality fully operational
- **571+ genes** with comprehensive annotations from 9 sources
- **Unified systems** for logging, caching, and retry logic (MUST be reused)
- **Admin panel** with user management, cache control, and pipeline management
- **Performance**: <10ms cached response times, 95%+ annotation coverage

## 🚨 CRITICAL: Development Principles

### DRY (Don't Repeat Yourself)
**NEVER recreate existing functionality.** We have robust, tested systems for:
- **Logging**: Use `UnifiedLogger` - DO NOT use `print()` or `logging.getLogger()`
- **Caching**: Use `CacheService` - DO NOT create new cache implementations
- **Retry Logic**: Use `retry_with_backoff` - DO NOT write custom retry loops
- **HTTP Clients**: Use `RetryableHTTPClient` - DO NOT use raw httpx/requests

### KISS (Keep It Simple, Stupid)
- Use existing patterns and utilities
- Prefer configuration over code
- Leverage PostgreSQL features (JSONB, views) over complex application logic
- Use Make commands for all operations

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
- `docs/` - Architecture documentation and implementation guides
- `scrapers/` - Data scraping utilities for diagnostic panels
- `backups/` - Database and migration backups

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

### Backend (Python/FastAPI)
```bash
make lint     # Lint with ruff (100-char line length)
make test     # Run pytest test suite
cd backend && uv run ruff check app/ --fix
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

## Logging System

### Overview
The backend uses a unified structured logging system that replaces scattered `logging.getLogger()` calls with a consistent, enterprise-grade infrastructure. Features include:
- **Dual output**: Console (sync) + Database (async) persistence
- **Request correlation**: Unique UUIDs for tracking across API calls
- **Performance monitoring**: Decorators for operation timing
- **Administrative API**: Endpoints for log management at `/api/admin/logs/`

### Usage
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Async context
await logger.info("Operation started", user_id=123)

# Sync context  
logger.sync_info("Operation completed", duration_ms=456)

# Performance monitoring
from app.core.logging import timed_operation

@timed_operation(warning_threshold_ms=1000)
async def slow_operation():
    await process_data()
```

### Key Components
- **UnifiedLogger**: Drop-in replacement for standard Python logging
- **DatabaseLogger**: Async persistence to `system_logs` table with JSONB
- **LoggingMiddleware**: Automatic request/response lifecycle tracking
- **Performance decorators**: `@timed_operation`, `@database_query`, `@api_endpoint`

### Administrative Endpoints
- `GET /api/admin/logs/` - Query and filter system logs
- `GET /api/admin/logs/statistics` - View log statistics and error rates
- `DELETE /api/admin/logs/cleanup` - Manage log retention

For detailed logging documentation, see [docs/development/logging-system.md](docs/development/logging-system.md)

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

## Summary: Key Systems to Reuse

### ✅ ALWAYS USE
1. **UnifiedLogger** (`app.core.logging`) - Structured logging with correlation
2. **CacheService** (`app.core.cache_service`) - Multi-layer caching
3. **retry_with_backoff** (`app.core.retry_utils`) - Exponential backoff retry
4. **RetryableHTTPClient** (`app.core.retry_utils`) - HTTP with retry/circuit breaker
5. **BaseAnnotationSource** (`app.pipeline.sources.annotations.base`) - For new sources
6. **Alembic migrations** - For database schema changes
7. **Make commands** - For all development operations

### ❌ NEVER CREATE
- Custom cache implementations (use CacheService)
- Custom retry loops (use retry_with_backoff)
- Raw HTTP clients (use RetryableHTTPClient)
- Direct database schema modifications (use Alembic)
- Console.log/print statements (use UnifiedLogger)
- New annotation sources from scratch (extend BaseAnnotationSource)

### 📊 Current System Metrics
- **Annotation Coverage**: 95%+ (up from 22% after implementing retry logic)
- **Cache Hit Rate**: 75-95% with unified cache
- **Response Times**: <10ms cached, <50ms uncached
- **Code Reduction**: 50% after cache consolidation
- **Error Rate**: <0.1% with retry and circuit breaker

### 📚 Documentation References
- Full documentation: `docs/` directory
- Project status: `docs/PROJECT_STATUS.md`
- Feature docs: `docs/features/`
- Implementation details: `docs/implementation/`

Remember: **DRY + KISS = Success**. Use what exists, configure don't code, and keep it simple!