# Kidney-Genetics Database - Development Plan

## Project Status
⚠️ **Alpha Stage (v0.1.0)**: Database, API, Frontend, and 4 data sources working with 571 genes. 

**WARNING**: This is alpha software with no tests, no security, and breaking changes expected. Do not use in production.

## Pending Development

### Phase 7: Ingestion API & Brittle Sources
*Goal: Handle unreliable data sources and manual uploads*

#### Tasks
- [ ] **Ingestion API**
  - [ ] Create `/api/ingest` endpoint with validation
  - [ ] Add API key authentication
  - [ ] Implement background processing queue
  
- [ ] **Manual Upload**
  - [ ] Create `/api/upload/literature` endpoint
  - [ ] Build upload form in frontend
  - [ ] Process Excel/CSV files
  - [ ] Show upload history
  
- [ ] **Web Scraping Service**
  - [ ] Create separate `scrapers/` directory
  - [ ] Implement Blueprint Genetics scraper
  - [ ] Add Natera panel scraper
  - [ ] Add Invitae panel scraper
  - [ ] Error handling and retry logic
  - [ ] Push data to ingestion API

### Phase 8: Performance Optimization
*Goal: Optimize response times and scalability*

#### Tasks
- [✅] **API Caching System** (Already implemented)
  - [✅] Database-persisted cache (cache_service.py)
  - [✅] Multi-level caching (L1 memory + L2 database)
  - [✅] TTL management per source
  - [ ] Cache management endpoints (partial)
  
- [ ] **Performance Optimization**
  - [ ] Database query optimization
  - [ ] API response compression
  - [ ] Frontend bundle optimization
  - [ ] Connection pooling tuning

### Phase 9: Testing & Validation
*Goal: Comprehensive test coverage*

#### Tasks
- [ ] **Data Validation**
  - [ ] Compare with R pipeline outputs
  - [ ] Validate evidence scores
  - [ ] Document differences
  
- [ ] **Test Suite**
  - [ ] Unit tests for pipeline sources
  - [ ] Integration tests for API
  - [ ] Frontend E2E tests
  - [ ] Performance benchmarks

### Phase 10: Production Deployment
*Goal: Production-ready deployment*

#### Tasks
- [ ] **Infrastructure**
  - [ ] Create `docker-compose.prod.yml`
  - [ ] Environment management
  - [ ] Logging configuration
  - [ ] Error monitoring (Sentry)
  
- [ ] **Security**
  - [ ] Security headers
  - [ ] Rate limiting
  - [ ] Input validation audit
  
- [ ] **Documentation**
  - [ ] Deployment guide
  - [ ] User manual
  - [ ] API documentation

## Minor Enhancements

### Export Functionality
- [ ] CSV export endpoint
- [ ] JSON export endpoint
- [ ] Configurable export formats
- [ ] Bulk export support

### HPO Data Source Enhancement
- [ ] Improve API-only integration
- [ ] Add more comprehensive disease-gene mappings
- [ ] Optimize API call efficiency

## Architecture Decisions

### Deferred Complexity
- No microservices (monolithic is sufficient)
- REST API only (no GraphQL needed)
- No Kubernetes (Docker Compose for deployment)
- No message queue (ThreadPoolExecutor sufficient)

### Technology Choices
- **Database**: PostgreSQL with JSONB (no NoSQL needed)
- **Backend**: FastAPI (not Django/Flask)
- **Frontend**: Vue.js (not React/Angular)
- **Deployment**: Docker Compose (not K8s)

## Resources
- **Completed Documentation**: See `/docs` directory
- **Implementation Details**: See `/TODO.md` for task tracking
- **Development Guide**: See `/docs/development/setup-guide.md`

## Contact
For questions about pending development, see project README.