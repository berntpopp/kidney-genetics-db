# Implementation TODO

## Progress Summary
- ✅ **Phase 0**: Project Foundation - Complete
- ✅ **Phase 1**: Database & Models - Complete  
- ✅ **Phase 2**: Basic API - Complete
- ✅ **Phase 3**: First Data Source (PanelApp) - Complete (407 genes from UK+AU combined!)
- ✅ **Phase 4**: Minimal Frontend - Complete (Vue.js app with sorting!)
- ✅ **Phase 5**: Complete Stable Pipeline - Complete (PanelApp + PubTator working!)
- ⏳ **Phase 6**: API & Frontend Enhancement
- ⏳ **Phase 7**: Ingestion API & Brittle Sources (Diagnostic panels need scraping)
- ⏳ **Phase 8**: Testing & Validation
- ⏳ **Phase 9**: Production Preparation

## Current Status (2025-08-16)
### Working Features
- **PanelApp Integration**: 407 genes from combined UK (19 panels) and Australian (12 panels) sources
- **PubTator3 Integration**: 22 genes from literature mining using comprehensive kidney query
- **Evidence Aggregation**: 429 genes total, with PKD1/PKD2 having evidence from multiple sources
- **Frontend**: Full table with sorting, search, filtering by score
- **API**: RESTful endpoints with pagination, sorting, and filtering

### Known Issues
- **HPO**: Needs valid OMIM genemap2.txt download link (API key required)
- **Diagnostic Panels**: Need web scraping implementation (Blueprint, Natera, etc.)

### Data Statistics
- Total genes: 429
- PanelApp only: 405 genes
- PubTator only: 22 genes  
- Both sources: 2 genes (PKD1, PKD2)

## Overview
Logical implementation phases for building the kidney-genetics-db system. Each phase produces working software that can be tested and validated.

## Phase 0: Project Foundation ✅
*Goal: Working development environment*

- [x] Initialize project structure
  - [x] Create `backend/`, `frontend/`, `plan/` directories
  - [x] Setup `.gitignore` for Python, Node, PostgreSQL
  - [x] Create `.env.example` with all required variables
  
- [x] Docker development setup
  - [x] Create `docker-compose.services.yml` (PostgreSQL only)
  - [x] Test PostgreSQL container starts and persists data
  - [x] Create `init.sql` with basic schema

- [x] Backend project setup
  - [x] Initialize Python project with `pyproject.toml`
  - [x] Install core dependencies using `uv`
  - [x] Create basic `app/main.py` with health check endpoint
  - [x] Verify hot reload works with `uvicorn --reload`

- [ ] Frontend project setup
  - [ ] Initialize Vue 3 project with Vite
  - [ ] Add Vuetify 3
  - [ ] Create basic App.vue
  - [ ] Verify HMR works

## Phase 1: Database & Models ✅
*Goal: Complete data model with migrations*

- [x] Database schema
  - [x] Create SQLAlchemy models
    - [x] `User` model with authentication fields
    - [x] `Gene` model with HGNC fields
    - [x] `GeneEvidence` model with JSONB storage
    - [x] `GeneCuration` model for aggregated data
    - [x] `PipelineRun` model for tracking
  - [x] Setup Alembic
    - [x] Initialize Alembic configuration
    - [x] Create initial migration
    - [x] Test upgrade/downgrade

- [x] Database connection
  - [x] Configure SQLAlchemy with connection pooling
  - [x] Create database session management
  - [x] Add health check for database connection
  - [x] Test with `docker-compose.services.yml`

## Phase 2: Basic API ✅
*Goal: CRUD operations for genes*

- [x] Core API structure
  - [x] Setup FastAPI app structure
    - [x] `app/api/` - endpoints
    - [x] `app/core/` - config, security
    - [x] `app/crud/` - database operations
    - [x] `app/schemas/` - Pydantic models
  
- [x] Gene endpoints
  - [x] `GET /api/genes` - List genes with pagination
  - [x] `GET /api/genes/{symbol}` - Get gene details
  - [x] `GET /api/genes/{symbol}/evidence` - Get gene evidence
  - [x] `POST /api/genes` - Create new gene

