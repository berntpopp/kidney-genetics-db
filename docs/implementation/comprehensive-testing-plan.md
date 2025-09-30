# Comprehensive Testing Plan for Kidney-Genetics Database

## Executive Summary

This testing plan implements modern testing best practices for 2024, avoiding common antipatterns. Following the **Test Diamond pattern** (20% unit, 60% integration, 20% E2E), this plan emphasizes practical, maintainable tests over coverage metrics, with focus on async patterns, proper transaction handling, and real-world testing scenarios.

## Key Testing Principles

### ❌ Common Antipatterns to Avoid
1. **Test Pyramid → Test Diamond**: More integration tests, fewer brittle unit tests
2. **Mock Everything → Test Real Components**: Use real DB, cache, services where possible
3. **Coverage Obsession → Quality Focus**: Meaningful tests over 95% coverage targets
4. **Sync/Async Mixing → Proper Async Testing**: Correct async patterns throughout
5. **Flaky Performance Tests → Proper Load Testing**: Use specialized tools, not loops

### ✅ Modern Patterns Added
1. **Session-scoped DB with nested transactions** for speed
2. **HTTPX AsyncClient** for true async testing
3. **Property-based testing** for edge cases
4. **Contract testing** for API schemas
5. **Test data factories** with Factory Boy

## Testing Philosophy

### Test Diamond Distribution (Optimal for APIs)
```
     /\
    /  \     20% E2E Tests (Critical User Flows)
   /    \
  /      \
 /        \  60% Integration Tests (API & Service Layer)
/          \
------------  20% Unit Tests (Pure Business Logic Only)
```

### Why Test Diamond Over Pyramid?
- **Integration tests catch 80% of bugs** in API applications
- Unit tests often test implementation details that change frequently
- E2E tests verify critical business flows without overdoing UI testing
- Better ROI on testing effort for data pipeline applications

## Testing Architecture

### 1. Test Organization (Mirror App Structure)

```
backend/tests/
├── conftest.py                    # Global fixtures & configuration
├── factories.py                   # Test data factories
├── fixtures/                      # Shared fixtures
│   ├── database.py               # Session-scoped DB with transactions
│   ├── client.py                 # HTTPX AsyncClient setup
│   └── auth.py                   # Auth token generators
├── api/                          # API endpoint tests (integration)
│   ├── test_auth.py
│   ├── test_genes.py
│   └── test_admin.py
├── pipeline/                     # Pipeline tests (integration)
│   ├── test_annotation_pipeline.py
│   └── sources/
│       ├── test_panelapp.py
│       └── test_clinvar.py
├── core/                         # Core utility tests (unit)
│   ├── test_retry_utils.py
│   └── test_security.py
├── e2e/                          # End-to-end workflows
│   └── test_critical_flows.py
└── performance/                  # Performance benchmarks
    └── test_load.py
```

## Implementation Patterns

### 1. Database Fixture with Proper Transaction Handling

```python
# tests/fixtures/database.py
"""Session-scoped database with nested transactions for test isolation"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.core.cache_service import get_cache_service

@pytest.fixture(scope="session")
def db_engine():
    """Create database engine once per test session"""
    # Use in-memory SQLite for speed with proper settings
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Share connection across threads
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db_engine):
    """Provide DB session with automatic rollback after each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    # Nested transaction for test isolation
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            # Restart nested transaction after rollback
            nonlocal nested
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
async def cache(db_session):
    """Provide clean cache service"""
    service = get_cache_service(db_session)
    await service.clear_all()
    return service
```

### 2. Async Client Setup (Proper Pattern)

```python
# tests/fixtures/client.py
"""HTTPX AsyncClient for true async testing"""
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator

from app.main import app
from app.core.dependencies import get_db

@pytest.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async client with dependency overrides"""

    # Override database dependency
    app.dependency_overrides[get_db] = lambda: db_session

    # Use HTTPX with ASGI transport for true async testing
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,  # Longer timeout for complex operations
    ) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
async def authenticated_client(async_client, test_user) -> AsyncClient:
    """Client with authentication headers"""
    from app.core.security import create_access_token

    token = create_access_token({"sub": test_user.username})
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client
```

