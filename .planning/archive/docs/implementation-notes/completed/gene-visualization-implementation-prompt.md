# Implementation Prompt: Gene Structure & Protein Domain Visualization

**For**: Agentic LLM (Claude Code / Cursor / Copilot)
**Issue**: [#29 - Add gene structure and protein domain annotations](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Date**: 2026-01-11

---

## System Prompt

You are a senior software engineer implementing gene structure and protein domain visualization for the kidney-genetics-db project. You have access to three comprehensive implementation plans that have been expert-reviewed and API-validated.

**Your role**: Implement this feature following best practices with minimal code, maximum reuse, and production-quality standards.

---

## Phase 0: Setup (REQUIRED FIRST STEP)

### 0.1 Create Feature Branch

Before any implementation, create a feature branch for issue #29:

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create feature branch following naming convention
git checkout -b feature/29-gene-structure-visualization

# Verify branch creation
git branch --show-current
# Should output: feature/29-gene-structure-visualization
```

**Branch naming**: `feature/29-gene-structure-visualization`
- `feature/` prefix for new features
- `29` is the issue number
- `gene-structure-visualization` is a short description

**Commit strategy**:
- Make atomic commits after each phase completion
- Use conventional commit messages referencing the issue:
  ```bash
  git commit -m "feat(annotations): add Ensembl and UniProt configuration (#29)"
  git commit -m "feat(annotations): implement EnsemblAnnotationSource (#29)"
  git commit -m "feat(annotations): implement UniProtAnnotationSource (#29)"
  git commit -m "feat(frontend): add gene structure visualization page (#29)"
  git commit -m "feat(frontend): add D3 visualization components (#29)"
  ```

### 0.2 Create Progress Tracking File

Create a TODO.md file to track implementation progress:

```bash
# Create the progress tracking file
cat > docs/implementation-notes/active/gene-visualization-TODO.md << 'EOF'
# Gene Visualization Implementation Progress

**Issue**: [#29](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Branch**: `feature/29-gene-structure-visualization`
**Started**: $(date +%Y-%m-%d)
**Status**: 🚧 In Progress

---

## Planning Documents

| Document | Purpose | Status |
|----------|---------|--------|
| [gene-protein-visualization.md](./gene-protein-visualization.md) | Main implementation plan | 📖 Reference |
| [ensembl-uniprot-system-integration.md](./ensembl-uniprot-system-integration.md) | Backend integration | 📖 Reference |
| [visualization-integration-ux-analysis.md](./visualization-integration-ux-analysis.md) | Frontend UX design | 📖 Reference |
| [gene-visualization-implementation-prompt.md](./gene-visualization-implementation-prompt.md) | Implementation prompt | 📖 Reference |

---

## Implementation Phases

### Phase 0: Setup
- [ ] Create feature branch `feature/29-gene-structure-visualization`
- [ ] Create this TODO.md tracking file
- [ ] Read all planning documents

### Phase 1: Backend Configuration
- [ ] Add Ensembl config to `backend/config/annotations.yaml`
- [ ] Add UniProt config to `backend/config/annotations.yaml`
- [ ] Validate: Config loads correctly
- [ ] Commit: `feat(annotations): add Ensembl and UniProt configuration (#29)`

### Phase 2: Backend Source Classes
- [ ] Create `backend/app/pipeline/sources/annotations/ensembl.py`
  - [ ] Extend `BaseAnnotationSource`
  - [ ] Implement `_is_valid_annotation()` override
  - [ ] Use `SimpleRateLimiter` from retry_utils.py
  - [ ] Use `@retry_with_backoff` decorator
  - [ ] Implement `fetch_annotation()` and `fetch_batch()`
- [ ] Create `backend/app/pipeline/sources/annotations/uniprot.py`
  - [ ] Extend `BaseAnnotationSource`
  - [ ] Implement `_is_valid_annotation()` override
  - [ ] Use `SimpleRateLimiter` from retry_utils.py
  - [ ] Use semaphore for concurrent batch requests
  - [ ] Implement `fetch_annotation()` and `fetch_batch()`
- [ ] Validate: `make lint` passes
- [ ] Validate: `make test` passes
- [ ] Commit: `feat(annotations): implement Ensembl and UniProt annotation sources (#29)`

### Phase 3: Backend Registration
- [ ] Update `backend/app/pipeline/sources/annotations/__init__.py`
- [ ] Update `backend/app/pipeline/annotation_pipeline.py`
- [ ] Update `backend/app/api/endpoints/gene_annotations.py`
- [ ] Validate: API returns 10 annotation sources
- [ ] Commit: `feat(annotations): register Ensembl and UniProt in pipeline (#29)`

### Phase 4: Frontend Route & Page
- [ ] Add route to `frontend/src/router/index.js`
  - [ ] Add route guard for gene symbol validation
- [ ] Create `frontend/src/views/GeneStructure.vue`
  - [ ] Use unified breadcrumb system
  - [ ] Add error boundary
  - [ ] Implement D3 cleanup in `onUnmounted()`
- [ ] Validate: `npm run lint` passes
- [ ] Commit: `feat(frontend): add gene structure visualization page (#29)`

### Phase 5: Visualization Components
- [ ] Create `frontend/src/composables/useD3Tooltip.js`
- [ ] Create `frontend/src/components/visualizations/GeneStructureVisualization.vue`
  - [ ] D3-based exon/intron visualization
  - [ ] Hover tooltips
  - [ ] Cleanup in `onUnmounted()`
- [ ] Create `frontend/src/components/visualizations/ProteinDomainVisualization.vue`
  - [ ] D3-based domain visualization
  - [ ] Hover tooltips with Pfam links
  - [ ] Cleanup in `onUnmounted()`
- [ ] Validate: `npm run lint` passes
- [ ] Validate: `npm run build` passes
- [ ] Commit: `feat(frontend): add D3 visualization components (#29)`

### Phase 6: Entry Points
- [ ] Update `frontend/src/components/gene/GeneInformationCard.vue` (add link)
- [ ] Update `frontend/src/views/admin/AdminAnnotations.vue` (add filter options)
- [ ] Validate: `npm run lint` passes
- [ ] Commit: `feat(frontend): add structure links and admin filter options (#29)`

### Phase 7: Final Validation & PR
- [ ] Final validation: `make lint && make test`
- [ ] Final validation: `npm run lint && npm run build`
- [ ] Manual test: Navigate to `/genes/PKD1/structure`
- [ ] Manual test: Verify tooltips work
- [ ] Manual test: Check admin dashboard
- [ ] Push branch: `git push -u origin feature/29-gene-structure-visualization`
- [ ] Create pull request

---

## Progress Log

| Date | Phase | Notes |
|------|-------|-------|
| $(date +%Y-%m-%d) | 0 | Started implementation |

---

## Blockers & Issues

_None yet_

---

## Notes

_Implementation notes go here_
EOF
```

**Update TODO.md** after completing each task by changing `[ ]` to `[x]` and adding entries to the Progress Log.

### 0.3 Read Planning Documents

Before writing any code, read these documents in order (all in `docs/implementation-notes/active/`):

1. **`gene-protein-visualization.md`** - Main implementation plan with full source code
2. **`ensembl-uniprot-system-integration.md`** - Backend integration patterns
3. **`visualization-integration-ux-analysis.md`** - Frontend UX design
4. **`gene-visualization-implementation-prompt.md`** - This prompt (for reference)

Mark the Phase 0 tasks as complete in TODO.md before proceeding.

---

## Planning Documents (Reference)

All documents are in `docs/implementation-notes/active/`:

| Document | Purpose |
|----------|---------|
| `gene-protein-visualization.md` | Main implementation plan with full source code |
| `ensembl-uniprot-system-integration.md` | Backend integration patterns and configuration |
| `visualization-integration-ux-analysis.md` | Frontend UX design and route configuration |
| `gene-visualization-implementation-prompt.md` | This implementation prompt |
| `gene-visualization-TODO.md` | Progress tracking (created in Phase 0) |

### Key Content in Each Plan

1. **`gene-protein-visualization.md`** - Main implementation plan
   - Full source code for backend annotation sources
   - Frontend visualization components with D3.js
   - API validation results and batch performance data

2. **`docs/implementation-notes/active/ensembl-uniprot-system-integration.md`** - Backend integration
   - Configuration for `annotations.yaml`
   - Source class patterns with `_is_valid_annotation()` override
   - `SimpleRateLimiter` and semaphore usage
   - Pipeline and API endpoint registration

3. **`docs/implementation-notes/active/visualization-integration-ux-analysis.md`** - Frontend UX
   - Route configuration with validation guard
   - D3 cleanup in `onUnmounted()` for memory leak prevention
   - Error boundaries and breadcrumb integration

---

## Core Principles (MUST FOLLOW)

### 1. DRY (Don't Repeat Yourself)
- **REUSE existing systems** - See CLAUDE.md for mandatory patterns
- Use `BaseAnnotationSource` - DO NOT create annotation sources from scratch
- Use `SimpleRateLimiter` from `retry_utils.py` - DO NOT implement custom rate limiting
- Use `@retry_with_backoff` decorator - DO NOT write custom retry loops
- Use `RetryableHTTPClient` - DO NOT use raw httpx
- Use `CacheService` - DO NOT create new cache implementations
- Use `UnifiedLogger` - DO NOT use print() or logging.getLogger()
- Extract `useD3Tooltip` composable for shared tooltip logic

### 2. KISS (Keep It Simple, Stupid)
- Start with the **minimum viable implementation**
- Avoid over-engineering - no features beyond what's specified
- Simple D3 + SVG visualizations - avoid complex libraries
- Configuration over code - use `annotations.yaml`
- One component = one responsibility

### 3. SOLID Principles
- **S**ingle Responsibility: Each class/component does one thing
- **O**pen/Closed: Extend `BaseAnnotationSource`, don't modify it
- **L**iskov Substitution: New sources work with existing pipeline
- **I**nterface Segregation: Implement only required abstract methods
- **D**ependency Inversion: Inject services, don't hardcode

### 4. Modularization
- Backend: Separate files for `ensembl.py` and `uniprot.py`
- Frontend: Separate components for gene structure and protein domains
- Composables: Extract `useD3Tooltip` for tooltip logic
- Keep files under 300 lines when possible

---

## Implementation Order

Execute in this exact order, validating each phase before proceeding.

> **IMPORTANT**: After completing Phase 0 (Git Setup), commit after each subsequent phase passes validation.

### Phase 1: Backend Configuration
```bash
# Add to backend/config/annotations.yaml
# See ensembl-uniprot-system-integration.md for exact config
```

**Validate**: `cd backend && uv run python -c "from app.core.datasource_config import get_annotation_config; print(get_annotation_config('ensembl'))"`

**Commit & Update Progress**:
```bash
git add backend/config/annotations.yaml
git commit -m "feat(annotations): add Ensembl and UniProt configuration (#29)"

# Update TODO.md - mark Phase 1 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 1 | Backend configuration complete |
```

### Phase 2: Backend Source Classes
```bash
# Create:
# - backend/app/pipeline/sources/annotations/ensembl.py
# - backend/app/pipeline/sources/annotations/uniprot.py
```

**Required patterns** (from expert review):
```python
# MUST include _is_valid_annotation() override
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    if not super()._is_valid_annotation(annotation_data):
        return False
    # Source-specific validation...

# MUST use SimpleRateLimiter
from app.core.retry_utils import SimpleRateLimiter
self.rate_limiter = SimpleRateLimiter(requests_per_second=self.requests_per_second)
await self.rate_limiter.wait()

# MUST use @retry_with_backoff
@retry_with_backoff(config=RetryConfig(max_retries=5))
async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:

# MUST check status code before parsing
if response.status_code != 200:
    logger.sync_warning(...)
    return None
```

**Validate**:
```bash
make lint
make test
```

**Commit & Update Progress**:
```bash
git add backend/app/pipeline/sources/annotations/ensembl.py
git add backend/app/pipeline/sources/annotations/uniprot.py
git commit -m "feat(annotations): implement Ensembl and UniProt annotation sources (#29)"

# Update TODO.md - mark Phase 2 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 2 | Source classes implemented |
```

### Phase 3: Backend Registration
```bash
# Update:
# - backend/app/pipeline/sources/annotations/__init__.py
# - backend/app/pipeline/annotation_pipeline.py
# - backend/app/api/endpoints/gene_annotations.py
```

**Validate**:
```bash
make backend  # Start backend
curl http://localhost:8000/api/annotations/sources | jq '.data | length'
# Should return 10 (8 existing + 2 new)
```

**Commit & Update Progress**:
```bash
git add backend/app/pipeline/sources/annotations/__init__.py
git add backend/app/pipeline/annotation_pipeline.py
git add backend/app/api/endpoints/gene_annotations.py
git commit -m "feat(annotations): register Ensembl and UniProt in pipeline (#29)"

# Update TODO.md - mark Phase 3 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 3 | Backend registration complete |
```

### Phase 4: Frontend Route & Page
```bash
# Create:
# - frontend/src/views/GeneStructure.vue
# Update:
# - frontend/src/router/index.js
```

**Required patterns** (from expert review):
```javascript
// MUST add route guard
beforeEnter: async (to, from, next) => {
  const symbol = to.params.symbol
  if (!/^[A-Z0-9][A-Z0-9-]*$/i.test(symbol)) {
    next({ name: 'NotFound' })
    return
  }
  next()
}

// MUST use unified breadcrumbs
import { useBreadcrumbs } from '@/composables/useBreadcrumbs'
useBreadcrumbs([...])

// MUST clean up D3 in onUnmounted
onUnmounted(() => {
  d3.select(containerRef.value).selectAll('*').remove()
  if (resizeObserver) resizeObserver.disconnect()
  d3.selectAll('.visualization-tooltip').remove()
})
```

**Validate**:
```bash
cd frontend && npm run lint
cd frontend && npm run type-check  # If available
```

**Commit & Update Progress**:
```bash
git add frontend/src/views/GeneStructure.vue
git add frontend/src/router/index.js
git commit -m "feat(frontend): add gene structure visualization page (#29)"

# Update TODO.md - mark Phase 4 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 4 | Frontend route and page complete |
```

### Phase 5: Visualization Components
```bash
# Create:
# - frontend/src/components/visualizations/GeneStructureVisualization.vue
# - frontend/src/components/visualizations/ProteinDomainVisualization.vue
# - frontend/src/composables/useD3Tooltip.js
```

**Validate**:
```bash
cd frontend && npm run lint
cd frontend && npm run build  # Verify no build errors
```

**Commit & Update Progress**:
```bash
git add frontend/src/components/visualizations/GeneStructureVisualization.vue
git add frontend/src/components/visualizations/ProteinDomainVisualization.vue
git add frontend/src/composables/useD3Tooltip.js
git commit -m "feat(frontend): add D3 visualization components (#29)"

# Update TODO.md - mark Phase 5 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 5 | Visualization components complete |
```

### Phase 6: Entry Points (Minimal Changes)
```bash
# Update:
# - frontend/src/components/gene/GeneInformationCard.vue (add link only)
# - frontend/src/views/admin/AdminAnnotations.vue (add to sourceFilterOptions)
```

**Validate**:
```bash
cd frontend && npm run lint
make frontend  # Test manually in browser
```

**Commit & Update Progress**:
```bash
git add frontend/src/components/gene/GeneInformationCard.vue
git add frontend/src/views/admin/AdminAnnotations.vue
git commit -m "feat(frontend): add structure links and admin filter options (#29)"

# Update TODO.md - mark Phase 6 tasks as complete [x]
# Add to Progress Log: | $(date +%Y-%m-%d) | 6 | Entry points added |
```

### Phase 7: Final Validation, Push & Create Pull Request

After all phases pass validation:

```bash
# Final validation
make lint
make test
cd frontend && npm run lint && npm run build

# Manual testing
# - Navigate to /genes/PKD1/structure
# - Verify gene structure visualization renders
# - Verify protein domain visualization renders
# - Test hover tooltips on exons and domains
# - Check admin dashboard shows Ensembl/UniProt sources

# Update TODO.md - mark Phase 7 tasks as complete [x]
# Update Status to: ✅ Complete
# Add to Progress Log: | $(date +%Y-%m-%d) | 7 | All validations passed, ready for PR |

# Commit TODO.md with final status
git add docs/implementation-notes/active/gene-visualization-TODO.md
git commit -m "docs: update implementation progress tracking (#29)"

# Push branch
git push -u origin feature/29-gene-structure-visualization

# Create pull request
gh pr create --title "feat: Add gene structure and protein domain visualization" \
  --body "## Summary
Implements gene structure and protein domain visualization for issue #29.

### Changes
- **Backend**: Added Ensembl and UniProt as annotation sources
- **Frontend**: Created dedicated \`/genes/:symbol/structure\` subpage
- **Visualizations**: D3-based gene structure and protein domain components

### New Files
- \`backend/app/pipeline/sources/annotations/ensembl.py\`
- \`backend/app/pipeline/sources/annotations/uniprot.py\`
- \`frontend/src/views/GeneStructure.vue\`
- \`frontend/src/components/visualizations/GeneStructureVisualization.vue\`
- \`frontend/src/components/visualizations/ProteinDomainVisualization.vue\`
- \`frontend/src/composables/useD3Tooltip.js\`

### Documentation
- Implementation progress tracked in \`docs/implementation-notes/active/gene-visualization-TODO.md\`

## Related Issue
Closes #29

## Test Plan
- [x] \`make lint\` passes
- [x] \`make test\` passes
- [x] \`npm run lint\` passes
- [x] \`npm run build\` passes
- [ ] Navigate to /genes/PKD1/structure shows visualization
- [ ] Hover tooltips work on exons and domains
- [ ] Admin dashboard shows Ensembl/UniProt in sources list"
```

**After PR is merged**, update TODO.md:
```bash
# Update Status to: ✅ Merged
# Add to Progress Log: | $(date +%Y-%m-%d) | PR | Merged to main |
```

---

## Validation Commands (Run After Each Phase)

```bash
# Backend
make lint                    # Lint Python code with ruff
make test                    # Run pytest test suite
cd backend && uv run ruff check app/ --fix

# Frontend
cd frontend && npm run lint  # ESLint + Prettier
cd frontend && npm run build # Verify production build

# Full system
make status                  # Check all services
```

---

## Anti-Patterns to Avoid

### Backend
- ❌ Creating annotation sources without extending `BaseAnnotationSource`
- ❌ Using `apply_rate_limit()` instead of `SimpleRateLimiter`
- ❌ Missing `_is_valid_annotation()` override
- ❌ Not checking HTTP status codes before parsing JSON
- ❌ Hardcoding rate limits instead of using config
- ❌ Using `print()` or `logging.getLogger()` instead of `UnifiedLogger`
- ❌ Creating custom cache implementations
- ❌ Writing custom retry loops

### Frontend
- ❌ Adding visualizations to `GeneDetail.vue` (use dedicated subpage)
- ❌ Missing D3 cleanup in `onUnmounted()`
- ❌ Not using error boundaries for visualization failures
- ❌ Duplicating tooltip code (extract composable)
- ❌ Missing route guard for gene symbol validation
- ❌ Not using unified breadcrumb system

---

## File Checklist

### Backend (Create/Modify)
- [ ] `backend/config/annotations.yaml` - Add ensembl/uniprot config
- [ ] `backend/app/pipeline/sources/annotations/ensembl.py` - NEW
- [ ] `backend/app/pipeline/sources/annotations/uniprot.py` - NEW
- [ ] `backend/app/pipeline/sources/annotations/__init__.py` - Add exports
- [ ] `backend/app/pipeline/annotation_pipeline.py` - Register sources
- [ ] `backend/app/api/endpoints/gene_annotations.py` - Add update tasks

### Frontend (Create/Modify)
- [ ] `frontend/src/router/index.js` - Add route with guard
- [ ] `frontend/src/views/GeneStructure.vue` - NEW page
- [ ] `frontend/src/components/visualizations/GeneStructureVisualization.vue` - NEW
- [ ] `frontend/src/components/visualizations/ProteinDomainVisualization.vue` - NEW
- [ ] `frontend/src/composables/useD3Tooltip.js` - NEW composable
- [ ] `frontend/src/components/gene/GeneInformationCard.vue` - Add link
- [ ] `frontend/src/views/admin/AdminAnnotations.vue` - Add to filter options

---

## Success Criteria

1. **Backend**: `GET /api/annotations/sources` returns 10 sources (including ensembl, uniprot)
2. **Backend**: `make lint` and `make test` pass with no errors
3. **Frontend**: `npm run lint` and `npm run build` pass with no errors
4. **Functionality**: Navigate to `/genes/PKD1/structure` shows gene structure visualization
5. **Functionality**: Protein domains render with hover tooltips
6. **Admin**: Ensembl/UniProt appear in admin annotations dashboard
7. **Performance**: Initial load < 3 seconds with caching

---

## Reference Files

Read these existing files for patterns:
- `backend/app/pipeline/sources/annotations/clinvar.py` - Reference implementation
- `backend/app/core/retry_utils.py` - SimpleRateLimiter, RetryConfig
- `frontend/src/components/visualizations/D3BarChart.vue` - D3 + Vue pattern
- `frontend/src/composables/useBreadcrumbs.js` - Breadcrumb composable

---

## Notes

- APIs have been tested and validated (see gene-protein-visualization.md)
- Ensembl: POST batch with 571 genes takes ~15s (1 request)
- UniProt: OR query with 571 genes takes ~10s (6 requests)
- 30-day cache TTL is appropriate for structural data
- Use MANE Select transcripts as canonical reference

---

**Start by reading the three implementation plans, then implement Phase 1 through Phase 6 in order, validating after each phase.**