- [ ] Authentication (deferred to later)
  - [ ] JWT token generation
  - [ ] Login endpoint
  - [ ] Protected route example

## Phase 3: First Data Source (PanelApp) ✅
*Goal: Working pipeline with one reliable source*

- [x] PanelApp integration
  - [x] Create `app/pipeline/sources/panelapp.py`
  - [x] Implement UK PanelApp API client
    - [x] Fetch panels list
    - [x] Filter kidney-related panels
    - [x] Extract genes from panels
  - [x] Add Australia PanelApp (DNS issues but code complete)
  - [x] Store in `gene_evidence` table

- [x] Pipeline framework
  - [x] Create `app/pipeline/run.py` main orchestrator
  - [x] Add configuration system
  - [x] Implement basic logging
  - [x] Successfully imported 318 genes from 19 panels!
  
- [x] Code quality (Backend)
  - [x] Ran ruff linting (auto-fixed 14 issues)
  - [x] Formatted code with ruff format (5 files reformatted)
  - [x] Type checking with mypy (SQLAlchemy warnings resolved)
  - [x] All Python code follows PEP 8 standards

## Phase 4: Minimal Frontend ✅
*Goal: View pipeline results in browser*

- [x] Basic Vue setup
  - [x] Configure API client (Axios)
  - [x] Setup Vue Router
  - [x] Create layout with navigation

- [x] Gene list view
  - [x] Create `GeneTable.vue` component
  - [x] Implement server-side pagination
  - [x] Add loading states
  - [x] Display gene symbol, HGNC ID, sources

- [x] Search functionality
  - [x] Add search input
  - [x] Implement debounced search
  - [x] Update table on search

- [x] Additional views
  - [x] Home dashboard with statistics
  - [x] Gene detail view with evidence
  - [x] About page with project info

- [x] Test end-to-end
  - [x] All services running (API port 8000, Frontend port 5173)
  - [x] Successfully viewing 318 genes from PanelApp
  - [x] Search and pagination working

- [x] Code quality
  - [x] ESLint configured for Vue 3 (flat config)
  - [x] Prettier formatting configured
  - [x] All components use Vue 3 Composition API with `<script setup>`
  - [x] Code formatted and linted (4 v-slot warnings remain, non-critical)

## Phase 5: Complete Stable Pipeline ✅
*Goal: All reliable sources integrated*

- [x] HPO integration
  - [x] Create `app/pipeline/sources/hpo.py`
  - [x] Implement file download approach (phenotype.hpoa)
  - [x] Parse OMIM disease-gene associations
  - [x] Store in database (4 genes added, needs OMIM fix)

- [x] PubTator integration  
  - [x] Create `app/pipeline/sources/pubtator.py`
  - [x] Migrate to PubTator3 API with search endpoint
  - [x] Use comprehensive kidney disease query
  - [x] Store with PMIDs (22 genes with 3+ publications)

- [x] Merge logic
  - [x] Create `app/pipeline/aggregate.py`
  - [x] Aggregate evidence by gene
  - [x] Calculate evidence scores (working!)
  - [x] Update `gene_curations` table (429 curations)

- [x] Frontend improvements
  - [x] Enable table sorting (all columns)
  - [x] Fix v-slot directive issues
  - [x] Show panel source differentiation (UK/AU)
  - [x] Display correct evidence counts

- [ ] Annotation pipeline
  - [ ] HGNC standardization
  - [ ] Add OMIM data
  - [ ] Add ClinVar annotations
  - [ ] Add constraint scores (gnomAD)

## Phase 6: API & Frontend Enhancement
*Goal: Full-featured user interface*

- [ ] Advanced API features
  - [ ] Export endpoints (CSV, JSON)
  - [ ] Filtering by evidence score
  - [ ] Sorting options
  - [ ] Statistics endpoint

- [ ] Gene detail view
  - [ ] Create `GeneDetail.vue`
  - [ ] Show all evidence sources
  - [ ] Display annotations
  - [ ] Add navigation between genes

- [ ] Dashboard
  - [ ] Create home dashboard
  - [ ] Show statistics
  - [ ] Recent updates
  - [ ] Source health status

