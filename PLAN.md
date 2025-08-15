# Kidney-Genetics Database Modernization Plan

## Executive Summary

Modernization of the R-based kidney-genetics pipeline into a lean, scalable web application using PostgreSQL, FastAPI, and Vue.js. The system processes kidney disease-related genes from 5 core data sources (PanelApp, Literature, Diagnostic Panels, HPO, PubTator) to produce a curated, searchable database.

## Project Overview

### Current State (kidney-genetics-v1)
- **Language**: R-based analysis scripts
- **Data Volume**: ~3,000 kidney disease genes
- **Sources**: 5 core data sources with manual execution
- **Output**: Timestamped CSV files

### Target Architecture
- **Database**: PostgreSQL 14+ with JSONB for flexibility
- **Backend**: FastAPI with simple CRUD operations
- **Frontend**: Vue 3 + Vuetify for clean Material Design UI
- **Pipeline**: Direct Python port of R logic
- **Deployment**: Docker-based development environment

## Core Principles

1. **Lean Implementation**: Focus on core functionality, avoid over-engineering
2. **Direct Port**: Replicate R pipeline logic in Python without unnecessary additions
3. **Simple Schema**: 4 core tables with JSONB for flexible evidence storage
4. **Fast Development**: Docker environment with hot reloading

## Implementation Plan

### Phase 1: Foundation
- Docker development environment (PostgreSQL, Redis, Backend, Frontend)
- Database schema with Alembic migrations
- Basic FastAPI skeleton

### Phase 2: Data Pipeline
- Port R scripts to Python (complete rewrite):
  - **PanelApp**: Direct API integration (stable)
  - **HPO**: Direct API integration (stable)
  - **PubTator**: Direct API integration (stable)
  - **Diagnostic Panels**: Separate scraping service with API ingestion
  - **Literature**: Manual upload API endpoint
- Recompute all gene data from original sources
- Implement merge and annotation logic in Python

### Phase 3: API Development
- Gene CRUD endpoints
- Search and filtering
- CSV/JSON export
- Pipeline management endpoints

### Phase 4: Frontend
- Vue 3 + Vuetify setup
- Gene browser with search
- Simple dashboard
- Export functionality

### Phase 5: Testing & Deployment
- Recompute all gene data from sources (no CSV migration)
- Validate new computations against R outputs
- Docker production setup

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

### Option 1: Full Docker (Simple)
```bash
# 1. Clone repository
git clone <repo-url>
cd kidney-genetics-db

# 2. Setup environment
cp .env.example .env

# 3. Start everything
docker-compose up -d

# 4. Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Database: localhost:5432
```

### Option 2: Hybrid Mode (Recommended for Development)
```bash
# 1. Start database only
docker-compose -f docker-compose.services.yml up -d

# 2. Run backend locally (Terminal 1)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. Run frontend locally (Terminal 2)
cd frontend
npm install
npm run dev
```

See [Hybrid Development Guide](plan/HYBRID-DEVELOPMENT.md) for more options.

## Key Technologies

- **PostgreSQL 14+**: Main database with JSONB support
- **FastAPI**: Modern Python web framework with automatic API documentation
- **Vue 3 + Vuetify**: Reactive frontend with Material Design components
- **Docker**: Containerized development and deployment
- **Alembic**: Database migration management

## Data Sources

1. **PanelApp** - Gene panels from Genomics England and Australia
2. **Literature** - Manual curation from research papers
3. **Diagnostic Panels** - Commercial panel data (Blueprint Genetics, etc.)
4. **HPO** - Human Phenotype Ontology associations
5. **PubTator** - Automated literature mining

## Reference Projects

- **kidney-genetics-v1**: Original R implementation with core logic
- **custom-panel**: Python project with reusable scraping patterns

## Documentation

Detailed implementation plans are available in the `plan/` directory:

- [Development Guide](plan/DEVELOPMENT.md) - Setup and development workflow
- [Hybrid Development](plan/HYBRID-DEVELOPMENT.md) - Flexible Docker/local development modes
- [Data Source Architecture](plan/DATA-SOURCE-ARCHITECTURE.md) - Smart source integration strategy
- [Database Plan](plan/database/README.md) - Schema and migration strategy
- [Backend Plan](plan/backend/README.md) - FastAPI implementation details
- [Frontend Plan](plan/frontend/README.md) - Vue.js application structure

## Success Metrics

- ✅ All gene data recomputed from original sources
- ✅ 5 core data sources integrated and automated
- ✅ <200ms API response times
- ✅ CSV/JSON export compatibility
- ✅ Results validated against R pipeline outputs
- ✅ Docker-based deployment

## Contact

For questions or contributions, see the project README.