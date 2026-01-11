# Gene Visualization Implementation Progress

**Issue**: [#29](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Branch**: `feature/29-gene-structure-visualization`
**Started**: 2026-01-11
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
- [x] Create feature branch `feature/29-gene-structure-visualization`
- [x] Create this TODO.md tracking file
- [x] Read all planning documents

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
| 2026-01-11 | 0 | Started implementation, created feature branch |

---

## Blockers & Issues

_None yet_

---

## Notes

_Implementation notes go here_