### 3. Test Data Factories (DRY & Maintainable)

```python
# tests/factories.py
"""Test data factories using Factory Boy"""
import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from app.models.gene import Gene, GeneStaging
from app.models.user import User

fake = Faker()

class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with session management"""
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "commit"

class GeneFactory(BaseFactory):
    """Gene factory with realistic data"""
    class Meta:
        model = Gene

    symbol = factory.LazyFunction(lambda: f"GENE{fake.random_int(1, 9999)}")
    hgnc_id = factory.LazyAttribute(lambda o: f"HGNC:{hash(o.symbol) % 100000}")
    ensembl_gene_id = factory.LazyAttribute(lambda o: f"ENSG{fake.random_number(11)}")

    # Realistic evidence scores
    evidence_score = factory.LazyFunction(lambda: fake.pyfloat(min_value=0.1, max_value=1.0))
    classification = factory.fuzzy.FuzzyChoice(["definitive", "strong", "moderate", "limited"])

    # JSONB data with structure
    annotations = factory.LazyFunction(
        lambda: {
            "panelapp": {"confidence": fake.random_element([3, 2, 1])},
            "clinvar": {"pathogenic": fake.random_int(0, 10)},
            "omim": {"mim_number": fake.random_number(6)}
        }
    )

class UserFactory(BaseFactory):
    """User factory with hashed passwords"""
    class Meta:
        model = User

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(
        lambda: get_password_hash(fake.password())
    )
    role = factory.fuzzy.FuzzyChoice(["admin", "curator", "public"])
    is_active = True
```

### 4. Integration Tests (60% of Tests)

```python
# tests/api/test_genes.py
"""Gene API integration tests - the bulk of our testing"""
import pytest
from httpx import AsyncClient

from tests.factories import GeneFactory

class TestGeneEndpoints:
    """Test gene API endpoints with real database"""

    @pytest.fixture(autouse=True)
    async def setup(self, db_session):
        """Create test data for each test"""
        self.genes = GeneFactory.create_batch(20, _session=db_session)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_list_genes_with_filters(self, async_client: AsyncClient):
        """Test gene listing with complex filters"""
        response = await async_client.get("/api/genes", params={
            "evidence_score_min": 0.5,
            "classification": "definitive",
            "limit": 10
        })

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "items" in data
        assert "total" in data
        assert "offset" in data

        # Verify filtering worked
        for gene in data["items"]:
            assert gene["evidence_score"] >= 0.5
            assert gene["classification"] == "definitive"

    @pytest.mark.asyncio
    async def test_gene_detail_caching(self, async_client: AsyncClient, cache):
        """Test that gene details are properly cached"""
        gene = self.genes[0]

        # First request - cache miss
        response1 = await async_client.get(f"/api/genes/{gene.hgnc_id}")
        assert response1.status_code == 200

        # Verify cache was populated
        cached = await cache.get(f"genes:{gene.hgnc_id}", namespace="api")
        assert cached is not None

        # Second request - should use cache
        response2 = await async_client.get(f"/api/genes/{gene.hgnc_id}")
        assert response2.json() == response1.json()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_param,value", [
        ("evidence_score_min", "not_a_number"),
        ("limit", -1),
        ("offset", "abc"),
    ])
    async def test_invalid_parameters(self, async_client: AsyncClient, invalid_param, value):
        """Test parameter validation"""
        response = await async_client.get("/api/genes", params={invalid_param: value})
        assert response.status_code == 422
        assert "detail" in response.json()
```

### 5. Pipeline Testing with Proper Async Handling

