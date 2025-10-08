# Comprehensive Testing Framework Design & Assessment

**Date**: October 8, 2025
**Status**: 🔨 ACTIVE - Design Phase
**Authors**: Senior Development Team
**Review**: Architecture & Best Practices Analysis

---

## 📋 Executive Summary

This document provides a comprehensive assessment of the current testing infrastructure and proposes a modern, production-ready testing framework for the Kidney Genetics Database application. The framework follows the **Testing Trophy** pattern (Kent C. Dodds), emphasizing integration tests while maintaining coverage across all layers, and strictly adheres to **DRY, KISS, SOLID**, and modularization principles already established in the codebase.

### Current State
- **Backend**: Basic pytest infrastructure with ~35 test files, good fixtures, but **limited coverage** (~30%)
- **Frontend**: **NO testing infrastructure** - critical gap
- **Architecture**: Mixed patterns, some e2e tests but no consistent strategy

### Proposed State
- **Backend**: Comprehensive pytest-based suite with **70-80% coverage target**
- **Frontend**: Modern Vitest + Vue Test Utils framework from scratch
- **Architecture**: Testing Trophy pattern with clear layer separation and reusable utilities

---

## 🎯 Testing Philosophy: The Testing Trophy

### Why Testing Trophy Over Pyramid?

After extensive research (Kent C. Dodds 2024, web.dev testing strategies), we adopt the **Testing Trophy** approach:

```
         ╱─────────╲
        │  E2E/UI   │  ← 10% - Critical user flows only
        │───────────│
       │ Integration │  ← 60% - Most valuable (THIS IS KEY)
       │─────────────│
      │   Unit      │  ← 25% - Business logic, utilities
      │─────────────│
     │    Static    │  ← 5% - TypeScript, linting, Ruff
     ╲─────────────╱
```

### Key Principles

1. **Integration tests provide maximum confidence** - Test components working together
2. **Test behavior, not implementation** - Resist testing internal details
3. **Avoid test fragility** - Tests should survive refactoring
4. **Fast feedback loops** - Run tests in <30 seconds locally
5. **DRY in test utilities** - Reuse fixtures, factories, and mocks

### Alignment with Testing Trophy Values

| Layer | Coverage | Rationale | Current Gap |
|-------|----------|-----------|-------------|
| Static | 5% | TypeScript types, linting (Ruff backend, ESLint frontend) | ✅ Have Ruff/ESLint |
| Unit | 25% | Pure functions, utilities, business logic | ⚠️ Partial (~15%) |
| Integration | 60% | API endpoints, database, component interactions | ❌ Major gap (~10%) |
| E2E | 10% | Critical user journeys | ⚠️ Skeleton only (~5%) |

---

## 🔍 Current State Analysis

### Backend Testing (Python/FastAPI/PostgreSQL)

#### ✅ Strengths

1. **Excellent Fixture Architecture**
   - `pytest-postgresql` for isolated database tests
   - Clean fixture hierarchy (`conftest.py`, `fixtures/` directory)
   - Proper transaction rollback after each test
   ```python
   # backend/tests/conftest.py - GOOD EXAMPLE
   @pytest.fixture(scope="function")
   def db_session(postgresql):
       engine = create_engine(connection_string, poolclass=NullPool)
       session = TestingSessionLocal()
       trans = session.begin()
       yield session
       trans.rollback()  # Clean rollback
   ```

2. **Factory Pattern Implementation**
   - Using Factory Boy (`tests/factories.py`)
   - Realistic test data generation with Faker
   - Batch creation helpers (`GeneFactoryBatch`, `UserFactoryBatch`)
   - **GOOD**: Follows DRY principle perfectly

3. **Comprehensive Cache Testing**
   - `test_cache_service.py` - 440 lines, 14 test classes
   - Tests L1/L2 cache layers, TTL, namespace isolation
   - Concurrency and performance tests included
   - **EXEMPLARY** - should be template for other tests

4. **Async Test Support**
   - Proper use of `@pytest.mark.asyncio`
   - `AsyncClient` for API testing
   - Event loop fixtures configured correctly

#### ❌ Weaknesses & Gaps

