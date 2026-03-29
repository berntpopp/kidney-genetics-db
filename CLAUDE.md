# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kidney-Genetics Database**: A modern web platform for curating and exploring kidney disease-related genes. Python/FastAPI + Vue.js architecture with PostgreSQL backend.

**Current Status**: v0.2.0 (Frontend migrated from JS+Vuetify to TS+Tailwind+shadcn-vue)
- 5,080+ genes with comprehensive annotations from 17 sources
- Unified systems for logging, caching, and retry logic (MUST be reused)
- Admin panel with user management, cache control, and pipeline management
- Non-blocking architecture: event loop never blocks, all heavy operations use thread pools

## CRITICAL: Development Principles

### DRY - NEVER Recreate Existing Functionality
- **Logging**: Use `UnifiedLogger` from `app.core.logging` - NOT `print()` or `logging.getLogger()`
- **Caching**: Use `CacheService` from `app.core.cache_service` - NOT custom cache dicts
- **Retry Logic**: Use `retry_with_backoff` from `app.core.retry_utils` - NOT custom retry loops
- **HTTP Clients**: Use `RetryableHTTPClient` from `app.core.retry_utils` - NOT raw httpx/requests
- **Annotation Sources**: Extend `BaseAnnotationSource` - NOT from scratch

### KISS
- Prefer configuration over code (YAML-based `datasource_config` with `KG_` env prefix)
- Leverage PostgreSQL features (JSONB, views, materialized views)
- Use Make commands for all operations
- Thread pools over complex async migrations for blocking operations

### Pipeline Operations: ALWAYS Use the API
**NEVER run annotation pipelines via manual Python scripts.** Always use REST API endpoints:
- `POST /api/annotations/pipeline/update-missing/{source_name}` - Update missing
- `POST /api/annotations/pipeline/update` - Full pipeline update
- `POST /api/annotations/pipeline/update-failed` - Update failed genes
- `GET /api/annotations/pipeline/status` - Check status

These endpoints handle session management, connection pooling, progress tracking, and error recovery.

## Development Commands

**Always use make commands. Run `make help` for the full list.**

### Quick Start - Hybrid Mode (Recommended)
```bash
make hybrid-up       # Start DB + Redis in Docker
make backend         # Terminal 1: FastAPI API (localhost:8000/docs)
make frontend        # Terminal 2: Vite dev server (localhost:5173)
make worker          # Terminal 3: ARQ background worker (requires Redis)
make hybrid-down     # Stop everything
```

### Code Quality (Pre-Commit)
```bash
make lint            # Backend: ruff check + fix (100-char line length)
make lint-frontend   # Frontend: ESLint check
make format-check    # Check formatting (backend + frontend, no auto-fix)
cd backend && uv run mypy <file.py> --ignore-missing-imports  # Typecheck modified files
# Pre-commit: gitleaks secret scanning (.pre-commit-config.yaml)
```

