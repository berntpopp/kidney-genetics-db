# Kidney-Genetics Database

[![CI](https://github.com/kidney-genetics-org/kidney-genetics-db/actions/workflows/ci.yml/badge.svg)](https://github.com/kidney-genetics-org/kidney-genetics-db/actions/workflows/ci.yml)
[![Security](https://github.com/kidney-genetics-org/kidney-genetics-db/actions/workflows/security.yml/badge.svg)](https://github.com/kidney-genetics-org/kidney-genetics-db/actions/workflows/security.yml)
[![Release](https://img.shields.io/github/v/release/kidney-genetics-org/kidney-genetics-db?label=release)](https://github.com/kidney-genetics-org/kidney-genetics-db/releases/latest)
[![Website](https://img.shields.io/badge/web-kidney--genetics.org-blue)](https://kidney-genetics.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![DOI](https://zenodo.org/badge/1029597888.svg)](https://doi.org/10.5281/zenodo.19316248)

The Kidney-Genetics Database curates kidney-disease genes and the evidence behind
them. It integrates 5,080+ genes from 17 sources (among them PanelApp, ClinGen,
GenCC, HPO, gnomAD, ClinVar, GTEx and PubTator) into an evidence score, with
provenance-aware annotations and a staging-to-curated ingestion pipeline. It
modernizes the original [kidney-genetics R pipeline](https://github.com/kidney-genetics-org/kidney-genetics-v1)
as a reproducible web application: a FastAPI/PostgreSQL backend, a Vue 3
frontend and a read-only [MCP](mcp/README.md) server for AI assistants.

Use it without installing anything at [kidney-genetics.org](https://kidney-genetics.org/).
Research use only.

## Quick start

Needs `uv`, Node.js >= 22.22.2 and Docker Compose v2.

```bash
git clone https://github.com/kidney-genetics-org/kidney-genetics-db.git
cd kidney-genetics-db
make install                     # locked backend, frontend and MCP dependencies
cp backend/.env.example backend/.env   # set DATABASE_URL, POSTGRES_PASSWORD, JWT_SECRET_KEY, ADMIN_PASSWORD
make hybrid-up                   # PostgreSQL + Redis
(cd backend && uv run alembic upgrade head)
make backend                     # API at http://localhost:8000/docs
make frontend                    # UI at http://localhost:5173
```

`make help` lists every target; `make check` runs the full quality gate.

## Containers

Each release publishes the backend, frontend and MCP images to GHCR with the
immutable `X.Y.Z` tag and the moving `X.Y` and `X` series tags. Pin `X.Y.Z`
for a reproducible deployment:

```bash
docker pull ghcr.io/kidney-genetics-org/kidney-genetics-db/backend:0.33.3
docker pull ghcr.io/kidney-genetics-org/kidney-genetics-db/frontend:0.33.3
docker pull ghcr.io/kidney-genetics-org/kidney-genetics-db/mcp:0.33.3
```

## Documentation

- [Development guide](docs/development.md): prerequisites, setup, commands, repository layout, versioning
- [AGENTS.md](AGENTS.md): architecture, component boundaries and verification rules for contributors and coding agents
- Component guides: [backend](backend/README.md), [frontend](frontend/README.md), [MCP server](mcp/README.md)
- Interactive API reference (Swagger): [kidney-genetics.org/docs](https://kidney-genetics.org/docs)

Related repositories in [kidney-genetics-org](https://github.com/kidney-genetics-org):
[kidney-genetics-v1](https://github.com/kidney-genetics-org/kidney-genetics-v1) (original R pipeline),
[nephro_candidate_score](https://github.com/kidney-genetics-org/nephro_candidate_score) and
[nc-scorer](https://github.com/kidney-genetics-org/nc-scorer) (Nephro Candidate Score).

## Citing

If you use the Kidney-Genetics Database, please cite the software archive:

> Kidney-Genetics Database. Zenodo. [doi:10.5281/zenodo.19316248](https://doi.org/10.5281/zenodo.19316248)

GitHub's "Cite this repository" button reads [`CITATION.cff`](CITATION.cff).

## License

Released under the [MIT License](LICENSE). Issues and pull requests are welcome in the
[issue tracker](https://github.com/kidney-genetics-org/kidney-genetics-db/issues).
