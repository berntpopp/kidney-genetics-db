# Testing Guide for Kidney-Genetics Database

## Overview

This project implements comprehensive testing following the **Test Diamond pattern** with focus on:
- **20% Unit Tests**: Fast, isolated tests for pure business logic
- **60% Integration Tests**: API endpoints, database, cache, and service layer
- **20% E2E Tests**: Complete user workflows and critical paths

## Prerequisites

### Required System Packages

Tests require PostgreSQL development packages for pytest-postgresql:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-server-dev-all libpq-dev

# Fedora/RHEL
sudo dnf install postgresql-devel

# macOS
brew install postgresql
```

### Python Dependencies

All test dependencies are automatically installed with:

```bash
uv sync --dev
```

Key testing libraries:
- **pytest** (7.4+): Test framework
- **pytest-asyncio**: Async test support
- **pytest-postgresql**: Database isolation
- **pytest-cov**: Coverage reporting
- **factory-boy**: Test data factories
- **faker**: Realistic fake data
- **hypothesis**: Property-based testing
- **httpx**: Async HTTP client for API tests

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run with coverage
make test-coverage
```

### Test Categories

```bash
# Unit tests only (fastest)
make test-unit

# Integration tests (API + pipeline)
make test-integration

# End-to-end tests
make test-e2e

# Critical tests only (smoke test)
make test-critical

# Re-run only failed tests
make test-failed
```

### Direct pytest Commands

```bash
# Run specific test file
uv run pytest tests/api/test_genes.py -v

# Run specific test class
uv run pytest tests/api/test_genes.py::TestGeneEndpoints -v

# Run specific test method
uv run pytest tests/api/test_genes.py::TestGeneEndpoints::test_list_genes_basic -v

# Run tests matching pattern
uv run pytest -k "test_auth" -v

# Run tests with marker
uv run pytest -m "integration" -v
uv run pytest -m "unit" -v
uv run pytest -m "e2e" -v
```

## Test Structure

```
tests/
├── api/                    # Integration tests for API endpoints
│   ├── test_genes.py      # Gene API tests (15+ test cases)
│   └── test_auth.py       # Authentication & RBAC tests
├── pipeline/              # Pipeline integration tests
│   └── test_annotation_sources.py  # Annotation sources
├── e2e/                   # End-to-end workflows
│   └── test_critical_flows.py     # Critical user journeys
├── core/                  # Unit tests
│   ├── test_validators.py         # Property-based tests
│   └── test_retry_utils.py        # Retry logic tests
├── fixtures/              # Shared test utilities
│   ├── database.py       # DB session fixtures
│   ├── client.py         # HTTPX AsyncClient
│   └── auth.py           # User fixtures
├── factories.py          # Test data factories
└── conftest.py          # Global pytest configuration
```

## Test Fixtures

### Database Fixtures

```python
def test_with_database(db_session):
    """Use database session with automatic rollback."""
    gene = Gene(symbol="PKD1", hgnc_id="HGNC:8945")
    db_session.add(gene)
    db_session.commit()
    # Automatically rolled back after test
```

### API Client Fixtures

```python
async def test_api_endpoint(async_client):
    """Test API with clean client."""
    response = await async_client.get("/api/genes")
    assert response.status_code == 200

async def test_authenticated_endpoint(authenticated_client):
    """Test with user authentication."""
    response = await authenticated_client.get("/api/auth/me")
    assert response.status_code == 200

async def test_admin_endpoint(admin_client):
    """Test with admin privileges."""
    response = await admin_client.get("/api/admin/users")
    assert response.status_code == 200
```

### User Fixtures

Available fixtures:
- `test_user`: Basic public user
- `admin_user`: Admin user
- `curator_user`: Curator user
- `inactive_user`: Inactive user
- `multiple_users`: Batch of 10 users

### Cache Fixtures

```python
async def test_with_cache(cache):
    """Test with clean cache service."""
    await cache.set("key", "value", namespace="test")
    value = await cache.get("key", namespace="test")
    assert value == "value"
```

## Test Data Factories

### Using Factories

```python
from tests.factories import GeneFactory, UserFactory

def test_with_factory_data(db_session):
    # Create single gene
    gene = GeneFactory.create(_session=db_session)

    # Create batch of genes
    genes = GeneFactory.create_batch(10, _session=db_session)

    # Create with specific attributes
    gene = GeneFactory.create(
        symbol="PKD1",
        classification="definitive",
        _session=db_session
    )
```

### Batch Helpers

