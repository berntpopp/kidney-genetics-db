# Gene Annotations Feature - TODO

## 📊 Current Status
**Overall Progress**: ~85% Complete

### ✅ Completed Phases
- **Phase 1**: Database Foundation - DONE
- **Phase 2**: Base Infrastructure - DONE  
- **Phase 3**: HGNC Integration - DONE
- **Phase 4**: gnomAD Integration - DONE
- **Phase 5**: API Endpoints - DONE
- **Phase 6**: Update Pipeline - DONE
- **Phase 7**: Integration & Optimization - DONE (Core features)

### 🚧 Remaining Work
- **Phase 7**: Integration with existing curation pipeline (optional)
- **Phase 8**: Documentation & Deployment (not started)

### 🎯 Key Achievements
- ✅ Full annotation pipeline with HGNC and gnomAD sources
- ✅ Automated scheduling with APScheduler (4 active jobs)
- ✅ Caching layer with Redis/in-memory fallback
- ✅ 20+ API endpoints for management and queries
- ✅ Performance: <10ms cached response times
- ✅ Materialized views for fast access
- ✅ Progress tracking integration
- ✅ Error recovery and retry mechanisms

## Overview
Implement extensible gene annotation system with HGNC and gnomAD data sources.

**Feature Branch**: `feature/gene-annotations`  
**Target Completion**: 3 weeks  
**Priority**: High
**Status**: 85% Complete - Core functionality operational

---

## Phase 1: Database Foundation (Days 1-3) ✅
**Goal**: Set up database schema and models for annotation storage

### Database Tasks
- [x] Create Alembic migration for annotation tables
  - [x] `gene_annotations` table with JSONB storage
  - [x] `annotation_sources` registry table
  - [x] `annotation_history` audit table
  - [x] Add indexes for performance
- [x] Create SQLAlchemy models
  - [x] `GeneAnnotation` model in `backend/app/models/gene_annotation.py`
  - [x] `AnnotationSource` model
  - [x] `AnnotationHistory` model
  - [x] Update `Gene` model relationships
- [x] Create materialized view for fast access
  - [x] `gene_annotations_summary` view
  - [x] Include commonly queried fields (pLI, oe_lof, etc.)
  - [x] Add refresh mechanism

### Testing
- [x] Test migration up/down
- [x] Test model relationships
- [x] Test JSONB queries

---

## Phase 2: Base Infrastructure (Days 4-5) ✅
**Goal**: Create base classes and utilities for annotation sources

### Core Components
- [x] Create base annotation source class
  - [x] `backend/app/pipeline/sources/annotations/base.py`
  - [x] ~~Inherit from `UnifiedDataSource`~~ (Created standalone base class)
  - [x] Define abstract methods
  - [x] Implement common functionality
- [x] Create annotation utilities
  - [x] Version management
  - [x] Data validation helpers
  - [x] Update tracking
- [x] Add configuration
  - [x] ~~Add annotation sources to `datasource_config`~~ (Self-registering in DB)
  - [x] Configure TTL settings
  - [x] ~~Add feature flags~~ (Using is_active in DB)

### Testing
- [x] ~~Unit tests for base class~~ (Integration tested)
- [x] Test inheritance patterns
- [ ] Test caching behavior (caching temporarily disabled)

---

## Phase 3: HGNC Integration (Days 6-8) ✅
**Goal**: Implement HGNC annotation source

### Implementation
- [x] Create HGNC annotation source
  - [x] `backend/app/pipeline/sources/annotations/hgnc.py`
  - [x] Implement REST API queries
  - [x] Parse MANE Select data
  - [x] Handle all HGNC fields
- [x] Integrate with existing HGNC client
  - [x] ~~Reuse `HGNCClientCached`~~ (Created dedicated implementation)
  - [x] Extend for annotation-specific fields
  - [x] Add batch processing
- [x] Implement update pipeline
  - [x] Single gene updates
  - [x] Batch updates
  - [x] Progress tracking

### Data Fields
- [x] Core identifiers (NCBI Gene, Ensembl)
- [x] MANE Select transcripts
- [x] Previous/alias symbols
- [x] Gene families and groups
- [x] Chromosomal locations

### Testing
- [x] Test API integration
- [x] Test data parsing
- [x] Test error handling
- [x] Test batch processing

---

## Phase 4: gnomAD Integration (Days 9-11) ✅
**Goal**: Implement gnomAD constraint score source

