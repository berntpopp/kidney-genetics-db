# ClinGen and GenCC Implementation Plan for Kidney Genetics Database

## Overview
Add ClinGen and GenCC as new data sources to provide curated gene-disease validity evidence for kidney-related genes, similar to the custom-panel implementation but focused on kidney diseases.

## Data Sources

### 1. ClinGen (Clinical Genome Resource)
- **Purpose**: Gene-disease validity assessments from expert curation
- **API Endpoint**: `https://search.clinicalgenome.org/api/`
- **Data Format**: JSON API with gene validity classifications
- **Key Features**:
  - Expert-curated gene-disease relationships
  - Classification levels: Definitive, Strong, Moderate, Limited, Disputed, Refuted
  - Evidence-based scoring system

### 2. GenCC (Gene Curation Coalition)
- **Purpose**: Harmonized gene-disease relationships from multiple sources
- **API Endpoint**: `https://search.thegencc.org/download/action/submissions-export-xlsx`
- **Data Format**: Excel file download (XLSX)
- **Key Features**:
  - Aggregated from 40+ submitters worldwide
  - Standardized classification system
  - Multiple disease relationships per gene

## Implementation Architecture

### Phase 1: Data Source Integration

#### 1.1 ClinGen Source Module
```python
# backend/app/pipeline/sources/clingen.py
class ClinGenSource:
    """
    Fetch and process ClinGen gene validity data for kidney diseases
    """
    
    BASE_URL = "https://search.clinicalgenome.org/api/"
    
    # Kidney-specific affiliate endpoints (identified from ClinGen API)
    KIDNEY_AFFILIATE_IDS = [
        40066,  # Kidney Cystic and Ciliopathy Disorders (69 curations)
        40068,  # Glomerulopathy (17 curations)
        40067,  # Tubulopathy (24 curations)
        40069,  # Complement-Mediated Kidney Diseases (12 curations)
        40070,  # Congenital Anomalies of the Kidney and Urinary Tract (3 curations)
    ]
    
    ENDPOINTS = {
        "cystic_ciliopathy": "affiliates/40066",      # Primary source - 69 curations
        "glomerulopathy": "affiliates/40068",         # 17 curations
        "tubulopathy": "affiliates/40067",            # 24 curations
        "complement_kidney": "affiliates/40069",       # 12 curations
        "cakut": "affiliates/40070",                  # 3 curations (CAKUT)
    }
    
    # Kidney disease keywords for filtering
    KIDNEY_KEYWORDS = [
        "kidney", "renal", "nephro", "glomerul", 
        "tubul", "polycystic", "alport", "nephritis"
    ]
    
    # Classification scoring (matches percentile approach)
    CLASSIFICATION_WEIGHTS = {
        "Definitive": 1.0,      # 100th percentile equivalent
        "Strong": 0.8,          # 80th percentile
        "Moderate": 0.6,        # 60th percentile  
        "Limited": 0.3,         # 30th percentile
        "Disputed": 0.1,        # 10th percentile
        "Refuted": 0.0,         # Excluded
        "No Evidence": 0.0      # Excluded
    }
```

#### 1.2 GenCC Source Module
```python
# backend/app/pipeline/sources/gencc.py
class GenCCSource:
    """
    Fetch and process GenCC submissions for kidney diseases
    """
    
    DOWNLOAD_URL = "https://search.thegencc.org/download/action/submissions-export-xlsx"
    
    # Same kidney keywords as ClinGen
    KIDNEY_KEYWORDS = [...]
    
    # GenCC classification mapping
    CLASSIFICATION_WEIGHTS = {
        "Definitive": 1.0,
        "Strong": 0.8,
        "Moderate": 0.6,
        "Supportive": 0.5,
        "Limited": 0.3,
        "Disputed Evidence": 0.1,
        "No Known Disease Relationship": 0.0,
        "Refuted Evidence": 0.0
    }
```

### Phase 2: Data Processing Pipeline

#### 2.1 Caching Strategy
- Use existing cache system from PubTator implementation
- Cache ClinGen API responses for 7 days
- Cache GenCC Excel file for 30 days
- Implement incremental updates

#### 2.2 Data Filtering
```python
def filter_kidney_diseases(disease_name: str, mondo_id: str = None) -> bool:
    """
    Filter for kidney-related diseases using:
    1. Disease name keyword matching
    2. MONDO ontology hierarchy (if available)
    3. HPO phenotype associations
    """
    # Check disease name
    if any(keyword in disease_name.lower() for keyword in KIDNEY_KEYWORDS):
        return True
    
    # Check MONDO hierarchy for kidney disease ancestors
    if mondo_id and is_kidney_disease_descendant(mondo_id):
        return True
    
    return False
```

#### 2.3 Evidence Storage
```python
# Store in gene_evidence table with JSONB
evidence_data = {
    "classifications": [
        {
            "disease": "Polycystic Kidney Disease",
            "disease_id": "MONDO:0004995",
            "classification": "Definitive",
            "date": "2024-01-15",
            "submitter": "ClinGen Kidney GCEP",
            "evidence_summary": "..."
        }
    ],
    "source_url": "https://...",
    "retrieval_date": "2025-08-16"
}
```