```python
# tests/pipeline/test_annotation_pipeline.py
"""Test annotation pipeline without blocking event loop"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.pipeline.annotation_pipeline import AnnotationPipeline

class TestAnnotationPipeline:
    """Test pipeline orchestration"""

    @pytest.mark.asyncio
    async def test_non_blocking_execution(self, db_session):
        """Verify pipeline doesn't block event loop"""
        pipeline = AnnotationPipeline(db_session)

        # Start pipeline task
        task = asyncio.create_task(pipeline.run_pipeline())

        # Verify we can execute other operations
        start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.01)  # Should complete quickly
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed < 0.02  # Should not be blocked

        # Cancel pipeline
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_retry_logic_integration(self, db_session):
        """Test retry logic with circuit breaker"""
        from app.core.retry_utils import RetryConfig, CircuitBreaker

        pipeline = AnnotationPipeline(db_session)

        # Mock a failing source
        with patch.object(pipeline.sources[0], 'fetch_annotation') as mock_fetch:
            mock_fetch.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                {"data": "success"}  # Third attempt succeeds
            ]

            # Should retry and eventually succeed
            result = await pipeline._fetch_with_retry(
                pipeline.sources[0],
                {"symbol": "PKD1"}
            )

            assert result == {"data": "success"}
            assert mock_fetch.call_count == 3
```

### 6. Property-Based Testing for Edge Cases

```python
# tests/core/test_gene_validation.py
"""Property-based testing with Hypothesis"""
import pytest
from hypothesis import given, strategies as st
from hypothesis import assume

from app.core.validators import validate_gene_symbol

class TestGeneValidation:
    """Property-based tests for gene validation"""

    @given(st.text(min_size=1, max_size=20))
    def test_gene_symbol_validation(self, symbol):
        """Test gene symbol validation with random inputs"""
        assume(symbol.strip())  # Skip empty strings

        try:
            result = validate_gene_symbol(symbol)
            # If validation passes, verify format
            assert result.isupper()
            assert not any(c in result for c in "!@#$%^&*()")
        except ValueError:
            # If validation fails, ensure it's for valid reason
            assert any([
                len(symbol) > 15,
                symbol[0].isdigit(),
                not symbol.replace("-", "").replace("_", "").isalnum()
            ])

    @given(
        st.floats(min_value=-1.0, max_value=2.0),
        st.sampled_from(["definitive", "strong", "moderate", "limited", "invalid"])
    )
    def test_evidence_score_bounds(self, score, classification):
        """Test evidence score validation"""
        from app.models.gene import validate_evidence

        is_valid = validate_evidence(score, classification)

        if is_valid:
            assert 0 <= score <= 1
            assert classification in ["definitive", "strong", "moderate", "limited"]
        else:
            assert score < 0 or score > 1 or classification == "invalid"
```

### 7. Contract Testing for API Schemas

```python
# tests/api/test_contracts.py
"""Contract testing for API schemas"""
import pytest
import json
from jsonschema import validate
from pathlib import Path

class TestAPIContracts:
    """Ensure API responses match documented schemas"""

    @pytest.fixture
    def openapi_spec(self):
        """Load OpenAPI specification"""
        with open("openapi.json") as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_gene_response_schema(self, async_client, openapi_spec):
        """Test gene endpoint matches OpenAPI schema"""
        response = await async_client.get("/api/genes")

        # Get schema from OpenAPI spec
        schema = openapi_spec["paths"]["/api/genes"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

        # Validate response matches schema
        validate(instance=response.json(), schema=schema)

    @pytest.mark.asyncio
    async def test_all_endpoints_documented(self, async_client):
        """Ensure all routes are documented"""
        from app.main import app

        # Get OpenAPI schema from app
        openapi = await async_client.get("/openapi.json")
        paths = openapi.json()["paths"]

        # Get all app routes
        app_routes = [route.path for route in app.routes if hasattr(route, "endpoint")]

        # Verify all routes are documented
        for route in app_routes:
            # Convert path params to OpenAPI format
            openapi_path = route.replace("{", "{").replace("}", "}")
            assert openapi_path in paths or route in ["/openapi.json", "/docs", "/redoc"]
```

### 8. E2E Tests for Critical Flows (20%)