### Testing
```bash
make test            # Run all backend tests
make test-unit       # Unit tests only (fast)
make test-critical   # Critical tests only (smoke test)
make test-coverage   # Tests with HTML coverage report
make test-failed     # Re-run only failed tests
cd backend && uv run pytest tests/test_specific.py -v          # Single test file
cd backend && uv run pytest tests/test_specific.py::test_name -v  # Single test
cd frontend && npm run test:run                                   # Frontend tests (Vitest)
```

Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.critical`, `@pytest.mark.slow`
Tests use the existing PostgreSQL from Docker/hybrid setup with transaction rollback isolation.
Factory-Boy factories in `tests/factories.py` for test data generation.
Frontend tests use Vitest + jsdom (13 spec files across `src/api/`, `src/stores/`, `src/composables/`, `src/views/`, `src/components/`).

### CI (Local Verification - Matches GitHub Actions)
```bash
make ci              # Run all CI checks (backend + frontend)
make ci-backend      # Backend: lint + format check + tests
make ci-frontend     # Frontend: lint + format check + build
```

### Security
```bash
make security        # All security scans
make bandit          # Python SAST
make pip-audit       # Python dependency scan
make npm-audit       # JS dependency scan
```

### Database Management
```bash
make db-reset            # Complete reset (drop + migrate + initialize)
make db-clean            # Remove data, keep structure
make db-rebuild          # Clean + rebuild all data sources
make db-verify-complete  # Verify tables + views + schema integrity
make db-refresh-views    # Recreate all database views
make db-backup-full      # Full backup (migrations + schema + data)
```

### Other
```bash
make dev-up / make dev-down    # Full Docker mode (all services)
make status                    # System status + DB stats + data source status
make version                   # Show all component versions
make clean-all                 # Stop everything and clean all data
```

### Docker Compose Variants
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Full Docker dev (all services) |
| `docker-compose.services.yml` | DB + Redis only (for hybrid mode) |
| `docker-compose.prod.yml` | Production (NPM proxy network, no exposed ports) |
| `docker-compose.prod.test.yml` | Production test mode (ports: 8080/8001/5433) |

### Access Points (Hybrid Mode)
- **Frontend**: http://localhost:5173
- **Backend API / Swagger**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Package Management
- **Backend**: UV (not pip/poetry) - `uv sync --group dev`, `uv run <command>`
- **Frontend**: npm - `npm install`, `npm run <script>`

## Commit & Release Requirements

### Commit Messages: Conventional Commits (REQUIRED)
All commits MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) spec:
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

| Type | When | Version Impact |
|------|------|----------------|
| `feat:` | New feature | Minor bump |
| `fix:` | Bug fix | Patch bump |
| `docs:` | Documentation only | None |
| `style:` | Formatting, no logic change | None |
| `refactor:` | Code change, no new feature/fix | None |
| `test:` | Adding/updating tests | None |
| `chore:` | Build, deps, tooling | None |
| `ci:` | CI/CD workflow changes | None |
| `perf:` | Performance improvement | Patch bump |
| `feat!:` or `BREAKING CHANGE:` footer | Breaking change | Major bump |

Optional scopes: `(backend)`, `(frontend)`, `(pipeline)`, `(deps)`, etc.

**ALL code must pass lint, typecheck, and tests BEFORE committing.**
- Backend: `make lint` + `uv run mypy <files> --ignore-missing-imports`
- Frontend: `cd frontend && npm run lint`
- Tests: `make test`
- Fix ALL warnings, even in files you didn't create
- No exceptions: do not commit code with lint errors, type errors, or failing tests

### Versioning: Dual Version Scheme
This project uses **two independent version streams**:

| Stream | Scheme | Where | Tag Format | DOI Type |
|--------|--------|-------|------------|----------|
| **Code** | SemVer (`0.2.0`) | `pyproject.toml`, `package.json`, `config.py`, `CITATION.cff` | `v0.2.0` | `software` (Zenodo webhook) |
| **Data** | CalVer (`YYYY.MM`) | `data_releases` table, admin UI | None (API-driven) | `dataset` (ZenodoService API) |

**Code version** lives in 4 files that MUST stay in sync:
- `backend/pyproject.toml` — `[project].version`
- `frontend/package.json` — `version`
- `backend/app/core/config.py` — `APP_VERSION`
- `CITATION.cff` — `version`

Never bump one without the others. Use `make release-patch` or `make release-tag`.

### Release Flow
**Code releases** (new features, bug fixes):
```bash
make release-patch            # Bumps version in all 4 files, commits, tags
git push && git push --tags   # Triggers: cd.yml + release.yml + Zenodo webhook
```

**Data releases** (new gene annotations): Published via Admin UI → ReleaseService → ZenodoService mints dataset DOI automatically (if `ZENODO_API_TOKEN` configured).

### CI/CD Pipeline (7 workflows)
| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to main | Lint, test, build |
| `cd.yml` | `v*` tag push | Docker build, scan, deploy |
| `release.yml` | `v*` tag push | Create GitHub Release + changelog |
| `security.yml` | Push/PR + weekly | pip-audit, bandit, npm audit |
| `trivy-security-scan.yml` | Push/PR + daily | Container + config scanning |
| `gitleaks.yml` | Push/PR to main | Secret scanning |
| `lighthouse.yml` | PR with frontend changes | Performance audit |

### Zenodo DOI Integration
Two independent DOI streams for citability:

**Software DOI** (code repo archive):
- Concept DOI: `10.5281/zenodo.19316248` (always resolves to latest release)
- Minted automatically by Zenodo webhook when a GitHub Release is created from `v*` tag
- Metadata controlled by `.zenodo.json` at repo root
- Citation metadata in `CITATION.cff` (GitHub "Cite this repository" button)

**Dataset DOI** (gene data export):
- Minted by `ZenodoService` (`app.services.zenodo_service`) on data release publish
- Triggered via Admin UI → Publish Release → `ReleaseService.publish_release()`
- Uploads JSON export to Zenodo, stores DOI in `data_releases.doi` column
- Non-blocking: Zenodo failure does not prevent release publish
- Requires `ZENODO_API_TOKEN` in `backend/.env` (production Zenodo, not sandbox)

**Key files:**
- `CITATION.cff` — CFF 1.2.0 citation metadata (type: dataset)
- `.zenodo.json` — Zenodo archive metadata (upload_type: dataset)
- `backend/app/services/zenodo_service.py` — Zenodo REST API client
- `backend/tests/test_zenodo_service.py` — 12 unit tests
- `.github/workflows/release.yml` — GitHub Release creation on `v*` tags

## Architecture

### Layered Pattern
```
API Layer (FastAPI)         ← JSON:API compliant REST endpoints + WebSocket
Business Logic (Services)   ← Annotation pipeline, scoring, network analysis
Core Utilities (Shared)     ← Cache, Retry, Logging (MUST REUSE)
Data Access (CRUD/ORM)      ← SQLAlchemy models and operations
Database (PostgreSQL)       ← Hybrid relational + JSONB + materialized views
```

### Backend Structure (`backend/app/`)
- **`main.py`** - FastAPI app with lifespan, router registration, middleware
- **`api/endpoints/`** - 21 REST endpoint modules (genes, auth, admin, annotations, statistics, network, seo, releases, etc.)
- **`models/`** - 22 SQLAlchemy models (genes, gene_evidence, gene_curations, gene_staging, users, annotations, settings, etc.)
- **`crud/`** - Database operations (gene, gene_staging, statistics)
- **`schemas/`** - Pydantic request/response schemas
- **`core/`** - Shared utilities (logging, cache, retry, config, ARQ, monitoring, etc.)
- **`services/`** - Business logic (backup, enrichment, network_analysis, release, settings, zenodo)
- **`pipeline/`** - Data ingestion pipeline and annotation sources
- **`db/`** - Database view system with dependency tracking
- **`middleware/`** - Error handling + logging middleware

### Frontend Structure (`frontend/src/`)
**Stack**: Vue 3 + TypeScript + Tailwind CSS v4 + shadcn-vue (reka-ui) + TanStack Table + Pinia + Vitest + vite-ssg (SSG/prerendering)
- **`views/`** - Page components (Home, Genes, GeneDetail, Dashboard, Admin panels, etc.)
- **`components/`** - Reusable components organized by domain (admin, auth, evidence, gene, network, visualizations) + `ui/` (shadcn-vue primitives)
- **`stores/`** - Pinia state management (auth, logs)
- **`services/`** - WebSocket service for real-time updates
- **`api/`** - Axios-based API client modules (use these, not raw fetch/axios)
- **`composables/`** - Reusable Vue composition functions
- **`router/`** - Vue Router with route guards
- **`plugins/`** - App plugins

### Database Design
- **Hybrid architecture**: Relational columns for fast queries + JSONB for flexible detailed data
- **Two-stage ingestion**: gene_staging (raw) → gene_curations (validated)
- **View system** (`app.db.views`, `app.db.materialized_views`): SQL views with dependency-aware topological sorting for creation/drop ordering. Use `make db-refresh-views` to recreate.
- **22 tables**, multiple views and materialized views (gene_scores, source_distribution, etc.)
- **All schema changes** through Alembic migrations (`backend/alembic/versions/`)

### ARQ Background Worker
Redis-based async task queue for pipeline operations:
- `app.core.arq_client.py` - Task submission
- `app.core.arq_tasks.py` - Task definitions
- `app.core.arq_worker.py` - Worker configuration
- Start with `make worker` (requires Redis via `make services-up`)

### Configuration System
YAML-based configuration with environment variable overrides:
- `app.core.datasource_config` - Pydantic-validated config loading
- Config files in `backend/app/core/` (datasources, keywords, annotations)
- Environment variable override prefix: `KG_`
- `backend/.env.example` for required environment variables

### Data Pipeline (`backend/app/pipeline/sources/`)
Annotation sources are split across two directories:
- **`unified/`** — Original sources extending `BaseAnnotationSource`: `panelapp.py`, `hpo.py`, `clingen.py`, `gencc.py`, `pubtator.py`, `diagnostic_panels.py`, `literature.py`
- **`annotations/`** — Newer annotation sources: `mpo_mgi.py`, `gtex.py`, `ensembl.py`, `hgnc.py`, `uniprot.py`, `gnomad.py`, `clinvar.py`, `string_ppi.py`, `descartes.py`, `hpo.py`
- Evidence aggregation in `backend/app/pipeline/aggregate.py`

#### External API Gotchas
- **JAX API** (`informatics.jax.org`): Behind reCAPTCHA — cannot be called server-side. MPO terms are loaded from a static file cache at `backend/app/data/mpo_kidney_terms.json` (661 terms).
- **InterMine/MouseMine**: `size=0` means "return 0 rows", NOT unlimited. Omit the `size` param entirely for unlimited results.
- **GTEx**: Uses bulk GCT file download (not API). Tissue keys must be normalized from human-readable (`"Kidney - Cortex"`) to API-style (`"Kidney_Cortex"`) via `_normalise_tissue_id()`.

## Non-Blocking Pattern (CRITICAL)

Sync SQLAlchemy + ThreadPoolExecutor (chosen over async SQLAlchemy for simplicity and maturity):

```python
# CORRECT - Offload heavy sync ops to thread pool
from starlette.concurrency import run_in_threadpool

