# Kidney-Genetics Database

[![DOI](https://zenodo.org/badge/1029597888.svg)](https://doi.org/10.5281/zenodo.19316248)
[![CI](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/ci.yml)
[![Security](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/security.yml/badge.svg)](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/security.yml)

**Version**: v0.3.1 (March 2026)
**Status**: Production

A modern platform for curating and exploring kidney disease-related genes with evidence-based scoring. Modernizes the original [kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R-based pipeline into a scalable web application.

## Overview

Curates 5,080+ kidney disease genes from 17 authoritative sources with evidence scoring, two-stage data ingestion (staging → curated), and comprehensive annotations. Features unified caching, retry logic, real-time progress tracking, and an admin panel with pipeline management.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.14, FastAPI, SQLAlchemy, PostgreSQL (relational + JSONB) |
| **Frontend** | Vue 3, TypeScript, Tailwind CSS v4, shadcn-vue (reka-ui), TanStack Table, Pinia |
| **Pipeline** | 17 annotation sources, bulk + per-gene fetching, async with ThreadPoolExecutor |
| **Infrastructure** | Docker Compose, Redis (ARQ worker), Alembic migrations, GitHub Actions CI/CD |
| **Data Sources** | HGNC, gnomAD, ClinVar, HPO, GTEx, Descartes, MPO/MGI, STRING PPI, Ensembl, UniProt, PanelApp, ClinGen, GenCC, PubTator |

## Quick Start

### Hybrid Development (Recommended)

```bash
# Start database + Redis in Docker
make hybrid-up

# Then in separate terminals:
make backend    # FastAPI API (localhost:8000/docs)
make frontend   # Vite dev server (localhost:5173)
make worker     # ARQ background worker (optional, requires Redis)

# Stop everything
make hybrid-down
```

### Full Docker Development

```bash
make dev-up     # Start all services in Docker
make dev-down   # Stop everything
```

### Access Points

- **Frontend**: http://localhost:5173
- **API / Swagger**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Requirements

- Python 3.14+ (managed via [UV](https://docs.astral.sh/uv/))
- Node.js 18+
- Docker & Docker Compose

## Project Structure

```
backend/            FastAPI application with data pipeline
  app/
    api/endpoints/  REST API endpoints (21 modules)
    pipeline/       Annotation sources (unified/ and annotations/)
    core/           Shared utilities (logging, cache, retry, config)
    models/         SQLAlchemy models (22 tables)
    services/       Business logic (backup, enrichment, releases, Zenodo)
    db/             View system with dependency-aware topological sorting
frontend/           Vue 3 + TypeScript SPA
  src/
    views/          Page components
    components/     Domain-organized + shadcn-vue primitives
    api/            Axios-based API client modules
    stores/         Pinia state management
    composables/    Vue composition functions
```

## Development

```bash
make help            # Show all available commands
make status          # System status + DB stats
make lint            # Backend: ruff check + fix
make lint-frontend   # Frontend: ESLint
make format-check    # Check formatting (backend + frontend)
make test            # Run all backend tests
make ci              # Run full CI checks locally
make security        # All security scans
make db-reset        # Complete database reset
```

See [CLAUDE.md](CLAUDE.md) for comprehensive development guidance and architecture details.

## Versioning

This project uses two independent version streams:

- **Code**: SemVer (`0.3.1`) — tagged releases with Zenodo software DOI
- **Data**: CalVer (`YYYY.MM`) — API-driven data releases with Zenodo dataset DOI

## Citation

If you use the Kidney-Genetics Database, please cite:

> Kidney-Genetics Database (v0.3.1). DOI: [10.5281/zenodo.19316248](https://doi.org/10.5281/zenodo.19316248)

See [CITATION.cff](CITATION.cff) for full citation metadata.

## License

MIT License — see [LICENSE](LICENSE) file.
