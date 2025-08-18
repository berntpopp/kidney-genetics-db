# Kidney Genetics Database - Backend

FastAPI-based backend for the Kidney Genetics Database.

## Quick Start

```bash
# Install dependencies with uv
uv venv
source .venv/bin/activate

# For development (allows package updates):
uv sync

# For production/CI (uses exact versions from lock file):
uv sync --frozen

# Start PostgreSQL
docker compose -f ../docker-compose.services.yml up -d

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

## Dependency Management

This project uses `uv` for dependency management with a lock file (`uv.lock`) to ensure reproducible builds.

### Installing Dependencies

- **Development**: Use `uv sync` to install dependencies and allow updates
- **Production/CI**: Use `uv sync --frozen` to install exact versions from the lock file
- **Adding new packages**: Use `uv add <package>` which updates both `pyproject.toml` and `uv.lock`

### Lock File

The `uv.lock` file contains exact versions of all dependencies and their transitive dependencies. This ensures:
- Reproducible builds across different environments
- Consistent dependency versions in CI/CD
- Protection against unexpected updates

**Important**: Always commit `uv.lock` changes when updating dependencies.

## Development

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Type checking
mypy app/

# Run tests
pytest
```