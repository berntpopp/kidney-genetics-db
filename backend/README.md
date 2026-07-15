# Kidney-Genetics Database Backend

The backend is a FastAPI service with SQLAlchemy, Alembic migrations,
PostgreSQL, and the curation/annotation pipeline.

## Runtime Baseline

Use Python 3.13 for local backend development and CI. The production Docker
image intentionally uses Python 3.14. The package metadata supports a wider
range, but the shared 3.13 baseline keeps local and CI behavior reproducible.

Backend integration tests need PostgreSQL. Use Docker Compose rather than
installing a system PostgreSQL server or development packages.

## Install Dependencies

From the repository root, use the deterministic component target:

```bash
make install-backend
```

The equivalent local command is:

```bash
cd backend && uv sync --locked --group dev
```

`uv.lock` records exact resolved dependencies. Commit its changes when you add
or update a dependency with `uv add`.

## Run Locally

Start the supporting services from the repository root:

```bash
make services-up
```

For a new local database, apply migrations before using the API or database
tests:

```bash
cd backend && uv run alembic upgrade head
```

Start FastAPI from the repository root:

```bash
make backend
```

The API and OpenAPI documentation are available at
<http://localhost:8000/docs>. The direct equivalent is:

```bash
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Verify Changes

With PostgreSQL running, use the root gate:

```bash
make check-backend
```

It verifies the lockfile, runs non-mutating Ruff lint and format checks, and
runs `uv run pytest tests/ -v`. It assumes the database is already available
and does not create, migrate, or reset it. `make check` and `make ci` include
this backend gate, so they require the same running PostgreSQL service.

For focused iteration:

```bash
cd backend && uv run ruff check --no-fix app/
cd backend && uv run ruff format --check app/
cd backend && uv run mypy app/
cd backend && uv run pytest tests/api/test_genes.py -v
```

Use `ruff check --fix` or `ruff format` only when you intentionally want to
rewrite files. See [TESTING.md](TESTING.md) for database-aware test workflows.