async def heavy_operation(db):
    result = await run_in_threadpool(lambda: db.execute(text("SELECT ...")).fetchall())
    return result

# Simple indexed lookups (<10ms) can be called directly
gene = db.query(Gene).filter_by(id=gene_id).first()  # OK - fast enough

# WRONG - Never block the event loop with heavy operations
async def bad():
    db.execute(text("REFRESH MATERIALIZED VIEW"))  # BLOCKS!
```

**Rule of thumb**: <10ms direct call OK, >50ms should offload, >100ms MUST offload.

## Core Systems (MUST USE)

### Logging
```python
from app.core.logging import get_logger
logger = get_logger(__name__)
await logger.info("msg", key=value)       # Async context
logger.sync_info("msg", key=value)        # Sync context
bound = logger.bind(request_id=uuid)      # Context binding
```
Decorators: `@timed_operation`, `@database_query`, `@monitor_blocking`

### Caching (L1 in-memory LRU + L2 PostgreSQL JSONB)
```python
from app.core.cache_service import get_cache_service
cache = get_cache_service(db_session)
await cache.get("key", namespace="annotations")
await cache.set("key", value, namespace="annotations", ttl=3600)
```

### Retry + HTTP
```python
from app.core.retry_utils import retry_with_backoff, RetryableHTTPClient, RetryConfig
@retry_with_backoff(config=RetryConfig(max_retries=5))
async def call(): ...
client = RetryableHTTPClient(client=httpx.AsyncClient(), retry_config=config)
```

### New Annotation Source
```python
from app.pipeline.sources.unified.base import BaseAnnotationSource
class NewSource(BaseAnnotationSource):
    source_name = "new_source"
    cache_ttl_days = 7
    requests_per_second = 5.0
    async def fetch_annotation(self, gene): ...
```

### Frontend Patterns
```typescript
// API: Use existing API client modules in src/api/
import { genesApi } from '@/api/genes'

// State: Use Pinia stores for shared state
import { useAuthStore } from '@/stores/auth'

// Real-time: WebSocket service for pipeline progress
import { useWebSocket } from '@/services/websocket'

// UI components: Use shadcn-vue primitives from src/components/ui/
import { Button } from '@/components/ui/button'
```

## Security
- JWT authentication with roles: Admin, Curator, Public
- Public access for all GET endpoints (no auth required for reading)
- Environment-based secrets configuration
- Bcrypt password hashing (12 rounds)

## Planning & Documentation
- **All planning documents** live in `.planning/` (PROJECT.md, ROADMAP.md, REQUIREMENTS.md, STATE.md, MILESTONES.md)
- **Archived/completed plans** are in `.planning/archive/`
- There is no separate `docs/` directory — `.planning/` is the single location for all project documentation.
