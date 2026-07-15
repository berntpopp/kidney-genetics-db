# Kidney-Genetics Database

[![DOI](https://zenodo.org/badge/1029597888.svg)](https://doi.org/10.5281/zenodo.19316248) [![CI](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/ci.yml) [![Security](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/security.yml/badge.svg)](https://github.com/berntpopp/kidney-genetics-db/actions/workflows/security.yml) [![Version](https://img.shields.io/github/v/release/berntpopp/kidney-genetics-db?label=version)](https://github.com/berntpopp/kidney-genetics-db/releases/latest)

A scientific platform for curating and exploring kidney disease-related genes
with evidence-based scoring. It modernizes the original
[kidney-genetics](https://github.com/halbritter-lab/kidney-genetics) R pipeline
as a reproducible web application.

## Overview

The database curates 5,080+ kidney disease genes from 17 authoritative sources
with evidence scoring, staging-to-curated ingestion, and provenance-aware
annotations. It includes unified caching, retries, progress tracking, and an
administrative pipeline interface.

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI, SQLAlchemy, PostgreSQL, Python 3.14 production image |
| **Frontend** | Vue 3, TypeScript, Vite SSG, Tailwind CSS, Pinia |
| **MCP** | Read-only FastMCP server over an allowlisted public API |
| **Infrastructure** | Docker Compose v2, Redis/ARQ, Alembic, GitHub Actions |
| **Data sources** | HGNC, gnomAD, ClinVar, HPO, GTEx, Descartes, MPO/MGI, STRING, Ensembl, UniProt, PanelApp, ClinGen, GenCC, and PubTator |

## Prerequisites

- Git
- [uv](https://docs.astral.sh/uv/) and Python 3.13 for local development and
  CI. The backend production container deliberately uses Python 3.14.
- Node.js >=22.18.0 and npm for the frontend.
- Docker Engine and Docker Compose v2 (`docker compose`).

Check the local toolchain before troubleshooting setup:

```bash
uv --version
node --version
npm --version
docker compose version
```

## Quick Start

Clone the repository and install all locked development dependencies:

```bash
git clone https://github.com/berntpopp/kidney-genetics-db.git
cd kidney-genetics-db
make install

# Backend configuration is read from backend/.env; never commit this file.
cp backend/.env.example backend/.env
# Before starting the API, set DATABASE_URL, POSTGRES_PASSWORD=kidney_pass,
# a unique JWT_SECRET_KEY of at least 32 characters, and ADMIN_PASSWORD in backend/.env.

# Start PostgreSQL and Redis for local services.
make hybrid-up
```

Then use separate terminals as needed:

```bash
make backend     # FastAPI API at http://localhost:8000/docs
make frontend    # Vite development server at http://localhost:5173
make worker      # Optional ARQ worker; requires Redis
make mcp         # Optional read-only MCP server at http://localhost:8789
```

Use `make hybrid-down` to stop the hybrid services. For a fully containerized
development stack, use `make dev-up` and `make dev-down` instead.

### Access points

- Frontend: <http://localhost:5173>
- API / Swagger: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- MCP: <http://localhost:8789>

## Development Commands

The root Makefile is the stable local interface. Use `make help` to see every
available target.

```bash
# Deterministic, locked installs
make install
make install-backend
make install-frontend
make install-mcp

# Quality checks (lint, format, and contract verification do not rewrite source)
make check-frontend
make check-mcp
make services-up       # PostgreSQL and Redis, required before backend checks
make check-backend
make check             # All three checks; therefore also needs PostgreSQL
make ci                # Local CI wrappers; therefore also needs PostgreSQL

# Explicit source-changing maintenance commands
make lint-fix
make format

# Security scans
make security
make bandit
make pip-audit
make npm-audit
```

`make check-backend`, and consequently `make check` and `make ci`, exercise the
backend test suite against a running PostgreSQL service. Tests can write to the
configured database, so use a dedicated local or disposable test database. The
checks do not run Alembic migrations or reset the database; on a newly created
database, apply migrations before testing:

```bash
cd backend && uv run alembic upgrade head
```

`make check-frontend` and `make check-mcp` do not require the application
database. Use `make lint` and `make format-check` for verification-only
maintenance checks; use the explicit fix commands only when you intend to
rewrite source files.

## Repository Structure

```text
backend/                 FastAPI service, Alembic migrations, pipeline, and tests
frontend/                Vue 3 + TypeScript application and Playwright/Vitest tests
mcp/                     Read-only FastMCP sidecar and generated API contract
scrapers/literature/     Independently locked scraper project
scrapers/diagnostics/    Legacy diagnostics utility (not root-managed)
docker-compose*.yml      Development, service-only, and production stacks
.planning/               Design and execution records
```

`scrapers/diagnostics` is a legacy utility with no dependency manifest,
lockfile, or test gate. It is deliberately excluded from root installation and
checks until a dedicated packaging modernization adds those guarantees.

## Guidance for Contributors and Agents

Read [AGENTS.md](AGENTS.md) for the shared repository guidance: architecture,
component boundaries, safe generated-data handling, verification, and
multi-agent handoffs. `CLAUDE.md` is only a small bridge to that source of
truth.

## Versioning

This project uses two independent version streams:

- **Code**: SemVer (`0.5.1`) — tagged releases with the Zenodo software DOI.
- **Data**: CalVer (`YYYY.MM`) — API-mediated data releases with dataset DOIs.

## Citation

If you use the Kidney-Genetics Database, please cite:

> Kidney-Genetics Database (v0.5.1). DOI: [10.5281/zenodo.19316248](https://doi.org/10.5281/zenodo.19316248)

See [CITATION.cff](CITATION.cff) for full citation metadata.

## License

MIT License — see [LICENSE](LICENSE).
