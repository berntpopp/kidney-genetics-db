# Kidney-Genetics Database

**Version**: Alpha v0.1.0 (October 2025)
**Status**: 🟢 Production-Ready

A modern platform for curating kidney disease-related genes with evidence-based scoring. Modernizes the original [kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R-based pipeline into a scalable web application.

## Overview

Curates kidney disease genes from multiple authoritative sources with evidence scoring, two-stage data ingestion (staging → curated), and comprehensive annotations. Features unified caching, retry logic, and real-time progress tracking.

## Implementation

**Backend**: Python/FastAPI with PostgreSQL (hybrid relational/JSONB), unified logging/caching/retry systems
**Frontend**: Vue.js + Vuetify with WebSocket progress tracking
**Data Sources**: HGNC, gnomAD, ClinVar, HPO, GTEx, Descartes, MPO/MGI, STRING PPI, PubTator
**Architecture**: Non-blocking async/await with ThreadPoolExecutor, L1/L2 caching, exponential backoff retry

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
- `.planning/archive/docs/` - Historical documentation and implementation notes
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

## Status

**Current**: Production-ready alpha with core functionality operational
**Working**: Multi-source gene curation, evidence scoring, admin panel, unified systems
**In Progress**: Email verification, password reset, comprehensive test coverage

See [CLAUDE.md](CLAUDE.md) for development guidance and architecture details.

## License

MIT License - see [LICENSE](LICENSE) file.