1. **Severely Limited Coverage (~30%)**
   - **Missing**:
     - API endpoint tests (only `test_genes.py`, `test_auth.py`)
     - Pipeline source testing (only `test_annotation_sources.py`)
     - CRUD operations testing
     - WebSocket testing
     - Background task testing
   - **Impact**: Production bugs not caught until runtime

2. **No Performance/Load Testing**
   - Missing benchmarks for critical paths
   - No load testing for concurrent users
   - No memory leak detection
   - **Gap**: Can't verify <50ms API response targets

3. **Incomplete E2E Coverage**
   - `test_critical_flows.py` exists but many tests skip with `pytest.skip()`
   - No actual WebSocket flow testing
   - Missing curator/admin workflow tests
   - **Gap**: Can't verify complete user journeys

4. **No Test Organization Strategy**
   - Tests scattered without clear categorization
   - No markers for slow vs fast tests
   - No test selection strategy (smoke, regression, full)
   - **Impact**: Can't run targeted test suites efficiently

5. **Missing Fixtures**
   - No `async_client` fixture defined
   - No `curator_client` or `admin_client` fixtures for auth testing
   - No mock fixtures for external APIs
   - **Impact**: Tests duplicate setup code (violates DRY)

### Frontend Testing (Vue 3/Vuetify/Vite)

#### ❌ Critical State: NO TESTING INFRASTRUCTURE

1. **Zero Test Files**
   - No Vitest configuration
   - No test files (*.spec.js, *.test.js)
   - No component tests
   - No E2E tests
   - **CRITICAL GAP**: Entire frontend untested

2. **No Testing Dependencies**
   - Missing `vitest`, `@vitest/ui`
   - Missing `@vue/test-utils`
   - Missing `happy-dom` or `jsdom`
   - Missing `@testing-library/vue`
   - **Blocker**: Can't even start writing tests

3. **Configuration Gaps**
   - `vite.config.js` has no test configuration
   - No test environment setup
   - No coverage reporting setup
   - **Impact**: No infrastructure to support testing

#### ⚠️ Existing Assets (Can Leverage)

1. **Clean Component Architecture**
   - Well-structured Vue components in `src/components/`
   - Composables pattern for reusability
   - Pinia stores for state management
   - **Advantage**: Components should be testable

2. **API Service Layer**
   - Centralized API calls in `src/api/`
   - **Advantage**: Easy to mock for component tests

---

## 🏗️ Proposed Architecture

### Backend Testing Framework

#### Layer 1: Unit Tests (25% coverage target)

**Purpose**: Test pure functions, utilities, business logic in isolation

**Structure**:
```
backend/tests/
├── unit/
│   ├── core/
│   │   ├── test_cache_service.py          ✅ EXISTS (excellent)
│   │   ├── test_retry_utils.py            ✅ EXISTS
│   │   ├── test_validators.py             ✅ EXISTS
│   │   ├── test_security.py               📝 NEW
│   │   └── test_logging.py                📝 NEW
│   ├── pipeline/
│   │   ├── test_gene_normalization.py     ✅ EXISTS
│   │   ├── test_scoring_engine.py         📝 NEW
│   │   └── test_evidence_aggregation.py   📝 NEW
│   └── utils/
│       ├── test_string_utils.py           📝 NEW
│       └── test_date_utils.py             📝 NEW
```

**Test Example** (following existing pattern):
```python
# backend/tests/unit/core/test_security.py
import pytest
from app.core.security import verify_password, get_password_hash

class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_different_each_time(self):
        """Verify salt makes each hash unique."""
        password = "SecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2  # Different due to salt

    def test_verify_correct_password(self):
        """Verify correct password validates."""
        password = "TestPass123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Verify incorrect password fails."""
        password = "TestPass123!"
        hashed = get_password_hash(password)

        assert verify_password("WrongPass!", hashed) is False
```

#### Layer 2: Integration Tests (60% coverage target)

**Purpose**: Test API endpoints, database interactions, service integration