- [ ] Export functionality
  - [ ] Add export buttons
  - [ ] Generate CSV files
  - [ ] Include all annotations

## Phase 7: Ingestion API & Brittle Sources
*Goal: Handle unreliable data sources*

- [ ] Ingestion API
  - [ ] Create `/api/ingest` endpoint
  - [ ] Add API key authentication
  - [ ] Implement validation
  - [ ] Add background processing

- [ ] Manual upload
  - [ ] Create `/api/upload/literature` endpoint
  - [ ] Build upload form in frontend
  - [ ] Process Excel files
  - [ ] Show upload history

- [ ] Scraping service setup
  - [ ] Create separate `scrapers/` directory
  - [ ] Implement Blueprint Genetics scraper
  - [ ] Add error handling and retries
  - [ ] Push data to ingestion API

- [ ] Monitoring
  - [ ] Track source health
  - [ ] Show last successful update
  - [ ] Alert on failures

## Phase 8: Testing & Validation
*Goal: Verify correctness vs R pipeline*

- [ ] Data validation
  - [ ] Compare gene counts with R output
  - [ ] Validate evidence scores
  - [ ] Check annotation completeness
  - [ ] Document any differences

- [ ] Unit tests
  - [ ] Test pipeline sources
  - [ ] Test merge logic
  - [ ] Test API endpoints
  - [ ] Test data transformations

- [ ] Integration tests
  - [ ] Full pipeline run
  - [ ] API with database
  - [ ] Frontend E2E tests

## Phase 9: Production Preparation
*Goal: Ready for deployment*

- [ ] Performance optimization
  - [ ] Database query optimization
  - [ ] Add caching (Redis)
  - [ ] Frontend bundle optimization
  - [ ] API response compression

- [ ] Production configuration
  - [ ] Create `docker-compose.prod.yml`
  - [ ] Environment variable management
  - [ ] Logging configuration
  - [ ] Error monitoring setup

- [ ] Documentation
  - [ ] API documentation (auto-generated)
  - [ ] Deployment guide
  - [ ] User manual
  - [ ] Developer documentation

- [ ] Security
  - [ ] Security headers
  - [ ] Rate limiting
  - [ ] Input validation
  - [ ] SQL injection prevention

## Phase 10: Advanced Features (Optional)
*Goal: Nice-to-have enhancements*

- [ ] Real-time updates
  - [ ] WebSocket for pipeline status
  - [ ] Live data refresh
  - [ ] Progress indicators

- [ ] Advanced analytics
  - [ ] Gene trend analysis
  - [ ] Source comparison
  - [ ] Evidence distribution

- [ ] User features
  - [ ] Save searches
  - [ ] Custom gene lists
  - [ ] Annotations/comments

- [ ] Pipeline scheduling
  - [ ] Automated daily runs
  - [ ] Email notifications
  - [ ] Failure alerts

## Development Patterns

### Always Working Software
After each phase, the system should be:
- Runnable with `docker-compose up`
- Testable with real data
- Demoable to stakeholders

### Incremental Complexity
- Start with simplest implementation
- Add complexity only when needed
- Defer difficult problems until core works

### Test as You Build
- Verify each component works before moving on
- Keep sample data for testing
- Document expected outputs

### Dependencies First
- Build foundation before features
- Ensure data flow works before UI
- Test pipeline before automation

## Key Decisions

### Start Simple
- ✅ One source (PanelApp) before multiple
- ✅ Basic auth before complex permissions  
- ✅ Simple UI before fancy visualizations
- ✅ Manual pipeline runs before automation

### Defer Complexity
- ❌ No microservices initially
- ❌ No real-time features initially
- ❌ No complex caching initially
- ❌ No CI/CD initially

### Focus on Core Value
- ✅ Accurate gene data
- ✅ Reliable pipeline
- ✅ Simple, fast search
- ✅ Data export

## Success Criteria

Each phase is complete when:
1. Code runs without errors
2. Data flows correctly
3. Tests pass
4. Can demo the feature
5. Ready to build upon

## Notes

- This TODO assumes a single developer or small team
- Each phase builds on the previous one
- Phases can be adjusted based on discoveries
- Some tasks can be parallelized within a phase
- The order prioritizes reducing technical risk early