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
- Port 5 data sources from R to Python:
  - **PanelApp**: API integration (UK & Australia)
  - **Literature**: Excel file processing
  - **Diagnostic Panels**: Web scraping (using custom-panel patterns)
  - **HPO**: Phenotype ontology API
  - **PubTator**: Literature mining API
- Merge and annotation logic

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
- Data migration from existing CSVs
- Validation against R outputs
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

```bash
# 1. Clone repository
git clone <repo-url>
cd kidney-genetics-db

# 2. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start services
docker-compose up -d

# 4. Access services
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Database: localhost:5432
```

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
- [Database Plan](plan/database/README.md) - Schema and migration strategy
- [Backend Plan](plan/backend/README.md) - FastAPI implementation details
- [Frontend Plan](plan/frontend/README.md) - Vue.js application structure

## Success Metrics

- ✅ All 3,000+ genes migrated successfully
- ✅ 5 core data sources integrated
- ✅ <200ms API response times
- ✅ CSV/JSON export compatibility
- ✅ Docker-based deployment

## Contact

For questions or contributions, see the project README.