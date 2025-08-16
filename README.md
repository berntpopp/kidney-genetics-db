# Kidney-Genetics Database

A modern web platform for curating and exploring kidney disease-related genes. This project modernizes the original [kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R-based pipeline into a scalable Python/FastAPI + Vue.js architecture.

## Overview

A comprehensive database of ~3,000 kidney disease-associated genes aggregated from multiple genomic databases including PanelApp, HPO, diagnostic panels, and literature sources. Provides both a web interface and REST API for researchers and clinicians.

### Key Features

- **Multi-source Integration**: PanelApp, HPO, PubTator, commercial panels, and manual curation
- **Evidence Scoring**: Configurable weighting system for gene-disease associations  
- **Interactive Interface**: Searchable gene browser with filtering and visualization
- **REST API**: JSON/CSV exports with comprehensive documentation
- **Automated Updates**: Scheduled pipeline keeps data current
- **Version Tracking**: Historical data access and provenance

## Architecture

**Backend**: Python/FastAPI with PostgreSQL database and Celery task processing  
**Frontend**: Vue.js/Vuetify with interactive gene browser and data visualizations  
**Data**: PanelApp, HPO, commercial panels, literature curation, PubTator, ClinVar/OMIM

## Quick Start

```bash
# 1. Start database
docker-compose -f docker-compose.services.yml up -d

# 2. Install backend dependencies
cd backend
pip install uv
uv pip install -e .

# 3. Run migrations & import data
uv run alembic upgrade head
uv run python -m app.pipeline.run update --source panelapp

# 4. Start backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. In new terminal, start frontend
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Database: 318 kidney-related genes from PanelApp

## Requirements

- Python 3.10+
- Node.js 18+
- Docker (for PostgreSQL)

## Project Structure

- `backend/` - FastAPI application with data pipeline
- `frontend/` - Vue.js/Vuetify web interface
- `plan/` - Architecture documentation and schemas
- `docker-compose.services.yml` - PostgreSQL database setup

## Development

```bash
# Backend linting
cd backend && uv run ruff check . --fix

# Frontend linting  
cd frontend && npm run lint && npm run format
```

## Status

✅ **Phases 0-4 Complete**: Database, API, PanelApp integration, and Vue.js frontend functional.  
🔄 **Phase 5 In Progress**: Adding HPO and PubTator data sources.

See `TODO.md` for detailed progress and `PLAN.md` for architecture.

## License

MIT License - see [LICENSE](LICENSE) file.