```python
from tests.factories import GeneFactoryBatch, UserFactoryBatch

def test_kidney_panel(db_session):
    # Create kidney disease genes
    genes = GeneFactoryBatch.create_kidney_panel(db_session, count=10)

    # Create genes with varying evidence
    genes = GeneFactoryBatch.create_with_varying_evidence(db_session, count=20)

    # Create users with specific roles
    users = UserFactoryBatch.create_role_distribution(
        db_session,
        admins=1,
        curators=3,
        public=6
    )
```

## Property-Based Testing

Tests use Hypothesis for property-based testing to explore edge cases:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=50))
def test_gene_validation(symbol):
    """Test gene validation with random inputs."""
    result = is_likely_gene_symbol(symbol)
    assert isinstance(result, bool)
```

Run property-based tests:
```bash
uv run pytest tests/core/test_validators.py -v
```

## Coverage Reports

### Generate Coverage

```bash
# HTML report
make test-coverage

# Open report
open backend/htmlcov/index.html  # macOS
xdg-open backend/htmlcov/index.html  # Linux
```

### Coverage Goals

| Component | Target | Rationale |
|-----------|--------|-----------|
| API Endpoints | 70% | Focus on critical paths |
| Authentication | 80% | Security-critical |
| Data Pipeline | 60% | Test key flows |
| Business Logic | 85% | Pure functions are easy |
| Models/CRUD | 40% | Tested via integration |

## Test Markers

Available markers:
- `@pytest.mark.unit`: Unit tests without dependencies
- `@pytest.mark.integration`: Tests requiring database
- `@pytest.mark.e2e`: End-to-end workflows
- `@pytest.mark.slow`: Tests taking >1s
- `@pytest.mark.critical`: Must-pass for deployment

Use markers to run specific test types:
```bash
pytest -m "unit"              # Fast unit tests
pytest -m "not slow"          # Skip slow tests
pytest -m "integration"       # Integration tests only
pytest -m "critical"          # Critical tests only
```

## Writing New Tests

### Integration Test Template

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
class TestNewFeature:
    """Test new feature."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Create test data."""
        # Setup code here
        pass

    @pytest.mark.asyncio
    async def test_feature(self, async_client: AsyncClient):
        """Test the feature."""
        response = await async_client.get("/api/new-feature")
        assert response.status_code == 200
```

### Unit Test Template

```python
import pytest

@pytest.mark.unit
class TestUtilityFunction:
    """Test utility function."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = utility_function(input_data)
        assert result == expected_output

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple cases."""
        assert utility_function(input) == expected
```

## Continuous Integration

Tests run automatically on GitHub Actions for all PRs and commits to main.

### CI Configuration

See `.github/workflows/test.yml` for CI setup.

### Pre-commit Testing

Run tests before committing:
```bash
# Quick smoke test
make test-critical

# Full test suite
make test

# With coverage
make test-coverage
```

## Troubleshooting

### PostgreSQL Issues

```bash
# Check if pg_config is available
pg_config --version

# Install PostgreSQL dev packages
sudo apt-get install postgresql-server-dev-all
```

### Test Collection Errors

```bash
# Check for import errors
uv run pytest --collect-only

# Run with verbose output
uv run pytest -vv --tb=short
```

### Slow Tests

```bash
# Skip slow tests
pytest -m "not slow"

# Run with timing
pytest --durations=10
```

### Database Connection Issues

```bash
# Verify database is running
make status

# Reset database
make db-reset

# Clean database
make db-clean
```

## Best Practices

### DO ✅
- Write integration tests for API endpoints
- Use factories for test data
- Test behavior, not implementation
- Keep tests independent
- Use meaningful test names
- Test happy path + key error cases
- Use property-based tests for validators

### DON'T ❌
- Test framework code (FastAPI, SQLAlchemy)
- Mock everything (test real components)
- Create test dependencies between tests
- Leave flaky tests
- Chase 100% coverage
- Test private methods directly
- Copy-paste test code (use fixtures)

## Performance Tips

1. **Use test markers** to run only relevant tests during development
2. **Run critical tests first** for fast feedback
3. **Use pytest-xdist** for parallel execution (coming soon)
4. **Keep database tests fast** with proper fixtures
5. **Mock external API calls** in unit tests

## Getting Help

- Check test output: `pytest -vv --tb=short`
- Review existing tests for patterns
- See docs/implementation/comprehensive-testing-plan.md for strategy
- Ask in GitHub discussions

## Example Test Session

```bash
# Start development
make hybrid-up

# Run tests during development
make test-unit              # Fast feedback
make test-integration       # API changes
make test-e2e              # Before commit

# Check coverage
make test-coverage

# Run critical tests
make test-critical

# Clean up
make hybrid-down
```

---

**Note**: These tests follow the comprehensive testing plan in `docs/implementation/comprehensive-testing-plan.md`. All tests use existing unified systems (UnifiedLogger, CacheService, retry_with_backoff) to avoid duplication and maintain DRY principles.