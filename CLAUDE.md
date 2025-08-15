# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Kidney-Genetics Database**: A modern web platform for curating and exploring kidney disease-related genes. This project is modernizing the original R-based pipeline into a scalable Python/FastAPI + Vue.js architecture with PostgreSQL backend.

**Current Status**: Under active development - planning and architecture phase complete, implementation pending.

## Project Architecture

### Core Components (Planned)
- **Backend**: FastAPI with PostgreSQL, hybrid relational + JSONB architecture
- **Frontend**: Vue 3 + Vite with Vuetify for Material Design
- **Database**: PostgreSQL 15+ with pg_jsonschema extension for validation
- **Pipeline**: Python-based data processing replacing R scripts
- **Background Tasks**: Celery with Redis for async processing

### Key Directories
- `plan/` - Complete implementation planning documents and schema definitions
- `plan/database/` - PostgreSQL schema design and migration plans
- `plan/backend/` - FastAPI implementation specifications
- `plan/frontend/` - Vue.js interface design plans
- `plan/pipeline/` - Data processing pipeline reference code (R and Python)
- `plan/schema/` - JSON schema definitions for data validation

## Development Commands

### Docker Development Environment (Planned)
```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Run data pipeline
docker-compose exec api python -m pipeline.run_update

# Stop services
docker-compose down
```

### Backend Development (Planned)
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest backend/tests/

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend Development (Planned)
```bash
# Install dependencies
cd frontend && npm install

# Run development server with HMR
npm run dev

# Build for production
npm run build

# Run tests
npm run test
```

## High-Level Architecture

### Database Design (Hybrid Architecture)
The database uses a hybrid PostgreSQL design combining:
- **Relational columns** for core metrics (fast queries on evidence scores, classification)
- **JSONB columns** for detailed evidence and flexible schema evolution
- **Content addressability** with SHA-256 hashing for immutable versioning
- **Complete audit trail** for professional curation workflow

### Data Flow
1. **Data Sources** → Multiple sources (PanelApp, HPO, Literature, Diagnostic Panels, PubTator)
2. **Pipeline Processing** → Python modules process and standardize data
3. **Database Storage** → PostgreSQL with versioned gene curations
4. **API Layer** → FastAPI serves RESTful endpoints
5. **Frontend** → Vue.js provides interactive interface

### Key Features
- **GenCC-compatible schema** for international database submission
- **Multi-stage curation workflow** with review tracking
- **Evidence scoring engine** with configurable weights
- **Complete provenance tracking** for all data points
- **Professional audit logging** for regulatory compliance

## Important Implementation Notes

### Schema Management
- All schema changes MUST go through Alembic migrations
- JSON schemas in `plan/schema/` define data structure
- Pydantic models auto-generated from JSON schemas
- Database-level validation using pg_jsonschema

### Data Pipeline Architecture
The project includes reference implementations from two sources:
1. **R Functions** (`plan/pipeline/sources/*.R`) - Original kidney-genetics logic
2. **Python Modules** (`plan/pipeline/sources/g*.py`) - Modern Python implementations

Key pipeline components:
- PanelApp integration (UK and Australia)
- HPO phenotype data processing
- Commercial panel web scraping
- Literature mining via PubTator
- Evidence scoring and merging

### Development Priorities
1. **Database First**: Set up PostgreSQL schema and migrations
2. **Backend API**: Implement FastAPI with core endpoints
3. **Data Migration**: Convert existing CSV data to new schema
4. **Frontend Interface**: Build Vue.js application
5. **Pipeline Modernization**: Port R scripts to Python

## Testing Strategy

### Backend Testing
- Unit tests for all API endpoints
- Integration tests for database operations
- Mock external API calls (PanelApp, HPO, etc.)
- Test coverage target: >90%

### Frontend Testing
- Component testing with Vitest
- E2E testing for critical workflows
- Visual regression testing for UI consistency

### Data Validation
- Compare Python pipeline output with R pipeline results
- Field-by-field validation of gene data
- Performance benchmarking with full dataset

## External Dependencies

### APIs and Data Sources
- **PanelApp API**: Gene panel data (UK and Australia)
- **HPO API**: Human Phenotype Ontology
- **PubTator API**: Literature mining
- **NCBI/OMIM**: Gene and disease information
- **ClinVar**: Clinical variant data
- **STRING-DB**: Protein interactions
- **GTEx**: Gene expression data

### Configuration
- API keys stored in environment variables
- YAML configuration for pipeline settings
- Docker secrets for production deployment

## Migration from R Pipeline

The project is migrating from an R-based pipeline (`kidney-genetics`) to Python. Key considerations:
- Preserve all existing functionality
- Maintain data compatibility
- Parallel validation during transition
- Gradual component-by-component migration

## Security Considerations

- JWT authentication for API access
- Role-based access control (viewer, curator, admin)
- Bcrypt password hashing
- Environment-based configuration
- Never commit secrets or API keys
- Use Docker secrets in production