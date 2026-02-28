# Active Data Sources

## Overview
The kidney-genetics database integrates data from multiple authoritative sources to provide comprehensive gene-disease associations for kidney disorders.

## Currently Active Sources (5)

### 1. PanelApp (UK & Australia)
- **Status**: ✅ Fully Operational
- **Genes**: 395 from 27 kidney-related panels
- **Update Frequency**: Real-time API
- **Evidence Type**: Gene panel inclusion with confidence levels
- **Key Features**:
  - Combined UK Genomics England and Australian Genomics panels
  - Green/Amber/Red gene confidence ratings
  - Expert-curated diagnostic panels
  - Kidney-specific filtering (excludes adrenal)

### 2. PubTator3
- **Status**: ✅ Fully Operational  
- **Genes**: 50 with literature evidence
- **Update Frequency**: Real-time API with caching
- **Evidence Type**: Publication counts from text mining
- **Key Features**:
  - Comprehensive kidney disease query
  - Smart caching for 5,435+ publication pages
  - Gene-publication associations via NLP
  - Minimum 3 publications threshold

### 3. ClinGen
- **Status**: ✅ Fully Operational
- **Genes**: 107 with expert validity assessments
- **Panels**: 5 kidney-specific expert panels
  - Kidney Cystic and Ciliopathy Disorders (69 assessments)
  - Glomerulopathy (17 assessments)
  - Tubulopathy (24 assessments)
  - Complement-Mediated Kidney Diseases (12 assessments)
  - Congenital Anomalies of Kidney and Urinary Tract (3 assessments)
- **Evidence Type**: Gene-disease validity classifications
- **Scoring**:
  - Definitive: 1.0
  - Strong: 0.8
  - Moderate: 0.6
  - Limited: 0.4

### 4. GenCC
- **Status**: ✅ Fully Operational
- **Genes**: 352 from harmonized submissions
- **Submissions**: 952 kidney-related (from 24,112 total)
- **Evidence Type**: Harmonized gene-disease relationships
- **Key Features**:
  - Worldwide submitter integration (Orphanet, ClinGen affiliates)
  - Standardized classification mapping
  - Multiple submitter support per gene
  - Automatic gene symbol updates

## Currently Active Sources (5)

### 5. HPO (Human Phenotype Ontology)
- **Status**: ✅ Fully Operational
- **Implementation**: Direct API access (no OMIM files needed)
- **Evidence Type**: Phenotype-gene associations
- **Update Frequency**: Real-time API calls
- **Note**: Using HPO API for all data retrieval

## Hybrid Sources (Upload-Based)

### 6. DiagnosticPanels
- **Status**: ✅ Fully Operational (Upload Interface)
- **Sources**: Blueprint Genetics, Invitae, GeneDx, CeGaT, custom labs
- **Upload Method**: Admin panel file upload
- **Formats**: JSON, CSV, TSV, Excel (max 50MB)
- **Features**:
  - Provider attribution
  - Evidence merging (no duplicates)
  - Auto gene normalization
  - Upload via `/admin/hybrid-sources`

### 7. Literature (Manual)
- **Status**: ✅ Fully Operational (Upload Interface)
- **Type**: Manual curation upload
- **Format**: Excel/CSV/JSON upload
- **Use Case**: Research publications, case reports
- **Features**:
  - Custom evidence types
  - Publication tracking
  - PMID integration
  - Upload via `/admin/hybrid-sources`

## Data Integration Flow

```
Data Sources → Pipeline Processing → PostgreSQL Storage → API Layer → Frontend
     ↓              ↓                      ↓                 ↓           ↓
Real-time API  Normalization     Evidence Scoring    REST/WebSocket  Vue.js UI
```

## Evidence Scoring

All sources contribute to a unified evidence score (0-100%):
- **Count-based sources** (PanelApp, PubTator): Percentile ranking
- **Classification-based** (ClinGen, GenCC): Weighted scoring
- **Combined score**: PostgreSQL PERCENT_RANK() across all evidence

## Update Strategy

### Automatic Updates
- Real-time API calls for PanelApp, PubTator
- Cached file downloads for ClinGen, GenCC
- Background task management with progress tracking

### Manual Triggers
```bash
# Update all sources
curl -X POST http://localhost:8000/api/pipeline/run

# Update specific source
curl -X POST http://localhost:8000/api/pipeline/run/panelapp
```

## Source Health Monitoring

The system tracks:
- Last successful update timestamp
- Error counts and messages
- Gene counts per source
- Processing time metrics

Access via: `GET /api/datasources`

## Adding New Sources

New data sources must implement the `DataSourceBase` interface:
```python
class NewSource(DataSourceBase):
    def fetch_data(self) -> List[Dict]
    def transform_evidence(self, data) -> GeneEvidence
    def calculate_score(self, evidence) -> float
```

See `backend/app/core/data_source_base.py` for details.