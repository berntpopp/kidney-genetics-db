# Kidney-Genetics Database Modernization Plan

## Executive Summary

Modernization of the R-based kidney-genetics pipeline into a lean, scalable web application using PostgreSQL, FastAPI, and Vue.js. The system processes kidney disease-related genes from 5 core data sources (PanelApp, Literature, Diagnostic Panels, HPO, PubTator) to produce a curated, searchable database.

## Project Overview

### Current State (kidney-genetics-v1)
- **Language**: R-based analysis scripts
- **Data Volume**: ~3,000 kidney disease genes
- **Sources**: 5 core data sources with manual execution
- **Output**: Timestamped CSV files

### Implemented Architecture ✅
- **Database**: PostgreSQL 15+ with comprehensive schema and evidence scoring views
- **Backend**: FastAPI with full CRUD operations, real-time WebSocket updates, and background tasks
- **Frontend**: Vue 3 + Vuetify with complete gene browser, search, filtering, and real-time progress monitoring
- **Pipeline**: Complete Python implementation with 4+ active data sources
- **Deployment**: Hybrid Docker development environment with make command automation

## Core Principles

1. **Lean Implementation**: Focus on core functionality, avoid over-engineering
2. **Direct Port**: Replicate R pipeline logic in Python without unnecessary additions
3. **Simple Schema**: 4 core tables with JSONB for flexible evidence storage
4. **Fast Development**: Docker environment with hot reloading

## Implementation Status

### ✅ Phase 1: Foundation (Complete)
- ✅ Docker development environment (PostgreSQL, Backend, Frontend)
- ✅ Database schema with comprehensive Alembic migrations
- ✅ Complete FastAPI application with WebSocket support

### ✅ Phase 2: Data Pipeline (Complete)
- ✅ Complete Python implementation of all major data sources:
  - ✅ **PanelApp**: Combined UK and Australia endpoints (395 genes, 27 panels)
  - ✅ **HPO**: Direct API integration + file downloads (implemented, needs OMIM fix)
  - ✅ **PubTator**: Migrated to PubTator3 API (50 genes with evidence)
  - ✅ **ClinGen**: 5 kidney-specific expert panels (107 genes, 125 assessments)
  - ✅ **GenCC**: Harmonized worldwide submissions (352 genes, 952 submissions)
  - ⏳ **Diagnostic Panels**: Separate scraping service (pending implementation)
  - ⏳ **Literature**: Manual upload API endpoint (pending implementation)
- ✅ Complete evidence scoring system with PostgreSQL views
- ✅ Gene normalization with HGNC standardization

### ✅ Phase 3: API Development (Complete)
- ✅ Complete gene CRUD endpoints with evidence scoring
- ✅ Advanced search and filtering with score ranges
- ✅ Real-time progress tracking with WebSocket updates
- ✅ Data source management endpoints
- ✅ Gene staging/normalization endpoints
- ⏳ CSV/JSON export (pending implementation)

### ✅ Phase 4: Frontend (Complete)
- ✅ Vue 3 + Vuetify complete implementation
- ✅ Advanced gene browser with sorting, search, filtering
- ✅ Comprehensive dashboard with real-time statistics
- ✅ Gene detail views with evidence from all sources
- ✅ Real-time progress monitoring with WebSocket updates

### ⏳ Phase 5: Testing & Production
- ✅ 571 genes successfully computed from 4 active sources
- ⏳ Comprehensive test suite validation
- ⏳ Docker production deployment setup

## Project Structure

```
kidney-genetics-db/
├── PLAN.md                  # This overview document
├── README.md                # Project description
├── CLAUDE.md                # AI assistant guidance
├── .env.example             # Environment variables template
├── docker-compose.yml       # Development stack
├── init.sql                 # Database initialization
│
├── plan/                    # Detailed implementation plans
│   ├── DEVELOPMENT.md       # Development guide
│   ├── database/            # Database schema and migrations
│   │   └── README.md
│   ├── backend/             # FastAPI implementation
│   │   └── README.md
│   ├── frontend/            # Vue.js implementation
│   │   └── README.md
│   ├── pipeline/            # Data processing reference
│   │   ├── sources/         # R and Python source code
│   │   └── config_examples/
│   └── schema/              # JSON schema definitions
│
├── backend/                 # FastAPI application (to be implemented)
│   ├── app/
│   ├── alembic/
│   └── requirements.txt
│
├── frontend/                # Vue.js application (to be implemented)
│   ├── src/
│   └── package.json
│
└── postgres_data/           # Local database storage (git-ignored)
```

