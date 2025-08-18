# TODO - Kidney Genetics Database (Alpha 0.1.0)

## Current Sprint (Priority)

### 🔥 Critical Fixes
- [ ] **HPO Data Source**
  - [ ] Improve HPO API integration
  - [ ] Add disease-gene associations via API
  - [ ] Test integration with pipeline

### 📤 Export Functionality  
- [ ] Implement `/api/genes/export` endpoint
- [ ] Support CSV and JSON formats
- [ ] Add filtering parameters to export
- [ ] Frontend download button integration

## Next Sprint

### 🔍 Web Scraping Service
- [ ] **Blueprint Genetics**
  - [ ] Analyze current website structure
  - [ ] Implement scraper with Playwright
  - [ ] Map to evidence schema
  - [ ] Schedule automated updates
  
- [ ] **Other Diagnostic Panels**
  - [ ] Natera Renasight scraper
  - [ ] Invitae panels scraper
  - [ ] GeneDx kidney panels

### 📥 Manual Upload System
- [ ] Literature upload endpoint
- [ ] Excel/CSV parser
- [ ] Validation and error handling
- [ ] Upload history tracking
- [ ] Frontend upload interface

## Backlog

### Performance Optimization
- [ ] Implement Redis caching layer
- [ ] Database query optimization
- [ ] API response compression
- [ ] Frontend lazy loading
- [ ] Bundle size optimization

### Testing Suite
- [ ] Unit tests (target: 80% coverage)
  - [ ] Pipeline sources
  - [ ] API endpoints
  - [ ] Data transformations
- [ ] Integration tests
  - [ ] Full pipeline run
  - [ ] API with database
- [ ] E2E tests (Playwright)
  - [ ] Gene search workflow
  - [ ] Export functionality
  - [ ] Data source updates

### Production Deployment
- [ ] Docker production config
- [ ] Environment management
- [ ] SSL/TLS setup
- [ ] Backup strategy
- [ ] Monitoring setup (Prometheus/Grafana)
- [ ] Error tracking (Sentry)

### Documentation
- [ ] API documentation improvements
- [ ] User guide with screenshots
- [ ] Deployment guide
- [ ] Data source integration guide

## Technical Debt
- [ ] Refactor evidence scoring to support custom weights
- [ ] Improve error handling in pipeline sources
- [ ] Add retry logic for failed API calls
- [ ] Optimize JSONB queries
- [ ] Clean up unused dependencies

## Future Features (Not Prioritized)
- User authentication and roles
- Gene list management
- Custom annotations
- Batch gene analysis
- Advanced visualizations
- Email notifications
- Scheduled reports

## Completed ✅
See [Release Notes](./docs/RELEASES.md) for completed features in previous sprints.

---
*Last Updated: 2025-08-18*
*Status: Alpha Development*