# Gene Annotations Feature - TODO

## Overview
Implement extensible gene annotation system with HGNC and gnomAD data sources.

**Feature Branch**: `feature/gene-annotations`  
**Target Completion**: 3 weeks  
**Priority**: High

---

## Phase 1: Database Foundation (Days 1-3)
**Goal**: Set up database schema and models for annotation storage

### Database Tasks
- [ ] Create Alembic migration for annotation tables
  - [ ] `gene_annotations` table with JSONB storage
  - [ ] `annotation_sources` registry table
  - [ ] `annotation_history` audit table
  - [ ] Add indexes for performance
- [ ] Create SQLAlchemy models
  - [ ] `GeneAnnotation` model in `backend/app/models/gene_annotation.py`
  - [ ] `AnnotationSource` model
  - [ ] `AnnotationHistory` model
  - [ ] Update `Gene` model relationships
- [ ] Create materialized view for fast access
  - [ ] `gene_annotations_summary` view
  - [ ] Include commonly queried fields (pLI, oe_lof, etc.)
  - [ ] Add refresh mechanism

### Testing
- [ ] Test migration up/down
- [ ] Test model relationships
- [ ] Test JSONB queries

---

## Phase 2: Base Infrastructure (Days 4-5)
**Goal**: Create base classes and utilities for annotation sources

### Core Components
- [ ] Create base annotation source class
  - [ ] `backend/app/pipeline/sources/annotations/base.py`
  - [ ] Inherit from `UnifiedDataSource`
  - [ ] Define abstract methods
  - [ ] Implement common functionality
- [ ] Create annotation utilities
  - [ ] Version management
  - [ ] Data validation helpers
  - [ ] Update tracking
- [ ] Add configuration
  - [ ] Add annotation sources to `datasource_config`
  - [ ] Configure TTL settings
  - [ ] Add feature flags

### Testing
- [ ] Unit tests for base class
- [ ] Test inheritance patterns
- [ ] Test caching behavior

---

## Phase 3: HGNC Integration (Days 6-8)
**Goal**: Implement HGNC annotation source

### Implementation
- [ ] Create HGNC annotation source
  - [ ] `backend/app/pipeline/sources/annotations/hgnc.py`
  - [ ] Implement REST API queries
  - [ ] Parse MANE Select data
  - [ ] Handle all HGNC fields
- [ ] Integrate with existing HGNC client
  - [ ] Reuse `HGNCClientCached`
  - [ ] Extend for annotation-specific fields
  - [ ] Add batch processing
- [ ] Implement update pipeline
  - [ ] Single gene updates
  - [ ] Batch updates
  - [ ] Progress tracking

### Data Fields
- [ ] Core identifiers (NCBI Gene, Ensembl)
- [ ] MANE Select transcripts
- [ ] Previous/alias symbols
- [ ] Gene families and groups
- [ ] Chromosomal locations

### Testing
- [ ] Test API integration
- [ ] Test data parsing
- [ ] Test error handling
- [ ] Test batch processing

---

## Phase 4: gnomAD Integration (Days 9-11)
**Goal**: Implement gnomAD constraint score source

### Implementation
- [ ] Create gnomAD annotation source
  - [ ] `backend/app/pipeline/sources/annotations/gnomad.py`
  - [ ] Implement GraphQL queries
  - [ ] Use gene symbol query approach
  - [ ] Add transcript fallback
- [ ] GraphQL query implementation
  - [ ] Gene constraint query
  - [ ] Transcript constraint query
  - [ ] Proper error handling
  - [ ] Response parsing
- [ ] Cache optimization
  - [ ] 30-day TTL for constraint scores
  - [ ] Batch caching strategy
  - [ ] Cache invalidation

### Data Fields
- [ ] Constraint scores (pLI, oe_lof, lof_z)
- [ ] Missense scores (oe_mis, mis_z)
- [ ] Synonymous scores (oe_syn, syn_z)
- [ ] Observation/expectation counts
- [ ] Confidence intervals

### Testing
- [ ] Test GraphQL queries
- [ ] Test constraint score parsing
- [ ] Test MANE Select integration
- [ ] Test parallel batch processing

---

## Phase 5: API Endpoints (Days 12-14)
**Goal**: Create REST API for annotation management

### Endpoints
- [ ] Query endpoints
  - [ ] `GET /api/annotations/gene/{gene_id}` - Get all annotations
  - [ ] `GET /api/annotations/sources` - List sources
  - [ ] `POST /api/annotations/batch` - Batch retrieval
  - [ ] `GET /api/annotations/search` - Search by values
- [ ] Management endpoints
  - [ ] `POST /api/annotations/update/{source}` - Trigger update
  - [ ] `GET /api/annotations/summary` - Statistics
  - [ ] `POST /api/annotations/refresh-materialized-view`
- [ ] CRUD operations
  - [ ] Create annotation records
  - [ ] Update existing annotations
  - [ ] Delete outdated annotations
  - [ ] Audit trail logging

### Schema/Serialization
- [ ] Create Pydantic schemas
  - [ ] `AnnotationResponse`
  - [ ] `AnnotationUpdate`
  - [ ] `AnnotationSourceResponse`
  - [ ] `AnnotationBatchRequest`

### Testing
- [ ] Test all endpoints
- [ ] Test authentication/authorization
- [ ] Test error responses
- [ ] Test batch operations

---

## Phase 6: Update Pipeline (Days 15-16)
**Goal**: Implement automated update system

### Pipeline Components
- [ ] Main pipeline orchestrator
  - [ ] `backend/app/pipeline/annotation_pipeline.py`
  - [ ] Source coordination
  - [ ] Error recovery
  - [ ] Progress tracking
- [ ] Update strategies
  - [ ] Full update (all genes)
  - [ ] Incremental update (changed genes)
  - [ ] Forced refresh
  - [ ] Selective source updates
- [ ] Scheduling (optional for now)
  - [ ] Weekly HGNC updates
  - [ ] Monthly gnomAD updates
  - [ ] Manual trigger option

### Testing
- [ ] Test update pipeline
- [ ] Test error recovery
- [ ] Test progress tracking
- [ ] Test materialized view refresh

---

## Phase 7: Integration & Optimization (Days 17-19)
**Goal**: Integrate with existing system and optimize performance

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

### Performance Optimization
- [ ] Query optimization
  - [ ] Analyze slow queries
  - [ ] Add missing indexes
  - [ ] Optimize JSONB queries
- [ ] Cache tuning
  - [ ] Adjust TTL values
  - [ ] Implement cache warming
  - [ ] Monitor hit rates
- [ ] Batch processing
  - [ ] Optimize batch sizes
  - [ ] Implement parallel processing
  - [ ] Add rate limiting

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
- [ ] >95% of genes have HGNC annotations
- [ ] >80% of genes have gnomAD constraint scores
- [ ] <100ms response time for annotation queries
- [ ] Successful automated updates
- [ ] No breaking changes to existing APIs
- [ ] Test coverage >80% for new code

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