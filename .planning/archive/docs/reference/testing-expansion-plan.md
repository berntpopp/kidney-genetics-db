# Testing Expansion Plan - Remaining Work

## Status: Active Development
**Last Updated**: 2025-10-03
**Completion**: ~40% (Infrastructure done, expansion needed)

## Overview
Core test infrastructure is complete with 1,121 lines of test code covering API endpoints and authentication. This plan focuses on expanding test coverage to include advanced testing patterns identified in the comprehensive testing plan.

## ✅ Already Completed (Infrastructure)

### Test Foundation
- ✅ Pytest configuration with async support
- ✅ Test fixtures (database, client, auth)
- ✅ Test data factories (GeneFactory, UserFactory)
- ✅ API integration tests (genes, auth)
- ✅ Test organization following Test Diamond pattern

**Evidence**:
- `backend/tests/fixtures/` - 3 fixture modules
- `backend/tests/factories.py` - Realistic test data generation
- `backend/tests/api/` - Gene and auth endpoint tests
- Total: ~1,121 lines of test infrastructure

## 🚧 Remaining Work (Prioritized)

### Priority 1: Pipeline Source Tests (High Value)
**Effort**: 2-3 days | **Value**: High | **Risk**: Medium

Test annotation sources with real API interactions (mocked externally):

```python
# backend/tests/pipeline/test_clinvar_source.py
# backend/tests/pipeline/test_hpo_source.py
# backend/tests/pipeline/test_panelapp_source.py
```

**Why Important**: Validates data ingestion pipeline correctness

**Blockers**: None - infrastructure ready

---

### Priority 2: E2E Critical Flows (Production Validation)
**Effort**: 1-2 days | **Value**: High | **Risk**: Low

Test complete user workflows end-to-end:

```python
# backend/tests/e2e/test_data_pipeline_flow.py
- Complete pipeline execution
- Progress monitoring via WebSocket
- Data validation post-update

# backend/tests/e2e/test_user_authentication_flow.py
- Registration → Login → Protected resource access
- Token refresh flows
- Role-based access verification
```

**Why Important**: Validates critical business processes work together

**Blockers**: None - infrastructure ready

---

### Priority 3: Property-Based Testing (Edge Case Discovery)
**Effort**: 1 day | **Value**: Medium | **Risk**: Low

Use Hypothesis for automated edge case discovery:

```python
# backend/tests/core/test_validators.py
@given(st.text(min_size=1, max_size=20))
def test_gene_symbol_validation(symbol):
    # Tests 100s of random inputs automatically
    ...

@given(st.floats(min_value=-1.0, max_value=2.0))
def test_evidence_score_bounds(score):
    # Finds edge cases in score validation
    ...
```

**Why Important**: Finds edge cases manual testing misses

**Blockers**: Need to add `hypothesis` dependency

---

### Priority 4: Performance Testing (Load Validation)
**Effort**: 2 days | **Value**: Medium | **Risk**: Medium

Use Locust for realistic load testing:

```python
# backend/tests/performance/test_load.py
class APIUser(HttpUser):
    @task(3)
    def list_genes(self):
        # Most common operation
        ...

    @task(1)
    def filter_genes(self):
        # Complex filtering
        ...
```

**Run**: `locust -f test_load.py --headless -u 50 -r 5 -t 60s`

**Why Important**: Validates performance under realistic load

**Blockers**: Need to add `locust` dependency and configure

---

### Priority 5: Contract Testing (API Schema Validation)
**Effort**: 1 day | **Value**: Low-Medium | **Risk**: Low

Validate API responses match OpenAPI schemas:

```python
# backend/tests/api/test_contracts.py
async def test_gene_response_schema(async_client, openapi_spec):
    response = await async_client.get("/api/genes")
    schema = openapi_spec["paths"]["/api/genes"]["get"]["responses"]["200"]
    validate(instance=response.json(), schema=schema)
```

**Why Important**: Prevents API contract breaking changes

**Blockers**: Need to generate/export OpenAPI spec first

---

## Implementation Timeline

### Week 1: Pipeline Source Tests
- [ ] Set up API mocking patterns
- [ ] Test ClinVar annotation source
- [ ] Test HPO annotation source
- [ ] Test PanelApp annotation source

### Week 2: E2E + Property-Based
- [ ] Implement data pipeline E2E flow
- [ ] Implement auth flow E2E test
- [ ] Add Hypothesis property-based tests
- [ ] Validate edge case coverage

### Week 3: Performance + Contract
- [ ] Set up Locust
- [ ] Create realistic load scenarios
- [ ] Establish baseline metrics
- [ ] Add contract tests

## Success Metrics

### Coverage Goals (Pragmatic)
- **Pipeline Sources**: 60% coverage (focus on happy path + critical errors)
- **E2E Flows**: 2-3 critical user journeys covered
- **Property Tests**: Core validators covered
- **Performance**: Baseline established, no regressions

### What NOT to Test
- ❌ Pydantic model validation (already tested by Pydantic)
- ❌ Database ORM operations (covered by integration tests)
- ❌ Third-party library behavior (trust dependencies)
- ❌ 100% code coverage (diminishing returns after 70-80%)

## Dependencies to Add

```toml
# pyproject.toml additions needed
[project.optional-dependencies]
test = [
    # Already have these:
    "pytest",
    "pytest-asyncio",
    "httpx",
    "factory-boy",
    "faker",

    # Need to add:
    "hypothesis",        # Property-based testing
    "locust",           # Performance testing
    "jsonschema",       # Contract testing
]
```

## Notes

### Test Pyramid → Test Diamond
Following the Test Diamond pattern (not pyramid):
- 20% Unit tests (pure business logic)
- **60% Integration tests** (API + services) ← Already done!
- 20% E2E tests (critical flows)

### Async Testing
All async patterns already working:
- HTTPX AsyncClient with ASGI transport ✅
- Proper async fixtures ✅
- Database transaction handling ✅

### Current Test Execution
```bash
# Run existing tests
make test              # All tests
make test-integration  # API tests (working)

# Will add when expansion complete
make test-e2e          # E2E flows
make test-performance  # Load tests
```

## Risks & Mitigations

### Risk 1: Flaky Tests
**Mitigation**: Use proper fixtures with transaction rollback, avoid time-dependent assertions

### Risk 2: Slow Test Suite
**Mitigation**: Session-scoped DB, parallel execution, smart test isolation

### Risk 3: Over-Testing
**Mitigation**: Focus on value - test behavior not implementation

## Related Documents

- ✅ `docs/implementation-notes/completed/testing-implementation-summary-COMPLETED.md` - Infrastructure completion summary
- 📚 `docs/archive/reference/comprehensive-testing-plan.md` - Full testing methodology reference
- ✅ `docs/implementation-notes/completed/annotations-system-COMPLETED.md` - Annotation system to test

---

**Next Action**: Implement Priority 1 (Pipeline Source Tests) - highest value, no blockers