**Structure**:
```
backend/tests/
├── integration/
│   ├── api/
│   │   ├── test_genes_endpoints.py        ✅ EXISTS (expand)
│   │   ├── test_auth_endpoints.py         ✅ EXISTS (expand)
│   │   ├── test_statistics_endpoints.py   📝 NEW
│   │   ├── test_admin_endpoints.py        📝 NEW
│   │   ├── test_ingestion_endpoints.py    📝 NEW
│   │   └── test_websocket_progress.py     📝 NEW
│   ├── pipeline/
│   │   ├── test_annotation_pipeline_integration.py  📝 NEW
│   │   ├── test_panelapp_source.py        📝 NEW
│   │   ├── test_hpo_source.py             📝 NEW
│   │   └── test_pubtator_source.py        📝 NEW
│   └── database/
│       ├── test_views.py                  ✅ EXISTS
│       ├── test_transactions.py           📝 NEW
│       └── test_migrations.py             📝 NEW
```

**Test Example** (following testing trophy):
```python
# backend/tests/integration/api/test_statistics_endpoints.py
import pytest
from httpx import AsyncClient
from tests.factories import GeneFactoryBatch

@pytest.mark.integration
class TestStatisticsEndpoints:
    """Integration tests for statistics API - 60% of test suite."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Create realistic test data distribution."""
        self.genes = GeneFactoryBatch.create_with_varying_evidence(
            db_session, count=100
        )

    @pytest.mark.asyncio
    async def test_source_overlaps_calculation(self, async_client: AsyncClient):
        """Test source overlap statistics calculation."""
        response = await async_client.get(
            "/api/statistics/source-overlaps",
            params={"filter[hide_zero_scores]": "true"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "overlaps" in data
        assert "total_genes" in data

        # Verify data integrity
        assert data["total_genes"] > 0
        for overlap in data["overlaps"]:
            assert overlap["count"] <= data["total_genes"]
```

#### Layer 3: E2E Tests (10% coverage target)

**Purpose**: Test complete user workflows end-to-end

**Structure**:
```
backend/tests/
├── e2e/
│   ├── test_critical_flows.py            ✅ EXISTS (expand)
│   ├── test_researcher_workflow.py       📝 NEW
│   ├── test_curator_workflow.py          📝 NEW
│   ├── test_admin_workflow.py            📝 NEW
│   └── test_pipeline_execution.py        📝 NEW
```

**Test Example**:
```python
# backend/tests/e2e/test_researcher_workflow.py
@pytest.mark.e2e
@pytest.mark.critical
class TestResearcherCompleteJourney:
    """E2E test for complete researcher workflow - 10% of suite."""

    @pytest.mark.asyncio
    async def test_browse_search_export_workflow(
        self, async_client: AsyncClient, db_session
    ):
        """Test: Browse → Search → Filter → View Details → Export."""
        # Step 1: Browse genes (public, no auth)
        response = await async_client.get("/api/genes", params={"limit": 10})
        assert response.status_code == 200
        genes = response.json()["items"]

        # Step 2: Search for kidney genes
        response = await async_client.get(
            "/api/genes", params={"search": "PKD"}
        )
        assert response.status_code == 200
        pkd_genes = response.json()["items"]
        assert len(pkd_genes) > 0

        # Step 3: View gene details with annotations
        gene_id = pkd_genes[0]["hgnc_id"]
        response = await async_client.get(
            f"/api/genes/{gene_id}",
            params={"include_annotations": True}
        )
        assert response.status_code == 200
        assert "annotations" in response.json()

        # Step 4: Export filtered results
        response = await async_client.get(
            "/api/genes/export",
            params={"format": "csv", "evidence_score_min": 0.7}
        )
        # Test completes the full workflow
```

#### Key Backend Infrastructure Additions

1. **Shared Fixtures Module** (`backend/tests/fixtures/shared.py`):
```python
"""Shared fixtures following DRY principle."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def async_client() -> AsyncClient:
    """Async HTTP client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
async def authenticated_client(async_client: AsyncClient) -> AsyncClient:
    """Authenticated client with valid token."""
    # Login and add token to headers
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpass"}
    )
    token = response.json()["access_token"]
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client

@pytest.fixture
async def admin_client(async_client: AsyncClient) -> AsyncClient:
    """Admin authenticated client."""
    # Login as admin
    response = await async_client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "adminpass"}
    )
    token = response.json()["access_token"]
    async_client.headers["Authorization"] = f"Bearer {token}"
    return async_client
```

