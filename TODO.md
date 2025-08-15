# Implementation TODO

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

## Phase 1: Database & Models
*Goal: Complete data model with migrations*

- [ ] Database schema
  - [ ] Create SQLAlchemy models
    - [ ] `User` model with authentication fields
    - [ ] `Gene` model with HGNC fields
    - [ ] `GeneEvidence` model with JSONB storage
    - [ ] `GeneCuration` model for aggregated data
    - [ ] `PipelineRun` model for tracking
  - [ ] Setup Alembic
    - [ ] Initialize Alembic configuration
    - [ ] Create initial migration
    - [ ] Test upgrade/downgrade

- [ ] Database connection
  - [ ] Configure SQLAlchemy with connection pooling
  - [ ] Create database session management
  - [ ] Add health check for database connection
  - [ ] Test with `docker-compose.services.yml`

## Phase 2: Basic API
*Goal: CRUD operations for genes*

- [ ] Core API structure
  - [ ] Setup FastAPI app structure
    - [ ] `app/api/` - endpoints
    - [ ] `app/core/` - config, security
    - [ ] `app/crud/` - database operations
    - [ ] `app/schemas/` - Pydantic models
  
- [ ] Gene endpoints
  - [ ] `GET /api/genes` - List genes with pagination
  - [ ] `GET /api/genes/{symbol}` - Get gene details
  - [ ] `GET /api/genes/search` - Search genes
  - [ ] Create sample data for testing

- [ ] Authentication (simple)
  - [ ] JWT token generation
  - [ ] Login endpoint
  - [ ] Protected route example
  - [ ] Skip complex permissions for now

## Phase 3: First Data Source (PanelApp)
*Goal: Working pipeline with one reliable source*

- [ ] PanelApp integration
  - [ ] Create `app/pipeline/sources/panelapp.py`
  - [ ] Implement UK PanelApp API client
    - [ ] Fetch panels list
    - [ ] Filter kidney-related panels
    - [ ] Extract genes from panels
  - [ ] Add Australia PanelApp
  - [ ] Store in `gene_evidence` table

- [ ] Pipeline framework
  - [ ] Create `app/pipeline/run.py` main orchestrator
  - [ ] Add configuration system
  - [ ] Implement basic logging
  - [ ] Create CLI command to run pipeline

- [ ] Test with real data
  - [ ] Run pipeline manually
  - [ ] Verify data in database
  - [ ] Check ~500-1000 genes imported

## Phase 4: Minimal Frontend
*Goal: View pipeline results in browser*

- [ ] Basic Vue setup
  - [ ] Configure API client (Axios)
  - [ ] Setup Vue Router
  - [ ] Create layout with navigation

- [ ] Gene list view
  - [ ] Create `GeneTable.vue` component
  - [ ] Implement server-side pagination
  - [ ] Add loading states
  - [ ] Display gene symbol, HGNC ID, sources

- [ ] Search functionality
  - [ ] Add search input
  - [ ] Implement debounced search
  - [ ] Update table on search

- [ ] Test end-to-end
  - [ ] Start all services
  - [ ] View genes from PanelApp
  - [ ] Test search works

## Phase 5: Complete Stable Pipeline
*Goal: All reliable sources integrated*

- [ ] HPO integration
  - [ ] Create `app/pipeline/sources/hpo.py`
  - [ ] Query HPO API for kidney phenotypes
  - [ ] Extract associated genes
  - [ ] Store in database

- [ ] PubTator integration  
  - [ ] Create `app/pipeline/sources/pubtator.py`
  - [ ] Query PubTator for kidney-related publications
  - [ ] Extract gene mentions
  - [ ] Store with PMIDs

- [ ] Merge logic
  - [ ] Create `app/pipeline/merge.py`
  - [ ] Aggregate evidence by gene
  - [ ] Calculate evidence scores
  - [ ] Update `gene_curations` table

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