### Implementation
- [x] Create gnomAD annotation source
  - [x] `backend/app/pipeline/sources/annotations/gnomad.py`
  - [x] Implement GraphQL queries
  - [x] Use gene symbol query approach
  - [x] ~~Add transcript fallback~~ (Added ExAC fallback)
- [x] GraphQL query implementation
  - [x] Gene constraint query
  - [x] Transcript constraint query
  - [x] Proper error handling
  - [x] Response parsing
- [x] Cache optimization
  - [x] 30-day TTL for constraint scores
  - [ ] Batch caching strategy (caching temporarily disabled)
  - [ ] Cache invalidation (caching temporarily disabled)

### Data Fields
- [x] Constraint scores (pLI, oe_lof, lof_z)
- [x] Missense scores (oe_mis, mis_z)
- [x] Synonymous scores (oe_syn, syn_z)
- [x] Observation/expectation counts
- [x] Confidence intervals

### Testing
- [x] Test GraphQL queries
- [x] Test constraint score parsing
- [ ] Test MANE Select integration (deferred)
- [x] Test parallel batch processing

---

## Phase 5: API Endpoints (Days 12-14) ✅
**Goal**: Create REST API for annotation management

### Endpoints ✅
- [x] Query endpoints
  - [x] `GET /api/annotations/genes/{gene_id}/annotations` - Get all annotations
  - [x] `GET /api/annotations/genes/{gene_id}/annotations/summary` - Get annotation summary
  - [x] `GET /api/annotations/sources` - List sources
  - [x] `POST /api/annotations/batch` - Batch retrieval (implemented)
  - [ ] `GET /api/annotations/search` - Search by values (deferred)
- [x] Management endpoints
  - [x] `POST /api/annotations/genes/{gene_id}/annotations/update` - Trigger update
  - [x] `GET /api/annotations/statistics` - Statistics
  - [x] `POST /api/annotations/refresh-view` - Refresh materialized view
- [x] Pipeline endpoints
  - [x] `POST /api/annotations/pipeline/update` - Trigger pipeline update
  - [x] `GET /api/annotations/pipeline/status` - Get pipeline status
  - [x] `POST /api/annotations/pipeline/validate` - Validate annotations
- [x] Scheduler endpoints
  - [x] `GET /api/annotations/scheduler/jobs` - List scheduled jobs
  - [x] `POST /api/annotations/scheduler/trigger/{job_id}` - Manually trigger job
- [x] Cache endpoints
  - [x] `GET /api/annotations/cache/stats` - Get cache statistics
  - [x] `DELETE /api/annotations/cache/clear` - Clear all cache
  - [x] `DELETE /api/annotations/cache/gene/{gene_id}` - Invalidate gene cache
- [x] CRUD operations
  - [x] Create annotation records (via update endpoints)
  - [x] Update existing annotations (via update endpoints)
  - [x] Delete outdated annotations (automatic via unique constraint)
  - [x] Audit trail logging (via AnnotationHistory)

### Schema/Serialization
- [x] Create response formats
  - [x] Annotation response structure
  - [x] Source list response
  - [x] Statistics response
  - [ ] ~~Pydantic schemas~~ (Using dict responses)

### Testing ✅
- [x] Test all endpoints
- [ ] Test authentication/authorization (not implemented yet)
- [x] Test error responses
- [x] Test batch operations (implemented and tested)

---

## Phase 6: Update Pipeline (Days 15-16) ✅
**Goal**: Implement automated update system

### Pipeline Components ✅
- [x] Main pipeline orchestrator
  - [x] `backend/app/pipeline/annotation_pipeline.py`
  - [x] Source coordination
  - [x] Error recovery
  - [x] Progress tracking
- [x] Update strategies
  - [x] Full update (all genes)
  - [x] Incremental update (changed genes)
  - [x] Forced refresh
  - [x] Selective source updates
- [x] Scheduling
  - [x] Weekly HGNC updates
  - [x] Monthly gnomAD updates
  - [x] Manual trigger option
  - [x] Daily incremental updates
  - [x] Weekly full updates

### Testing ✅
- [x] Test update pipeline
- [x] Test error recovery
- [x] Test progress tracking
- [x] Test materialized view refresh

---

## Phase 7: Integration & Optimization (Days 17-19) ✅
**Goal**: Integrate with existing system and optimize performance

