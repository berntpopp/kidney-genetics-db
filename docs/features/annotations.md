# Gene Annotations System

## Overview
Comprehensive gene annotation system that aggregates data from multiple biological databases to provide rich metadata for kidney disease genes.

## Current Status
✅ **Fully Implemented and Operational**
- 9 annotation sources active (HGNC, gnomAD, ClinVar, HPO, GTEx, Descartes, MPO/MGI, STRING PPI)
- Automated update pipeline with scheduling
- Unified caching system with L1/L2 layers
- Real-time progress tracking
- Comprehensive API endpoints

## Architecture

### Data Sources

#### Core Reference Data
- **HGNC** - Gene nomenclature and identifiers
  - NCBI Gene ID, Ensembl ID, OMIM ID
  - MANE Select transcripts
  - Previous/alias symbols
  - Update frequency: Weekly

- **gnomAD** - Constraint scores and population genetics
  - pLI, oe_lof, lof_z scores
  - Missense and synonymous Z-scores
  - v4.0.0 with GRCh38 reference
  - Update frequency: Monthly

#### Clinical Annotations
- **ClinVar** - Pathogenic variant counts
  - P/LP/VUS/B/LB classification counts
  - High confidence variant percentage
  - Top associated traits
  - Update frequency: Weekly

- **HPO** - Human Phenotype Ontology
  - Associated phenotype terms
  - Disease associations
  - Kidney phenotype classification
  - Update frequency: Weekly

#### Expression Data
- **GTEx** - Tissue expression (v8)
  - Kidney cortex/medulla expression
  - Expression categories (Low/Medium/High)
  - Update frequency: Monthly

- **Descartes** - Single-cell expression
  - Embryonic kidney expression
  - Cell type specificity
  - Update frequency: Monthly

#### Functional Data
- **STRING PPI** - Protein interactions
  - Physical interaction scores
  - Weighted by kidney evidence
  - Hub bias correction
  - Update frequency: Bi-weekly

- **MPO/MGI** - Mouse phenotypes
  - Mouse ortholog mapping
  - Kidney phenotype indicators
  - Knockout model data
  - Update frequency: Bi-weekly

### Storage Architecture

#### Database Schema
```sql
-- Main annotation storage with JSONB
gene_annotations (
  id, gene_id, source, version, 
  annotations JSONB, metadata JSONB,
  created_at, updated_at
)

-- Source registry
annotation_sources (
  id, source_name, display_name, 
  is_active, last_update, next_update, 
  config JSONB
)

-- Materialized view for fast access
gene_annotations_summary (
  gene_id, pli, oe_lof, lof_z, mis_z,
  ncbi_gene_id, ensembl_gene_id, etc.
)
```

### Caching System
- **L1 Cache**: In-memory LRU (process-local, <10ms response)
- **L2 Cache**: PostgreSQL JSONB (persistent, shared)
- **Cache TTLs**: 
  - HGNC: 24 hours
  - gnomAD: 30 days  
  - ClinVar: 7 days
  - Expression data: 30 days

## API Endpoints

### Query Endpoints
- `GET /api/annotations/genes/{gene_id}/annotations` - All annotations
- `GET /api/annotations/genes/{gene_id}/annotations/summary` - Summary view
- `GET /api/annotations/sources` - List active sources
- `GET /api/annotations/statistics` - System statistics

### Management Endpoints
- `POST /api/annotations/pipeline/update` - Trigger updates
- `GET /api/annotations/pipeline/status` - Pipeline status
- `GET /api/annotations/scheduler/jobs` - Scheduled jobs
- `POST /api/annotations/refresh-view` - Refresh materialized view

### Cache Management
- `GET /api/admin/cache/stats` - Cache statistics
- `DELETE /api/admin/cache/{namespace}` - Clear namespace
- `GET /api/admin/cache/health` - Health check

## Update Pipeline

### Automated Schedule
- **Daily**: Incremental updates (2 AM)
- **Weekly**: Full updates (Sunday 3 AM)
- **Source-specific**:
  - HGNC: Weekly (Monday)
  - gnomAD: Monthly (1st of month)
  - ClinVar: Weekly (Wednesday)

### Manual Triggers
All updates can be triggered manually via API or admin panel.

## Performance Metrics
- **Response time**: ~10ms (cached), ~50ms (uncached)
- **Cache hit rate**: 75-95%
- **Update duration**: 5-30 minutes per source
- **Storage**: ~2-3MB per 1000 genes

## Error Handling
- Retry logic with exponential backoff
- Circuit breakers for failing sources
- Rate limiting compliance
- Graceful degradation on source failures

## Data Validation
- JSONB schema validation
- Empty/null response filtering
- Source-specific validation rules
- Audit trail for all changes