### Phase 3: Database Integration

#### 3.1 Update Database Schema
```sql
-- No schema changes needed, use existing JSONB structure
-- gene_evidence table already supports this

-- Add indexes for performance
CREATE INDEX idx_gene_evidence_clingen ON gene_evidence(gene_id) 
WHERE source_name = 'ClinGen';

CREATE INDEX idx_gene_evidence_gencc ON gene_evidence(gene_id)
WHERE source_name = 'GenCC';
```

#### 3.2 Scoring Integration
- ClinGen and GenCC will be treated as separate sources
- Each contributes to percentile scoring
- With 4 sources (PanelApp, PubTator, ClinGen, GenCC):
  - Max raw score: 4.0
  - Percentage score: (raw_score / 4) * 100

### Phase 4: API Updates

#### 4.1 Data Sources Configuration
```python
# Add to DATA_SOURCE_CONFIG in datasources.py
"ClinGen": {
    "display_name": "ClinGen",
    "description": "Clinical Genome Resource - Expert-curated gene-disease validity",
    "url": "https://clinicalgenome.org/",
    "documentation_url": "https://clinicalgenome.org/docs/",
},
"GenCC": {
    "display_name": "GenCC",
    "description": "Gene Curation Coalition - Harmonized gene-disease relationships",
    "url": "https://thegencc.org/",
    "documentation_url": "https://thegencc.org/api/",
}
```

### Phase 5: Frontend Updates
- Data sources will automatically appear in UI
- No frontend changes needed (dynamic system)

## Implementation Steps

### Week 1: ClinGen Integration
1. **Day 1-2**: Implement ClinGen API client
   - Test API endpoints
   - Identify kidney-specific data
   - Implement caching

2. **Day 3-4**: Process and filter data
   - Filter for kidney diseases
   - Transform to evidence format
   - Store in database

3. **Day 5**: Testing and validation
   - Verify data quality
   - Check scoring integration
   - Update statistics

### Week 2: GenCC Integration
1. **Day 1-2**: Implement GenCC downloader
   - Excel file parsing
   - Caching mechanism
   - Error handling

2. **Day 3-4**: Process and merge
   - Filter kidney diseases
   - Handle duplicates with ClinGen
   - Store evidence

3. **Day 5**: Integration testing
   - Test full pipeline
   - Verify percentile calculations
   - Update documentation

## Expected Outcomes

### Data Volume Estimates
- **ClinGen**: ~125 kidney disease gene validities across 5 expert panels
  - Kidney Cystic and Ciliopathy: 69 genes (primary source)
  - Glomerulopathy: 17 genes
  - Tubulopathy: 24 genes  
  - Complement-Mediated: 12 genes
  - CAKUT: 3 genes
- **GenCC**: ~100-200 kidney disease associations (estimated)
- **Overlap**: ~30-50% genes in both sources

### Score Impact
- High-confidence genes will now have 4 sources
- Maximum percentage score remains 100%
- Better differentiation of evidence levels

### Quality Improvements
- Expert curation from ClinGen GCEPs
- Harmonized data from multiple submitters
- Standardized disease classifications
- Evidence-based validity assessments

## Technical Considerations

### 1. Rate Limiting
- ClinGen API: Respect rate limits (likely 10 req/sec)
- GenCC: Single file download (no rate limit)

### 2. Data Updates
- ClinGen: Weekly updates via API
- GenCC: Monthly file download
- Incremental processing to save resources

### 3. Disease Ontology Mapping
- Map to MONDO IDs where possible
- Use HPO for phenotype matching
- Consider OMIM disease IDs

### 4. Conflict Resolution
- If ClinGen and GenCC disagree, store both
- Let percentile scoring handle weighting
- Show all evidence in UI

## Testing Strategy

### Unit Tests
```python
def test_clingen_kidney_filter():
    """Test kidney disease filtering"""
    assert filter_kidney_diseases("Polycystic Kidney Disease")
    assert filter_kidney_diseases("Alport Syndrome")
    assert not filter_kidney_diseases("Breast Cancer")

def test_classification_scoring():
    """Test classification weight mapping"""
    assert get_classification_weight("Definitive") == 1.0
    assert get_classification_weight("Refuted") == 0.0
```

### Integration Tests
- Full pipeline run with both sources
- Verify database storage
- Check API responses
- Test frontend display

## Dependencies
- No new Python packages needed
- Use existing requests, pandas
- Leverage current caching system
- Reuse percentile scoring

## Timeline
- **Week 1**: ClinGen implementation
- **Week 2**: GenCC implementation  
- **Week 3**: Testing and refinement
- **Total**: 3 weeks to production

## Success Metrics
- ✅ Both sources integrated and running
- ✅ 100+ new gene-disease relationships
- ✅ Scoring system properly scaled
- ✅ Frontend displays new sources
- ✅ Documentation complete