### Scheduling & Automation ✅
- [x] Implemented scheduler (`backend/app/core/scheduler.py`)
  - [x] APScheduler integration
  - [x] Daily incremental updates at 2 AM
  - [x] Weekly full updates on Sundays at 3 AM
  - [x] Source-specific schedules (HGNC weekly, gnomAD monthly)
  - [x] API endpoints for job management
  - [x] Manual trigger support

### Caching Strategy ✅
- [x] Implemented caching layer (`backend/app/core/cache.py`)
  - [x] Redis-based cache with in-memory fallback
  - [x] Cache for annotations and summaries
  - [x] Cache invalidation on updates
  - [x] Cache management API endpoints
  - [x] TTL-based expiration
  - [x] Performance improvement verified

### Integration Tasks
- [ ] Update gene curation pipeline
  - [ ] Include annotation data in curation
  - [ ] Update evidence aggregation
  - [ ] Modify scoring algorithms
- [ ] Migrate existing data
  - [ ] Move constraint_scores from gene_curations
  - [ ] Populate annotation_sources table
  - [ ] Backfill annotation history
- [ ] Update existing endpoints
  - [ ] Include annotations in gene responses
  - [ ] Add annotation filters
  - [ ] Update search functionality

### Performance Optimization ✅
- [x] Query optimization via materialized views
- [x] Caching layer for frequent queries
  - [x] In-memory cache with Redis support
  - [x] Cache hit/miss tracking
  - [x] Performance improvement verified (9.2ms cached vs 11.8ms uncached)
- [x] Cache tuning
  - [x] TTL values configured (1hr annotations, 2hr summaries)
  - [x] Cache invalidation on updates
  - [x] Cache statistics monitoring
- [x] Batch processing
  - [x] Batch retrieval endpoint implemented
  - [x] Parallel processing for sources
  - [x] Batch size limits (100 genes max)

### Testing
- [ ] Performance testing
- [ ] Load testing
- [ ] Integration testing
- [ ] End-to-end testing

---

## Phase 8: Documentation & Deployment (Days 20-21)
**Goal**: Document and prepare for deployment

### Documentation
- [ ] API documentation
  - [ ] Update OpenAPI specs
  - [ ] Document all endpoints
  - [ ] Add usage examples
- [ ] Developer documentation
  - [ ] How to add new sources
  - [ ] Architecture overview
  - [ ] Troubleshooting guide
- [ ] User documentation
  - [ ] Feature overview
  - [ ] Data sources explained
  - [ ] Update schedule

### Deployment Preparation
- [ ] Environment configuration
  - [ ] Update .env.example
  - [ ] Document required variables
  - [ ] Set production values
- [ ] Migration plan
  - [ ] Test migration on staging
  - [ ] Backup procedures
  - [ ] Rollback plan
- [ ] Monitoring setup
  - [ ] Add metrics collection
  - [ ] Set up alerts
  - [ ] Create dashboards

### Final Testing
- [ ] System testing
- [ ] User acceptance testing
- [ ] Security review
- [ ] Performance validation

---

## Success Criteria
- [x] HGNC annotations working for all test genes
- [x] gnomAD constraint scores successfully retrieved
- [x] <100ms response time for annotation queries (achieved ~10ms with cache)
- [x] Successful automated updates (scheduler running with 4 jobs)
- [x] No breaking changes to existing APIs
- [ ] Test coverage >80% for new code (limited test coverage)

---

## Notes & Considerations

### Technical Debt
- Consider adding more annotation sources in future (ClinVar, GTEx, etc.)
- May need to implement GraphQL endpoint for flexible queries
- Consider adding annotation versioning for reproducibility

### Risks
- gnomAD API rate limiting
- Large JSONB fields may impact performance
- Need to handle genes without MANE Select transcripts

### Dependencies
- Existing HGNC client implementation
- Unified cache service
- Database migration system

### Future Enhancements
- Add ClinVar pathogenicity scores
- Add GTEx expression data
- Add protein interaction data
- Implement custom user annotations
- Add annotation comparison tools

---

## Team Assignment
- **Backend Development**: Primary developer
- **Database**: DBA consultation for schema review
- **Testing**: QA for integration testing
- **DevOps**: Deployment and monitoring setup

---

## Progress Tracking
Use GitHub Issues/Projects to track individual tasks.
Daily updates in team standup.
Weekly progress review with stakeholders.