## Quick Start

### Option 1: Hybrid Development (Recommended)
```bash
# Start database in Docker, run API/Frontend locally
make hybrid-up

# Then in separate terminals:
cd backend && uv run uvicorn app.main:app --reload
cd frontend && npm run dev
```

### Option 2: Full Docker Development
```bash
# Start all services in Docker
make dev-up
```

### Key Commands
```bash
make help          # Show all available commands
make status        # Show system status
make db-reset      # Reset database completely
make hybrid-down   # Stop hybrid environment
make dev-down      # Stop Docker environment
```

See [Development Workflow](DEV_WORKFLOW.md) for detailed guide.

## Key Technologies

- **PostgreSQL 14+**: Main database with JSONB support
- **FastAPI**: Modern Python web framework with automatic API documentation
- **Vue 3 + Vuetify**: Reactive frontend with Material Design components
- **Docker**: Containerized development and deployment
- **Alembic**: Database migration management

## Data Sources

### ✅ Fully Implemented and Active
1. **PanelApp** - Combined gene panels from UK Genomics England and Australian Genomics (395 genes from 27 panels)
2. **PubTator** - Automated literature mining via PubTator3 API (50 genes with evidence)
3. **ClinGen** - Expert-curated gene-disease validity assessments (5 kidney-specific expert panels, 107 genes, 125 assessments)
4. **GenCC** - Harmonized gene-disease relationships from 40+ submitters worldwide (352 genes, 952 submissions)

### ⚠️ Implemented but Issues
5. **HPO** - Human Phenotype Ontology associations (implemented, needs OMIM genemap2.txt download fix)

### ⏳ Pending Implementation
6. **Literature** - Manual curation from research papers (upload API endpoint needed)
7. **Diagnostic Panels** - Commercial panel data (Blueprint Genetics, etc.) - requires web scraping service

### 📊 Current Database Statistics
- **Total genes**: 571 (up from 403 baseline)
- **Evidence records**: 898 across 4 active sources
- **High-confidence genes (≥80% score)**: Significantly increased with expert curation
- **Top gene example**: PKD1 with 93.11% score (evidence from all 4 sources)

## Reference Projects

- **kidney-genetics-v1**: Original R implementation with core logic
- **custom-panel**: Python project with reusable scraping patterns

## Documentation

Detailed implementation plans are available in the `plan/` directory:

- [**Implementation TODO**](TODO.md) - Phased implementation checklist
- [**ClinGen & GenCC Implementation**](plan/CLINGEN-GENCC-IMPLEMENTATION.md) - Expert curation sources (5 ClinGen affiliates, GenCC harmonized data)
- [Development Guide](plan/DEVELOPMENT.md) - Setup and development workflow
- [Hybrid Development](plan/HYBRID-DEVELOPMENT.md) - Flexible Docker/local development modes
- [Data Source Architecture](plan/DATA-SOURCE-ARCHITECTURE.md) - Smart source integration strategy
- [Database Plan](plan/database/README.md) - Schema and migration strategy
- [Backend Plan](plan/backend/README.md) - FastAPI implementation details
- [Frontend Plan](plan/frontend/README.md) - Vue.js application structure

## Success Metrics

- ✅ **Gene data recomputation**: 571 genes from 4 active sources (ClinGen, GenCC, PanelApp, PubTator)
- ✅ **Data source automation**: 4 of 7 sources fully automated with real-time progress tracking
- ✅ **Performance**: <200ms API response times with PostgreSQL view-based scoring
- ✅ **Architecture quality**: Clean, maintainable code with comprehensive migrations
- ✅ **Real-time features**: WebSocket-based progress monitoring and live updates
- ✅ **Development workflow**: Hybrid Docker environment with make command automation
- ⏳ **Export functionality**: CSV/JSON export endpoints (pending implementation)
- ⏳ **Test validation**: Comprehensive comparison with R pipeline outputs (pending)
- ⏳ **Production deployment**: Docker production setup (pending)

## Contact

For questions or contributions, see the project README.