2. **Test Markers** (`backend/pytest.ini`):
```ini
[pytest]
markers =
    unit: Unit tests - fast, isolated
    integration: Integration tests - database required
    e2e: End-to-end tests - slow, full stack
    slow: Tests that take >5 seconds
    critical: Critical path tests for smoke testing
    api: API endpoint tests
    pipeline: Data pipeline tests
    requires_external: Tests requiring external API access
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

3. **Coverage Configuration** (`backend/.coveragerc`):
```ini
[run]
source = app
omit =
    app/tests/*
    app/main.py
    app/alembic/*

[report]
precision = 2
skip_covered = False
skip_empty = True

[html]
directory = htmlcov
```

### Frontend Testing Framework

#### Complete Setup from Scratch

**Step 1: Install Dependencies**

```bash
cd frontend
npm install --save-dev \
  vitest \
  @vitest/ui \
  @vue/test-utils \
  happy-dom \
  @testing-library/vue \
  @testing-library/user-event \
  @vitest/coverage-v8 \
  msw \
  vitest-mock-extended
```

**Step 2: Configure Vitest** (`frontend/vitest.config.js`):
```javascript
import { defineConfig, mergeConfig } from 'vite'
import { configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'happy-dom',
      setupFiles: ['./tests/setup.js'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        exclude: [
          'node_modules/',
          'tests/',
          '**/*.spec.js',
          '**/*.test.js',
        ],
        thresholds: {
          lines: 70,
          functions: 70,
          branches: 70,
          statements: 70
        }
      },
      include: ['src/**/*.{test,spec}.js'],
      testTimeout: 10000,
    },
  })
)
```

**Step 3: Test Setup File** (`frontend/tests/setup.js`):
```javascript
import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Create Vuetify instance for all tests
const vuetify = createVuetify({
  components,
  directives,
})

// Global test config
config.global.plugins = [vuetify]
config.global.mocks = {
  $t: (key) => key, // Mock i18n if used
}

// Mock window.matchMedia (needed for Vuetify)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
```

#### Layer 1: Component Tests (50% of frontend tests)

**Structure**:
```
frontend/
├── src/
│   └── components/
│       ├── genes/
│       │   ├── GeneCard.vue
│       │   └── GeneCard.spec.js           📝 NEW
│       ├── statistics/
│       │   ├── SourceOverlapChart.vue
│       │   └── SourceOverlapChart.spec.js 📝 NEW
│       └── auth/
│           ├── LoginForm.vue
│           └── LoginForm.spec.js          📝 NEW
```

**Test Example** (Vuetify component):
```javascript
// frontend/src/components/genes/GeneCard.spec.js
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import GeneCard from './GeneCard.vue'

describe('GeneCard.vue', () => {
  let vuetify
  let wrapper

  beforeEach(() => {
    // Create fresh Vuetify instance for each test
    vuetify = createVuetify({ components, directives })
  })

  afterEach(() => {
    if (wrapper) wrapper.unmount()
  })

  it('renders gene symbol correctly', () => {
    const gene = {
      symbol: 'PKD1',
      hgnc_id: 'HGNC:9008',
      evidence_score: 0.95,
      classification: 'definitive'
    }

    wrapper = mount(GeneCard, {
      props: { gene },
      global: { plugins: [vuetify] }
    })

    expect(wrapper.text()).toContain('PKD1')
  })

  it('displays evidence score badge with correct color', () => {
    const gene = {
      symbol: 'PKD1',
      evidence_score: 0.95,
      classification: 'definitive'
    }

    wrapper = mount(GeneCard, {
      props: { gene },
      global: { plugins: [vuetify] }
    })

    // Find v-chip component
    const chip = wrapper.findComponent({ name: 'VChip' })
    expect(chip.exists()).toBe(true)
    expect(chip.text()).toContain('0.95')
    // High score should be green
    expect(chip.props('color')).toBe('success')
  })

  it('emits click event when card is clicked', async () => {
    const gene = { symbol: 'PKD1', hgnc_id: 'HGNC:9008' }

    wrapper = mount(GeneCard, {
      props: { gene },
      global: { plugins: [vuetify] }
    })

    await wrapper.find('[data-testid="gene-card"]').trigger('click')

    expect(wrapper.emitted('geneSelected')).toBeTruthy()
    expect(wrapper.emitted('geneSelected')[0][0]).toEqual(gene)
  })
})
```

#### Layer 2: Integration Tests (30% of frontend tests)

**Test composables and stores with API mocking**:

```javascript
// frontend/src/stores/genes.spec.js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useGenesStore } from './genes'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

