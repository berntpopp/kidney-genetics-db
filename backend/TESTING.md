# Backend Testing Guide

## Test Environment

The backend test suite uses PostgreSQL from the repository's Docker Compose
services. Tests isolate database changes with transactions and savepoints; they
do not need a locally installed PostgreSQL server, `pg_config`, or PostgreSQL
development packages.

Install the locked backend development dependencies and start PostgreSQL and
Redis from the repository root:

```bash
make install-backend
make services-up
```

The backend process reads `backend/.env`, not the root `.env`. Create it from
the component template and set `DATABASE_URL`, `POSTGRES_PASSWORD` (use
`kidney_pass` for the default Compose service), a unique `JWT_SECRET_KEY` of at
least 32 characters, and `ADMIN_PASSWORD` before running tests:

```bash
cp backend/.env.example backend/.env
```

On a newly created local database, apply the schema before running tests:

```bash
cd backend && uv run alembic upgrade head
```

The default Compose service is reachable at
`postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics`. Tests
use `TEST_DATABASE_URL` when set, then `DATABASE_URL`, then the backend
configuration. Keep local credentials in uncommitted environment files.

## Primary Verification

Use the database-aware root quality gate for backend work:

```bash
make check-backend
```

It checks the lockfile, runs non-mutating Ruff lint and formatting checks, and
runs `uv run pytest tests/ -v`. It requires PostgreSQL to be running, does not
run Alembic migrations or reset the database, and tests may write to it; use a
dedicated local or disposable test database. Because `make check` and `make ci`
include `make check-backend`, they require the same service setup.

For a focused test run, always use the project environment:

```bash
cd backend && uv run pytest tests/test_gene_resolve.py -v
cd backend && uv run pytest tests/test_gene_resolve.py::TestResolveEndpoint::test_resolve_exact_symbol -v
cd backend && uv run pytest -k "test_auth" -v
cd backend && uv run pytest -m "integration" -v
```

## Test Categories

The historical convenience targets remain useful during focused development:

```bash
make test-unit          # Fast unit-focused selection
make test-integration   # Marked pipeline integration selection
make test-coverage      # Coverage report under backend/htmlcov/
make test-failed        # Re-run the last failures
```

These targets also need the backend environment and, where fixtures access the
database, the Compose PostgreSQL service. Start with `make check-backend` before
relying on a narrower marker selection as a release signal.

## Test Layout

```text
tests/
├── core/                Unit tests for shared utilities and configuration
├── fixtures/            Shared database, client, and authentication fixtures
├── pipeline/            Annotation and ingestion tests
├── factories.py         Test-data factories
└── conftest.py          Transactional PostgreSQL and global fixtures
```

The `tests/api/` and `tests/e2e/` packages are reserved for future suites; they
do not currently contain collected tests. Do not use their historical Make
targets as verification signals.

## Fixtures and Data

`db_session` opens a transaction for each test and rolls it back after the test.
Use factories and fixtures instead of making tests depend on state created by a
previous test. Common fixtures include `async_client`, `authenticated_client`,
`admin_client`, and `db_session`.

```python
async def test_gene_lookup(async_client):
    response = await async_client.get("/api/genes")
    assert response.status_code == 200
```

For database-backed tests, keep assertions focused on behavior, use meaningful
test names, and mock only external systems that are not the subject of the
test.

## Troubleshooting

### Database is unavailable

```bash
make services-up
make status
```

If the service is new or schema-dependent tests fail, apply migrations with
`cd backend && uv run alembic upgrade head`. Do not use `make db-reset` merely
to fix a test failure: it is destructive and recreates local data.

### Collection or import errors

```bash
cd backend && uv run pytest --collect-only
cd backend && uv run pytest -vv --tb=short
```

### Slow tests

```bash
cd backend && uv run pytest -m "not slow"
cd backend && uv run pytest --durations=10
```

## Before Handoff

Run the narrowest relevant test first, then `make check-backend` for backend
changes. Report the exact command, whether PostgreSQL was running, and any
remaining failure; do not treat a skipped database fixture as a passing
integration test.
