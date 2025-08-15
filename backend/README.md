# Kidney Genetics Database - Backend

FastAPI-based backend for the Kidney Genetics Database.

## Quick Start

```bash
# Install dependencies with uv
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Start PostgreSQL
docker compose -f ../docker-compose.services.yml up -d

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

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