const mockGenes = [
  { symbol: 'PKD1', hgnc_id: 'HGNC:9008', evidence_score: 0.95 },
  { symbol: 'PKD2', hgnc_id: 'HGNC:9009', evidence_score: 0.92 },
]

// Mock API server using MSW (Mock Service Worker)
const server = setupServer(
  http.get('/api/genes', () => {
    return HttpResponse.json({
      items: mockGenes,
      total: 2,
      offset: 0,
      limit: 10
    })
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Genes Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('fetches and stores genes from API', async () => {
    const store = useGenesStore()

    await store.fetchGenes()

    expect(store.genes).toHaveLength(2)
    expect(store.genes[0].symbol).toBe('PKD1')
    expect(store.totalGenes).toBe(2)
  })

  it('handles API errors gracefully', async () => {
    // Override mock to return error
    server.use(
      http.get('/api/genes', () => {
        return new HttpResponse(null, { status: 500 })
      })
    )

    const store = useGenesStore()
    await store.fetchGenes()

    expect(store.error).toBeTruthy()
    expect(store.genes).toHaveLength(0)
  })
})
```

#### Layer 3: E2E Tests (20% of frontend tests)

**Use Playwright for full browser testing**:

```javascript
// frontend/tests/e2e/researcher-workflow.spec.js
import { test, expect } from '@playwright/test'

test.describe('Researcher Workflow', () => {
  test('complete gene search and export workflow', async ({ page }) => {
    // Navigate to app
    await page.goto('http://localhost:5173')

    // Step 1: Browse genes on home page
    await expect(page.getByRole('heading', { name: 'Genes' })).toBeVisible()

    // Step 2: Search for PKD genes
    await page.getByPlaceholder('Search genes...').fill('PKD')
    await page.keyboard.press('Enter')

    // Step 3: Verify results
    await expect(page.getByText('PKD1')).toBeVisible()

    // Step 4: Click on gene card
    await page.getByTestId('gene-card-PKD1').click()

    // Step 5: Verify gene details page
    await expect(page).toHaveURL(/\/genes\/HGNC:\d+/)
    await expect(page.getByRole('heading', { name: 'PKD1' })).toBeVisible()

    // Step 6: Check annotations loaded
    await expect(page.getByTestId('annotations-panel')).toBeVisible()
  })
})
```

---

## 🛠️ Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### Backend Tasks
- [ ] Create test infrastructure enhancements
  - [ ] Add missing fixtures (`async_client`, `admin_client`, `curator_client`)
  - [ ] Configure pytest markers in `pytest.ini`
  - [ ] Set up coverage reporting (`.coveragerc`)
  - [ ] Create `tests/fixtures/shared.py` with reusable fixtures

#### Frontend Tasks
- [ ] Install all testing dependencies
- [ ] Create `vitest.config.js` configuration
- [ ] Create `tests/setup.js` with Vuetify integration
- [ ] Add test scripts to `package.json`:
  ```json
  {
    "scripts": {
      "test": "vitest",
      "test:ui": "vitest --ui",
      "test:coverage": "vitest --coverage",
      "test:run": "vitest run"
    }
  }
  ```

### Phase 2: Integration Layer (Week 3-5)

**Priority: Integration tests first (60% of effort)**

#### Backend
- [ ] Complete API endpoint testing
  - [ ] Statistics endpoints (`test_statistics_endpoints.py`)
  - [ ] Admin endpoints (`test_admin_endpoints.py`)
  - [ ] Ingestion endpoints (`test_ingestion_endpoints.py`)
  - [ ] WebSocket progress (`test_websocket_progress.py`)

- [ ] Pipeline integration tests
  - [ ] Full annotation pipeline flow
  - [ ] Individual source tests (PanelApp, HPO, etc.)

#### Frontend
- [ ] Write component tests for all major components
  - [ ] Gene components (GeneCard, GeneList, GeneDetails)
  - [ ] Statistics components (all D3 charts)
  - [ ] Auth components (LoginForm, UserMenu)
  - [ ] Admin components (AdminDashboard, etc.)

- [ ] Write store tests
  - [ ] Genes store
  - [ ] Auth store
  - [ ] UI store

### Phase 3: Unit & E2E Layers (Week 6-7)

#### Backend Unit Tests
- [ ] Security utilities
- [ ] Logging utilities
- [ ] Scoring engine
- [ ] Evidence aggregation

#### Backend E2E Tests
- [ ] Researcher workflow
- [ ] Curator workflow
- [ ] Admin workflow
- [ ] Pipeline execution

#### Frontend E2E Tests
- [ ] Install Playwright
- [ ] Write critical user journeys
- [ ] Set up CI/CD integration

### Phase 4: CI/CD Integration (Week 8)

- [ ] GitHub Actions workflow for backend tests
- [ ] GitHub Actions workflow for frontend tests
- [ ] Coverage reporting integration
- [ ] Pre-commit hooks for running tests
- [ ] Documentation updates

---

## 📊 Success Metrics

### Coverage Targets

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Backend Unit | ~15% | 25% | HIGH |
| Backend Integration | ~10% | 60% | CRITICAL |
| Backend E2E | ~5% | 10% | MEDIUM |
| **Backend Total** | **~30%** | **70-80%** | - |
| Frontend Unit | 0% | 0% | N/A |
| Frontend Component | 0% | 50% | CRITICAL |
| Frontend Integration | 0% | 30% | HIGH |
| Frontend E2E | 0% | 20% | MEDIUM |
| **Frontend Total** | **0%** | **70-80%** | - |

### Performance Targets

- [ ] Unit tests: <5 seconds total
- [ ] Integration tests: <30 seconds total
- [ ] E2E tests: <3 minutes total
- [ ] Full test suite: <5 minutes total
- [ ] CI/CD pipeline: <10 minutes total

### Quality Targets

- [ ] Zero flaky tests (99.9% consistency)
- [ ] All tests have clear assertions
- [ ] All tests follow AAA pattern (Arrange, Act, Assert)
- [ ] 100% of critical paths covered by E2E tests
- [ ] All new features require tests (enforced in PR)

---

## 🔧 Tools & Technologies

### Backend Stack

| Tool | Purpose | Status |
|------|---------|--------|
| **pytest** | Test runner | ✅ Configured |
| **pytest-asyncio** | Async test support | ✅ Configured |
| **pytest-postgresql** | Database fixtures | ✅ Configured |
| **pytest-cov** | Coverage reporting | ⚠️ Needs config |
| **pytest-xdist** | Parallel execution | 📝 To install |
| **Factory Boy** | Test data factories | ✅ Configured |
| **Faker** | Fake data generation | ✅ Configured |
| **httpx** | Async HTTP client | ✅ Available |

### Frontend Stack

| Tool | Purpose | Status |
|------|---------|--------|
| **Vitest** | Test runner | ❌ Not installed |
| **@vue/test-utils** | Vue component testing | ❌ Not installed |
| **happy-dom** | DOM environment | ❌ Not installed |
| **@testing-library/vue** | User-centric testing | ❌ Not installed |
| **MSW** | API mocking | ❌ Not installed |
| **Playwright** | E2E testing | ❌ Not installed |
| **@vitest/ui** | Test UI | ❌ Not installed |
| **@vitest/coverage-v8** | Coverage reporting | ❌ Not installed |

---

## 🏛️ Architectural Principles Applied

### DRY (Don't Repeat Yourself)

**✅ Applied**:
- Shared fixtures in `tests/fixtures/` (backend)
- Factory pattern for test data
- Reusable test utilities
- Centralized test configuration

**Example**:
```python
# DON'T repeat this in every test file:
@pytest.fixture
def test_gene():
    return Gene(symbol="PKD1", hgnc_id="HGNC:9008")

# DO use factory:
from tests.factories import GeneFactory
gene = GeneFactory.create(symbol="PKD1")
```

### KISS (Keep It Simple, Stupid)

**✅ Applied**:
- Simple, readable test names
- Clear AAA pattern (Arrange, Act, Assert)
- Avoid over-mocking
- Test one thing at a time

**Example**:
```python
def test_password_hash_is_different_each_time():
    """Simple, focused test - does ONE thing."""
    # Arrange
    password = "test123"

    # Act
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Assert
    assert hash1 != hash2  # Clear assertion
```

### SOLID Principles

**Single Responsibility**:
- Each test tests ONE behavior
- Test classes group related tests

**Open/Closed**:
- Factories open for extension (subclassing)
- Fixtures closed for modification (stable interface)

**Liskov Substitution**:
- Mock objects substitute real objects without breaking tests

**Interface Segregation**:
- Minimal, focused fixtures
- Don't force tests to depend on unused fixtures

**Dependency Inversion**:
- Tests depend on abstractions (fixtures) not concrete implementations

### Modularization

**✅ Applied**:
- Clear directory structure (`unit/`, `integration/`, `e2e/`)
- Separate fixture files by concern
- Reusable test utilities in separate modules
- Frontend tests co-located with components

---

## 🚨 Anti-Patterns to Avoid

### Backend

1. **❌ Testing Implementation Details**
   ```python
   # BAD - tests private method
   def test_private_method():
       obj = MyClass()
       assert obj._private_method() == "value"

   # GOOD - tests public behavior
   def test_public_behavior():
       obj = MyClass()
       assert obj.public_method() == "expected_result"
   ```

2. **❌ Over-Mocking**
   ```python
   # BAD - mocks everything, tests nothing
   @patch('module.function1')
   @patch('module.function2')
   @patch('module.function3')
   def test_something(mock3, mock2, mock1):
       # This tests the mocks, not the code
       pass

   # GOOD - use real objects, mock only external dependencies
   def test_something(db_session, mock_external_api):
       # Tests real logic with real database
       pass
   ```

3. **❌ Test Interdependence**
   ```python
   # BAD - tests depend on execution order
   class TestSuite:
       def test_1_create(self):
           self.obj = create_object()

       def test_2_update(self):
           update_object(self.obj)  # Depends on test_1

   # GOOD - each test is independent
   class TestSuite:
       @pytest.fixture(autouse=True)
       def setup(self):
           self.obj = create_object()

       def test_update(self):
           update_object(self.obj)  # Independent
   ```

### Frontend

1. **❌ Testing Library Implementation**
   ```javascript
   // BAD - tests Vue internals
   it('data property is set', () => {
       expect(wrapper.vm.internalData).toBe('value')
   })

   // GOOD - tests user-visible behavior
   it('displays the value', () => {
       expect(wrapper.text()).toContain('value')
   })
   ```

2. **❌ Shallow Mounting Everything**
   ```javascript
   // BAD - shallow mount breaks Vuetify components
   const wrapper = shallowMount(Component)

   // GOOD - mount with Vuetify plugin
   const vuetify = createVuetify()
   const wrapper = mount(Component, {
       global: { plugins: [vuetify] }
   })
   ```

---

## 📝 Example: Complete Test Suite for New Feature

### Scenario: Adding "Gene Comparison" Feature

Following **Testing Trophy**, we'd write tests in this order:

#### 1. Integration Tests (60% effort first)

```python
# backend/tests/integration/api/test_gene_comparison.py
@pytest.mark.integration
class TestGeneComparisonEndpoint:
    """Integration tests for gene comparison API."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        self.gene1 = GeneFactory.create(
            symbol="PKD1",
            evidence_score=0.95,
            _session=db_session
        )
        self.gene2 = GeneFactory.create(
            symbol="PKD2",
            evidence_score=0.87,
            _session=db_session
        )
        db_session.commit()

    @pytest.mark.asyncio
    async def test_compare_two_genes(self, async_client):
        """Test comparing two genes returns comparison data."""
        response = await async_client.post(
            "/api/genes/compare",
            json={"gene_ids": [self.gene1.hgnc_id, self.gene2.hgnc_id]}
        )

        assert response.status_code == 200
        data = response.json()

        assert "comparison" in data
        assert len(data["comparison"]) == 2
        assert data["comparison"][0]["symbol"] == "PKD1"
```

#### 2. Unit Tests (25% effort)

```python
# backend/tests/unit/services/test_gene_comparison_service.py
def test_calculate_evidence_difference():
    """Test evidence score difference calculation."""
    gene1 = GeneFactory.build(evidence_score=0.95)
    gene2 = GeneFactory.build(evidence_score=0.87)

    service = GeneComparisonService()
    diff = service.calculate_evidence_difference(gene1, gene2)

    assert diff == pytest.approx(0.08, rel=0.01)
```

#### 3. Component Tests (Frontend)

```javascript
// frontend/src/components/genes/GeneComparison.spec.js
describe('GeneComparison.vue', () => {
    it('displays both genes in comparison table', () => {
        const genes = [
            { symbol: 'PKD1', evidence_score: 0.95 },
            { symbol: 'PKD2', evidence_score: 0.87 }
        ]

        const wrapper = mount(GeneComparison, {
            props: { genes },
            global: { plugins: [createVuetify()] }
        })

        expect(wrapper.text()).toContain('PKD1')
        expect(wrapper.text()).toContain('PKD2')
    })
})
```

#### 4. E2E Tests (10% effort last)

```python
# backend/tests/e2e/test_gene_comparison_workflow.py
@pytest.mark.e2e
async def test_complete_comparison_workflow(async_client, db_session):
    """Test complete gene comparison workflow."""
    # Create genes
    genes = GeneFactoryBatch.create_kidney_panel(db_session, count=5)

    # Step 1: List genes
    response = await async_client.get("/api/genes")
    assert response.status_code == 200

    # Step 2: Compare first two
    gene_ids = [genes[0].hgnc_id, genes[1].hgnc_id]
    response = await async_client.post(
        "/api/genes/compare",
        json={"gene_ids": gene_ids}
    )
    assert response.status_code == 200

    # Step 3: Export comparison
    comparison_id = response.json()["comparison_id"]
    response = await async_client.get(
        f"/api/genes/compare/{comparison_id}/export"
    )
    assert response.status_code == 200
```

---

## 🔗 References & Resources

### Official Documentation
- [Pytest Documentation](https://docs.pytest.org/) - Backend testing framework
- [Vitest Documentation](https://vitest.dev/) - Frontend testing framework
- [Vue Test Utils](https://test-utils.vuejs.org/) - Vue component testing
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/) - FastAPI-specific patterns
- [Testing Library](https://testing-library.com/docs/vue-testing-library/intro/) - User-centric testing

### Best Practices Articles
- [Kent C. Dodds - Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [Kent C. Dodds - Write Tests](https://kentcdodds.com/blog/write-tests)
- [FastAPI Async Testing 2024](https://testdriven.io/blog/fastapi-crud/)
- [Vue 3 Testing Best Practices](https://vuejs.org/guide/scaling-up/testing.html)
- [Vuetify Unit Testing](https://vuetifyjs.com/en/getting-started/unit-testing/)

### Testing Philosophy
- [Web.dev Testing Strategies](https://web.dev/articles/ta-strategies)
- [Testing Pyramid vs Trophy](https://www.baytechconsulting.com/blog/test-pyramid-vs-testing-trophy-whats-the-difference)
- [Integration Testing Benefits](https://martinfowler.com/articles/practical-test-pyramid.html)

---

## 🎯 Next Steps

### Immediate Actions (This Week)

1. **Get Team Approval** - Review this document with the team
2. **Set Up Frontend Infrastructure** - Install Vitest and dependencies
3. **Add Backend Fixtures** - Create missing shared fixtures
4. **Write First Tests** - Start with one integration test as template

### Short Term (Next 2 Weeks)

1. **Backend**: Complete API endpoint integration tests
2. **Frontend**: Write component tests for core components
3. **CI/CD**: Set up basic GitHub Actions workflow

### Long Term (Next 2 Months)

1. **Achieve 70% Coverage** - Steadily increase coverage
2. **E2E Suite**: Build critical path E2E tests
3. **Performance Testing**: Add benchmarking tests
4. **Documentation**: Write testing guide for contributors

---

## 📧 Questions & Discussion

This is a living document. For questions or suggestions:

1. Open an issue in the repo with label `testing-framework`
2. Discuss in team meetings
3. Update this document based on learnings

**Document Status**: 🔨 ACTIVE - Ready for team review and feedback

**Last Updated**: October 8, 2025
**Next Review**: Weekly during implementation phase
