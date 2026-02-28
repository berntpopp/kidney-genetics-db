# STRING PPI Annotation Implementation Plan

## Overview
Implement protein-protein interaction scoring using STRING database physical interactions, weighted by partner kidney evidence scores and normalized to avoid hub bias.

## Algorithm

### Core Formula
```
PPI_score(gene) = Σ(STRING_score/1000 × partner_kidney_evidence) / sqrt(degree)
```

Where:
- **STRING_score**: Physical interaction confidence (150-1000)
- **partner_kidney_evidence**: Partner's evidence score from database (0-100)
- **degree**: Count of kidney gene interaction partners
- **Final normalization**: Percentile rank across all kidney genes

### Key Constraints
- **Direct interactions only** (no 2nd degree paths)
- **Both proteins must be kidney genes** (currently ~2-3K genes)
- **Minimum STRING score**: 400 (medium confidence)
- **Hub bias correction**: sqrt(degree) normalization

## Data Sources

### STRING Files
- **Location**: `/data/string/v12.0/`
- **Files**:
  - `9606.protein.info.v12.0.txt` (6MB) - ENSP to gene symbol mapping
  - `9606.protein.physical.links.v12.0.txt` (65MB) - Interaction scores
- **Update frequency**: Yearly (check for v12.5)

## Storage Design

### Primary Storage: JSONB in gene_annotations
```json
{
  "ppi_score": 122.5,          // Final weighted/normalized score
  "ppi_percentile": 0.87,      // Percentile rank (0-1)
  "ppi_degree": 15,            // Number of kidney gene partners
  "interactions": [            // Top 30 interactions for display
    {
      "partner_symbol": "PKD2",
      "partner_gene_id": 456,
      "string_score": 900,
      "partner_evidence": 95,
      "weighted_score": 85.5
    }
  ],
  "summary": {
    "total_interactions": 15,
    "raw_sum": 12450,
    "weighted_sum": 1837.5,
    "avg_string_score": 830,
    "strong_interactions": 5   // score > 800
  }
}
```

### Optional: Network Table (if needed for queries)
```sql
CREATE TABLE IF NOT EXISTS gene_ppi_network (
    gene_id INTEGER REFERENCES genes(id),
    partner_gene_id INTEGER REFERENCES genes(id),
    string_score INTEGER,
    weighted_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (gene_id, partner_gene_id)
);
CREATE INDEX idx_ppi_partner ON gene_ppi_network(partner_gene_id);
```

## Implementation Steps

### 1. Data Preparation Class
```python
# app/pipeline/sources/annotations/string_ppi.py

class StringPPIAnnotationSource(BaseAnnotationSource):
    source_name = "string_ppi"
    display_name = "STRING Protein Interactions"
    version = "12.0"
    cache_ttl_days = 30
```

### 2. Processing Pipeline

#### Phase 1: Load and Filter
1. Load protein info file → Create ENSP to gene_id mapping
2. Get all kidney genes with evidence scores from database
3. Map kidney genes to ENSP identifiers
4. Load physical links file (streaming, chunked)
5. Filter: Keep only rows where BOTH proteins are kidney genes
6. Filter: Keep only interactions with score ≥ 400
7. Result: ~100-200K filtered interactions in memory

#### Phase 2: Calculate Scores
For each kidney gene:
1. Get all direct interactions
2. Calculate weighted score for each partner:
   - `weighted = (string_score/1000) × partner_evidence_score`
3. Sum all weighted scores
4. Calculate degree (number of partners)
5. Normalize: `final_raw = weighted_sum / sqrt(degree)`

#### Phase 3: Percentile Normalization
1. Collect all raw scores
2. Calculate percentile rank for each gene
3. Store both raw and percentile scores

### 3. Batch Processing Strategy
```python
async def fetch_batch(self, genes: list[Gene]) -> dict:
    # Process ALL genes at once for efficiency
    # 1. Load STRING data once
    # 2. Build interaction matrix in memory
    # 3. Calculate all scores
    # 4. Apply percentile normalization
    # 5. Format and return annotations
```

### 4. Storage Optimization
- Store top 30 interactions per gene (by weighted score)
- Include summary statistics for full network
- Total storage: ~2-3MB for 3K genes

## API Integration

### Endpoints
```
GET /api/genes/{gene_id}/annotations?source=string_ppi
GET /api/genes/{gene_id}/ppi/network  # Optional, if network table implemented
```

### Response Format
```json
{
  "source": "string_ppi",
  "version": "12.0",
  "data": {
    "score": 122.5,
    "percentile": 0.87,
    "degree": 15,
    "top_partners": [
      {"symbol": "PKD2", "score": 85.5},
      {"symbol": "PKHD1", "score": 70.4}
    ]
  }
}
```

## Update Strategy

### Initial Load
1. Download STRING files (if not present)
2. Run batch processing for all genes
3. Store in gene_annotations table
4. Optionally populate network table

### Periodic Updates (Monthly)
1. Check for new STRING version
2. Refresh kidney gene evidence scores
3. Reprocess all interactions
4. Update annotations

### Triggers for Update
- New STRING database version
- Significant changes in kidney gene list (>10%)
- Monthly scheduled refresh

## Performance Considerations

### Memory Usage
- Peak: ~500MB during processing
- Runtime: ~2-3 minutes for 3K genes
- Storage: ~2-3MB in database

### Query Performance
- Single gene lookup: <10ms (JSONB index)
- Network queries: <50ms (if network table used)
- Batch updates: Process in single transaction

## Quality Checks

### Validation
1. Verify all genes have non-null scores
2. Check score distribution (should be continuous)
3. Confirm percentiles range 0-1
4. Validate degree counts match interactions

### Expected Distributions
- Median degree: 10-20 interactions
- Top percentile genes: Known PPI hubs in kidney
- Zero-score genes: <10% (isolated proteins)

## Error Handling

### File Processing
- Validate file headers before processing
- Check ENSP ID format (9606.ENSP...)
- Handle missing gene mappings gracefully

### Score Calculation
- Handle genes with no interactions (score = 0)
- Handle genes with degree = 1 (no sqrt(0) issues)
- Cap maximum interactions stored at 30

## Future Enhancements

### Phase 2 (Optional)
- Add interaction type filtering (physical vs functional)
- Implement 2-hop scoring with decay factor
- Add tissue-specific expression weighting

### Phase 3 (Optional)
- Interactive network visualization API
- Pathway enrichment for interaction clusters
- Disease module proximity scoring