```python
# tests/e2e/test_critical_flows.py
"""End-to-end tests for critical business flows"""
import pytest
from httpx import AsyncClient

class TestCriticalUserFlows:
    """Test complete user workflows"""

    @pytest.mark.asyncio
    async def test_complete_data_pipeline_flow(self, async_client: AsyncClient, authenticated_client: AsyncClient):
        """Test complete pipeline execution flow"""
        # 1. Admin triggers pipeline
        response = await authenticated_client.post("/api/pipeline/start")
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # 2. Monitor progress via WebSocket
        from httpx_ws import aconnect_ws
        async with aconnect_ws(f"ws://test/ws/progress/{job_id}", async_client) as ws:
            # Receive progress updates
            message = await ws.receive_json()
            assert "progress" in message
            assert 0 <= message["progress"] <= 100

        # 3. Verify data was updated
        response = await async_client.get("/api/statistics")
        stats = response.json()
        assert stats["total_genes"] > 0
        assert stats["last_update"] is not None

    @pytest.mark.asyncio
    async def test_user_authentication_flow(self, async_client: AsyncClient):
        """Test complete authentication flow"""
        # 1. Register user
        register_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
        response = await async_client.post("/api/auth/register", json=register_data)
        assert response.status_code == 201

        # 2. Login
        login_data = {"username": "testuser", "password": "SecurePass123!"}
        response = await async_client.post("/api/auth/login", data=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"
```

### 9. Performance Testing (Separate from Unit Tests)

```python
# tests/performance/test_load.py
"""Performance testing using Locust"""
from locust import HttpUser, task, between
import json

class APIUser(HttpUser):
    """Simulate API user behavior"""
    wait_time = between(1, 3)

    def on_start(self):
        """Login and store token"""
        response = self.client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "testpass"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_genes(self):
        """Most common operation"""
        self.client.get("/api/genes?limit=20", headers=self.headers)

    @task(1)
    def get_gene_detail(self):
        """Less common operation"""
        self.client.get("/api/genes/HGNC:12345", headers=self.headers)

    @task(1)
    def filter_genes(self):
        """Complex filtering"""
        params = {
            "evidence_score_min": 0.5,
            "classification": "definitive",
            "has_panel": True
        }
        self.client.get("/api/genes", params=params, headers=self.headers)

# Run with: locust -f test_load.py --host=http://localhost:8000
```

## Testing Best Practices Implementation

### 1. Pytest Configuration

```ini
# backend/pytest.ini
[tool.pytest.ini_options]
minversion = "7.0"
asyncio_mode = "auto"  # Handle async tests automatically
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]

markers = [
    "integration: Integration tests requiring database",
    "e2e: End-to-end workflow tests",
    "slow: Tests taking >1s",
    "critical: Must-pass tests for deployment",
]

# Sane defaults
addopts = [
    "--strict-markers",
    "--tb=short",
    "--disable-warnings",
    "-vv",
    "--color=yes",
]

# Coverage settings
[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__init__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### 2. Makefile Commands

```makefile
# Testing commands
.PHONY: test test-unit test-integration test-e2e test-coverage

test:  ## Run all tests
	cd backend && uv run pytest

test-unit:  ## Run unit tests only
	cd backend && uv run pytest tests/core -v

test-integration:  ## Run integration tests
	cd backend && uv run pytest tests/api tests/pipeline -v

test-e2e:  ## Run E2E tests
	cd backend && uv run pytest tests/e2e -v --tb=long

test-coverage:  ## Run tests with coverage
	cd backend && uv run pytest --cov=app --cov-report=html --cov-report=term

test-watch:  ## Run tests in watch mode
	cd backend && uv run ptw -- -vv

test-failed:  ## Run only failed tests
	cd backend && uv run pytest --lf

test-performance:  ## Run performance tests
	cd backend && locust -f tests/performance/test_load.py --headless -u 10 -r 2 -t 30s
