# Kidney-Genetics Database (Alpha)

⚠️ **WARNING: This is alpha software (v0.1.0). Not suitable for production use.**

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
**Configuration**: Three-tier system (ENV → YAML → Defaults) with pydantic-settings validation

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
# Start all services in Docker containers
make dev-up
```

**Access Points:**
- Frontend: http://localhost:5173 (hybrid) or http://localhost:3000 (docker)
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

## Requirements

- Python 3.10+
- Node.js 18+
- Docker (for PostgreSQL)

## Project Structure

- `backend/` - FastAPI application with data pipeline
- `backend/config/` - YAML configuration files (datasources, keywords, annotations)
- `frontend/` - Vue.js/Vuetify web interface
- `docs/` - Architecture documentation and implementation guides
- `docker-compose.services.yml` - PostgreSQL database setup

## Development

### Available Commands
```bash
make help           # Show all available commands
make status         # Show system status and statistics
make db-reset       # Complete database reset
make clean-all      # Stop everything and clean data
```

### Code Quality
```bash
# Backend linting
cd backend && uv run ruff check . --fix

# Frontend linting  
cd frontend && npm run lint && npm run format
```

## Status: Alpha Development

🚧 **Version**: 0.1.0-alpha (2025-08-18)
🔴 **Stage**: Alpha - Expect bugs and breaking changes
✅ **Working**: Core features with 571 genes from 4 data sources
⚠️ **Missing**: Tests, security, production readiness

See `ROADMAP.md` for path to production, `TODO.md` for current tasks, and `PLAN.md` for pending features.

## License

MIT License - see [LICENSE](LICENSE) file.