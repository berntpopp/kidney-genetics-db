# Diagnostic Panel Web Scraping - Executive Summary

## Overview
The kidney-genetics database requires gene lists from 10 commercial diagnostic laboratories that offer genetic testing panels for kidney diseases. These panels represent clinically validated gene-disease associations used in patient care.

## Current Status
- **Original Implementation**: R script using PhantomJS (deprecated technology)
- **Data Location**: `kidney-genetics-v1/analyses/03_DiagnosticPanels/`
- **Last Successful Run**: 2024-05-14
- **Migration Status**: Pending Python/Playwright implementation

## Key Statistics
- **10 diagnostic panel providers** targeted
- **34 total panels** (including Blueprint Genetics sub-panels)
- **10/10 sites currently accessible** (100% availability)
- **Evidence threshold**: Genes in ≥2 panels considered significant
- **Mayo Clinic Panel**: 302 genes tested

## Website Accessibility (2025-08-18)
✅ **Working (10 sites)**:
- Blueprint Genetics (+ 24 sub-panels)
- Centogene CentoNephro (NEW URL: centoportal.com)
- CeGaT Kidney Diseases
- PreventionGenetics
- Invitae (2 panels)
- MGZ München
- MVZ Medicover
- Natera Renasight
- Mayo Clinic Labs (requires Playwright - 302 genes)

## Technical Architecture

### Directory Structure
- `/scrapers/diagnostics/` - Main scraping module
- `/scrapers/diagnostics/providers/` - One scraper per provider
- Unified schema using Pydantic models
- JSON output with sub-panel information preserved

### Output Schema Design
- **ProviderData**: Complete data from each provider
- **SubPanel**: Maintains structure for multi-panel providers (Blueprint)
- **GeneEntry**: Tracks which panels contain each gene
- **DiagnosticPanelBatch**: Combined data for API ingestion

### Key Features
1. **One script per provider** - Blueprint handles all 24 sub-panels
2. **Uniform JSON output** - Standardized schema for database import
3. **Sub-panel preservation** - Maintains disease-specific groupings
4. **Cross-provider analysis** - Identifies genes in multiple providers
5. **Evidence scoring** - Based on provider occurrence count

### Technical Stack
- **Engine**: Playwright for protected sites, httpx for standard sites
- **Validation**: Pydantic for schema enforcement
- **Scheduling**: Monthly updates via Docker + Ofelia
- **API Integration**: POST to `/api/ingest/diagnostic-panels`
- **HGNC Mapping**: Built-in symbol normalization

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- Set up Playwright scraping framework
- Create base scraper class with error handling
- Implement HGNC gene symbol normalization

### Phase 2: High-Priority Scrapers (Week 2)
- Blueprint Genetics (most comprehensive)
- Invitae panels (major US provider)
- Natera Renasight (kidney-specific)

### Phase 3: Additional Scrapers (Week 3)
- European providers (CeGaT, MGZ, MVZ)
- PreventionGenetics
- Investigate Centogene redirect

### Phase 4: Integration (Week 4)
- Connect to ingestion API
- Set up scheduling (monthly updates)
- Add monitoring and alerts

## Business Value
- **Clinical Relevance**: Captures real-world genetic testing practices
- **Evidence Quality**: Commercial panels undergo clinical validation
- **Coverage**: ~500-600 unique genes across all panels
- **Updates**: Monthly refresh ensures current clinical practice

## Risk Mitigation
1. **Legal**: Add robots.txt compliance and rate limiting
2. **Technical**: Implement retry logic and fallback mechanisms
3. **Data Quality**: Validate against historical data
4. **Maintenance**: Monitor for HTML structure changes

## Recommendations
1. **Prioritize** Blueprint Genetics, Invitae, and Natera (highest value)
2. **Implement** robust error handling for website changes
3. **Consider** reaching out to vendors for official data access
4. **Document** scraping logic for maintainability
5. **Cache** results to minimize server load

## Next Steps
1. Review and approve implementation plan
2. Set up development environment with Playwright
3. Create proof-of-concept with Blueprint Genetics
4. Establish monitoring dashboard
5. Schedule regular scraping runs

---
*For detailed technical specifications, see [diagnostic-panels-scraping-plan.md](./diagnostic-panels-scraping-plan.md)*