```

## Realistic Coverage Goals

### Coverage by Component (Pragmatic Targets)

| Component | Current | Target | Rationale |
|-----------|---------|--------|-----------|
| API Endpoints | 0% | **70%** | Focus on happy paths + key error cases |
| Authentication | 0% | **80%** | Critical security, needs good coverage |
| Data Pipeline | 0% | **60%** | Test key sources, not every edge case |
| Business Logic | 0% | **85%** | Pure functions are easy to test |
| Models/CRUD | 0% | **40%** | Tested implicitly via integration tests |
| Utilities | 95% | **90%** | Already well-tested, maintain quality |

### What NOT to Test
- **Pydantic models**: Validation is already tested by Pydantic
- **Simple CRUD**: Covered by integration tests
- **Third-party libraries**: Trust they work
- **Database migrations**: Test in staging, not unit tests
- **Configuration loading**: Test once in integration

## Implementation Timeline (Revised)

### Week 1: Foundation & Infrastructure
- [ ] Set up proper async test fixtures
- [ ] Configure pytest with async support
- [ ] Create test data factories
- [ ] Fix database transaction handling

### Week 2: Core Integration Tests (Priority)
- [ ] API endpoint integration tests (60% of effort)
- [ ] Authentication flow tests
- [ ] Pipeline source integration tests
- [ ] Cache and retry integration

### Week 3: Critical Flows & Edge Cases
- [ ] E2E tests for main user journeys
- [ ] Property-based tests for validators
- [ ] Contract tests for API schemas
- [ ] Error handling scenarios

### Week 4: Performance & Polish
- [ ] Set up Locust for load testing
- [ ] Add mutation testing with mutmut
- [ ] CI/CD integration with parallel execution
- [ ] Documentation and examples

## CI/CD Pipeline (Optimized)

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration, e2e]

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/uv
        key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}

    - name: Install dependencies
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        cd backend && uv sync --dev

    - name: Run ${{ matrix.test-type }} tests
      run: |
        cd backend
        if [ "${{ matrix.test-type }}" = "unit" ]; then
          uv run pytest tests/core -v
        elif [ "${{ matrix.test-type }}" = "integration" ]; then
          uv run pytest tests/api tests/pipeline -v
        else
          uv run pytest tests/e2e -v
        fi

    - name: Upload coverage
      if: matrix.test-type == 'integration'
      uses: codecov/codecov-action@v3
```

## Key Success Factors

### Do's ✅
1. **Test behavior, not implementation**: Focus on what, not how
2. **Use real components**: Minimize mocking, test real integrations
3. **Fast feedback**: Keep tests under 30 seconds total
4. **Clear test names**: `test_should_return_401_when_token_expired`
5. **One assertion per test**: Or logical assertion group
6. **Deterministic tests**: No random failures
7. **Test data factories**: Consistent, maintainable test data

### Don'ts ❌
1. **Don't test framework code**: FastAPI/SQLAlchemy work
2. **Don't mock everything**: Leads to false confidence
3. **Don't test private methods**: Test via public interface
4. **Don't ignore flaky tests**: Fix or remove them
5. **Don't chase 100% coverage**: Diminishing returns after 80%
6. **Don't test generated code**: Migrations, auto-generated schemas
7. **Don't mix test types**: Keep unit/integration/e2e separate

## Monitoring Test Quality

### Metrics That Matter
- **Test execution time**: <30 seconds for full suite
- **Flakiness rate**: 0% tolerance
- **Mean time to fix**: <1 day for test failures
- **Test maintenance cost**: <20% of development time
- **Bug escape rate**: <5% bugs found in production

### Metrics That Don't Matter
- **100% code coverage**: Quality > quantity
- **Number of tests**: Focus on critical paths
- **Lines of test code**: Conciseness is key

## Conclusion

This revised plan addresses critical antipatterns and implements modern testing best practices:

1. **Test Diamond over Pyramid**: 60% integration tests for maximum bug catching
2. **Real components over mocks**: Test actual behavior, not assumptions
3. **Async-first testing**: Proper HTTPX + ASGI for FastAPI
4. **Smart fixtures**: Session-scoped DB with transactions for speed
5. **Pragmatic coverage**: Focus on value, not metrics
6. **Modern patterns**: Property-based, contract, and performance testing

The result is a maintainable, fast, and reliable test suite that provides confidence without brittleness.

---
*Created for Issue #18: Comprehensive Testing Implementation*
*Focus on Test Diamond pattern, real component testing, and pragmatic coverage goals*