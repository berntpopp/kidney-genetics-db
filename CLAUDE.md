# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kidney-Genetics Database**: A modern web platform for curating and exploring kidney disease-related genes. This project modernizes the original R-based pipeline into a scalable Python/FastAPI + Vue.js architecture with PostgreSQL backend.

**Current Status**: Alpha version (v0.1.0) with working backend API, frontend interface, and data ingestion pipeline. Core functionality operational with 571+ genes from multiple data sources.

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

## Security Notes

- Basic user model with admin flag (authentication not fully implemented)
- Bcrypt dependency available for password hashing
- Environment-based configuration
- Never commit secrets or API keys to repository