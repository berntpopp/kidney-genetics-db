# Evidence Scoring Methodology

**Version**: 2.0 (PostgreSQL-based implementation)  
**Date**: August 16, 2025  
**Status**: ✅ IMPLEMENTED

## Overview

The kidney-genetics-db implements a sophisticated evidence scoring system that normalizes evidence strength across multiple data sources and combines them into a final confidence score (0-100%). This system is implemented entirely in PostgreSQL using database views for maximum performance and transparency.

## Core Principles

1. **Source Independence**: Each evidence source can contribute a maximum of 1.0 to the score
2. **Source-Specific Normalization**: Different source types use appropriate normalization methods
3. **Transparent Calculation**: All scoring logic is implemented in PostgreSQL views
4. **Real-Time Updates**: Scores are calculated dynamically without Python dependencies

## Scoring Methodology

### Overview of Scoring Tracks

The system implements three distinct scoring approaches based on evidence type:

#### 1. Count-Based Sources (Direct Percentile Normalization)
Used for sources where evidence strength is determined by quantity of sub-evidence:

- **PanelApp**: Number of clinical panels containing the gene
- **HPO**: Number of phenotype associations + disease associations  
- **PubTator**: Number of publications mentioning the gene
- **Literature**: Number of literature references

**Method**: Uses PostgreSQL `PERCENT_RANK()` function to convert counts directly to percentiles (0-1) within each source.

#### 2. ClinGen (Direct Weight Mapping)
Expert-curated classifications that map directly to 0-1 weights:

- Classifications already span the full range (Definitive=1.0 to Refuted=0.1)
- No normalization needed as weights are well-distributed
- Single classification per gene ensures straightforward mapping

**Method**: Direct mapping of classification strings to predetermined weights (0-1).

#### 3. GenCC (Two-Stage: Weighted Scoring + Percentile Normalization)
Complex multi-classification system requiring sophisticated handling:

- Multiple classifications per gene from different submitters
- Raw weighted scores have limited range (~0.28-0.85)
- Requires both quality/quantity evaluation AND normalization

**Method**: 
1. Calculate weighted score using 3-component formula
2. Apply percentile normalization to spread scores across 0-1 range

### Source-Specific Implementation

#### PanelApp Scoring
```sql
-- Extract panel count
jsonb_array_length(evidence_data->'panels')

-- Convert to percentile within PanelApp source
PERCENT_RANK() OVER (
    PARTITION BY source_name 
    ORDER BY source_count
) 
```

#### HPO Scoring  
```sql
-- Extract total associations count
jsonb_array_length(evidence_data->'phenotypes') +
jsonb_array_length(evidence_data->'disease_associations')

-- Convert to percentile within HPO source
PERCENT_RANK() OVER (
    PARTITION BY source_name 
    ORDER BY source_count
)
```

#### PubTator Scoring
```sql
-- Extract publication count
COALESCE(
    (evidence_data->>'publication_count')::int,
    jsonb_array_length(evidence_data->'pmids')
)

-- Convert to percentile within PubTator source  
PERCENT_RANK() OVER (
    PARTITION BY source_name 
    ORDER BY source_count
)
```

#### ClinGen Classification Weights
```sql
CASE evidence_data->>'classification'
    WHEN 'Definitive' THEN 1.0
    WHEN 'Strong' THEN 0.8
    WHEN 'Moderate' THEN 0.6
    WHEN 'Limited' THEN 0.3
    WHEN 'Disputed' THEN 0.1
    WHEN 'Refuted' THEN 0.0
    WHEN 'No Evidence' THEN 0.0
    ELSE 0.5  -- Unknown classifications
END
```

#### GenCC Classification Weights (Two-Stage Weighted and Normalized System)

**Current Implementation: Migration 2d3f4a5b6c7e (August 18, 2025)**  
*Previous: Migration 1c0a4ff21798 (weighted scoring without normalization)*

GenCC scoring uses a sophisticated two-stage system that addresses the complexity of multiple classifications per gene:

##### Stage 1: Weighted 3-Component Scoring

Unlike simple classification mapping, GenCC genes often have multiple classifications from different submitters. The weighted scoring system evaluates these comprehensively:

**Components:**
1. **Quality Score (50% weight)**: Uses quadratic weighting to emphasize higher classifications
   - Definitive classifications contribute disproportionately more than lower ones
   - Formula: `SUM(weight²) / SUM(weight) × 0.5`
   
2. **Quantity Score (30% weight)**: Rewards multiple submissions with diminishing returns
   - More submissions increase confidence, but with square root scaling
   - Formula: `MIN(1.0, √(count/5)) × 0.3`
   - Normalized to 5 as a "good evidence" baseline
   
3. **Confidence Score (20% weight)**: Proportion of high-quality classifications
   - Measures consensus on Definitive/Strong classifications
   - Formula: `(count_definitive_strong / total_count) × 0.2`

**Classification Weight Values:**
| Classification | Weight | Rationale |
|---------------|--------|-----------|
| Definitive | 1.0 | Highest confidence level |
| Strong | 0.8 | Well-established association |
| Moderate | 0.6 | Good evidence with some limitations |
| Supportive | 0.5 | Supporting but not conclusive |
| Limited | 0.4 | Weak evidence |
| Disputed | 0.2 | Conflicting evidence |
| Refuted | 0.1 | Evidence against association |

**Stage 1 Formula Implementation:**
```sql
-- Component 1: Quality Score (50%)
-- Quadratic weighting emphasizes higher quality
quality_score = SUM(weight²) / SUM(weight) × 0.5

-- Component 2: Quantity Score (30%)  
-- Square root for diminishing returns
quantity_score = MIN(1.0, √(count/5)) × 0.3

-- Component 3: Confidence Score (20%)
-- Proportion of high-quality classifications
confidence_score = (count_definitive_strong / total_count) × 0.2

-- Raw weighted score (ranges ~0.28 to ~0.85)
raw_score = quality_score + quantity_score + confidence_score
```

**Stage 1 Example Calculations:**

*Gene with ["Strong", "Definitive", "Supportive"] (e.g., HNF1B):*
- Quality: (0.8² + 1.0² + 0.5²) / (0.8 + 1.0 + 0.5) = 1.89/2.3 = 0.8217 × 0.5 = 0.4109
- Quantity: √(3/5) × 0.3 = 0.7746 × 0.3 = 0.2324
- Confidence: 2/3 × 0.2 = 0.6667 × 0.2 = 0.1333
- **Raw Score: 0.7766**

*Gene with ["Strong", "Definitive"] (e.g., DPAGT1):*
- Quality: (0.8² + 1.0²) / (0.8 + 1.0) = 1.64/1.8 = 0.9111 × 0.5 = 0.4556
- Quantity: √(2/5) × 0.3 = 0.6325 × 0.3 = 0.1897
- Confidence: 2/2 × 0.2 = 1.0 × 0.2 = 0.2000
- **Raw Score: 0.8453** (maximum achievable with 2 classifications)

##### Stage 2: Percentile Normalization

The raw weighted scores have a limited range (~0.28 to ~0.85) because:
- Most genes have only 2-4 classifications (limiting quantity score)
- Perfect scores require 5+ Definitive classifications (rare in practice)
- The formula was designed for theoretical perfection, not real-world distribution

To address this, percentile normalization is applied:

**Stage 2 Implementation:**
```sql
-- Apply percentile ranking to weighted scores
WITH gencc_percentiles AS (
    SELECT 
        gene_id,
        classification_weight as raw_score,
        PERCENT_RANK() OVER (ORDER BY classification_weight) as percentile
    FROM evidence_classification_weights
    WHERE source_name = 'GenCC'
)
SELECT percentile as normalized_score
FROM gencc_percentiles
```

**Benefits of Percentile Normalization:**
- Spreads scores across full 0-1 range (instead of 0.28-0.85)
- Top genes achieve scores near 1.0
- Maintains relative ranking while improving distribution
- Makes GenCC scores comparable to other percentile-normalized sources

**Real-World Results After Both Stages:**

| Gene | Classifications | Raw Score | Percentile | Final Score |
|------|----------------|-----------|------------|-------------|
| DPAGT1 | ["Strong", "Definitive"] | 0.8453 | 93.7% | 0.937 |
| HNF1B | ["Strong", "Definitive", "Supportive"] | 0.7766 | 73.5% | 0.735 |
| PKD1 | ["Strong", "Definitive", "Supportive"] | 0.7766 | 73.5% | 0.735 |
| PKD2 | ["Strong", "Definitive", "Supportive", "Limited"] | 0.7480 | 68.1% | 0.681 |

**Impact on Overall Gene Scores:**
- IFT140: 96.4% (top gene with strong evidence across all sources)
- HNF1B: 90.8% (8th overall, appropriate for important kidney gene)
- PKD2: 90.0% (strong kidney disease gene)
- PKD1: 84.6% (well-established polycystic kidney disease gene)

This two-stage approach ensures:
1. **Meaningful differentiation**: Weighted scoring creates meaningful differences based on quality/quantity
2. **Full range utilization**: Percentile normalization uses the complete 0-1 scale
3. **Fair comparison**: All evidence sources now use comparable 0-1 normalized scores
4. **Accurate ranking**: Important genes score appropriately high

### Final Score Calculation

```sql
-- Raw Score: Sum of all normalized source scores (0 to N)
raw_score = SUM(normalized_scores_across_sources)

-- CORRECTED Percentage Score: Normalized by total active sources (not evidence count)
percentage_score = (raw_score / total_active_sources) * 100
```

**Example Calculation**:
- Gene with 3 sources: PanelApp=0.85, GenCC=0.6, PubTator=0.92  
- Raw score: 0.85 + 0.6 + 0.92 = 2.37
- Total active sources in system: 4 (PanelApp, GenCC, ClinGen, PubTator)
- **Correct percentage score**: (2.37 / 4) × 100 = 59.25%
- ~~Wrong calculation~~: ~~(2.37 / 3) × 100 = 79.0%~~ ❌

**Key Fix (Migration c6a336ffa682)**:
- **BEFORE**: Divided by `evidence_count` (how many sources this gene has evidence from)
- **AFTER**: Divided by `total_active_sources` (total sources in the system)
- **Impact**: Single-source genes now get realistic scores (e.g., CYP24A1: 23.48% not 93.91%)

## Database Schema

### PostgreSQL Views

The scoring system is implemented using a cascade of PostgreSQL views:

1. **`evidence_source_counts`**: Extracts counts from each source type
2. **`evidence_count_percentiles`**: Calculates percentiles for count-based sources
3. **`evidence_classification_weights`**: Maps classifications to weights
4. **`evidence_normalized_scores`**: Combines normalized scores from both tracks
5. **`gene_scores`**: Final scoring view with percentage calculations

### Key View: `gene_scores`

```sql
CREATE OR REPLACE VIEW gene_scores AS
SELECT 
    g.id AS gene_id,
    g.approved_symbol,
    g.hgnc_id,
    COUNT(DISTINCT ens.source_name) AS source_count,
    COUNT(ens.*) AS evidence_count,
    COALESCE(SUM(ens.normalized_score), 0) AS raw_score,
    CASE 
        WHEN COUNT(ens.*) > 0 THEN
            ROUND((COALESCE(SUM(ens.normalized_score), 0) / COUNT(ens.*) * 100)::numeric, 2)
        ELSE 0
    END AS percentage_score,
    jsonb_object_agg(ens.source_name, ens.normalized_score) AS source_percentiles
FROM genes g
LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
GROUP BY g.id, g.approved_symbol, g.hgnc_id
ORDER BY percentage_score DESC NULLS LAST, g.approved_symbol;
```

## Score Interpretation

### Score Ranges
- **90-100%**: Exceptional evidence (top-tier genes with strong evidence across multiple sources)
- **75-89%**: Strong evidence (well-supported genes with good cross-source validation)
- **50-74%**: Moderate evidence (genes with reasonable evidence from multiple sources)  
- **25-49%**: Limited evidence (genes with evidence from few sources or weak evidence)
- **0-24%**: Minimal evidence (genes with very limited or weak evidence)

### Example Real Scores (After Formula Fix)
- **PKD1**: 73.48% (4/4 sources: PanelApp=0.94, GenCC=0.5, ClinGen=0.5, PubTator=1.0)
- **COL4A5**: 59.00% (3/4 sources: PanelApp=0.92, GenCC=0.5, PubTator=0.94)  
- **ACE**: 33.44% (2/4 sources: PanelApp=0.84, GenCC=0.5)
- **CYP24A1**: 23.48% (1/4 sources: PanelApp=0.94 only)

## Performance Characteristics

- **Real-time calculation**: No Python processing required
- **Scalable**: PostgreSQL window functions handle large datasets efficiently
- **Cacheable**: Views can be materialized for even better performance
- **Transparent**: All calculations visible in SQL queries

## Migration Implementation

### Original Implementation
**Migration**: `eb908f8d6701_implement_correct_postgresql_based_.py`

This migration:
1. Removes the broken Python-based scoring system
2. Creates the PostgreSQL view-based scoring system
3. Implements both count-based and classification-based normalization
4. Provides rollback capability

### Weighted GenCC Scoring Update
**Migration**: `1c0a4ff21798_implement_weighted_gencc_scoring_with_3_.py` (August 18, 2025)

This migration enhances GenCC scoring from simple first-classification to weighted multi-component:
1. Implements 3-component weighted scoring (Quality 50%, Quantity 30%, Confidence 20%)
2. Uses quadratic weighting for quality to emphasize higher classifications
3. Applies diminishing returns for quantity using square root normalization
4. Measures consensus through proportion of high-quality classifications
5. Supports all GenCC classification levels including "Supportive"

### GenCC Percentile Normalization
**Migration**: `2d3f4a5b6c7e_normalize_gencc_weighted_scores_with_.py` (August 18, 2025)

This migration adds percentile normalization to GenCC weighted scores:
1. Applies `PERCENT_RANK()` to weighted GenCC scores
2. Spreads scores across the full 0-1 range (was capped at ~0.85)
3. Ensures top genes (2x Definitive) score near 1.0
4. Makes GenCC scores comparable to other percentile-normalized sources
5. Maintains relative ranking while improving score distribution

## Validation Against Original Implementation

This implementation improves upon the original kidney-genetics-v1 R-based system by:

1. **Enhanced Classification Support**: Original R implementation only stored classifications as text; new system scores them numerically
2. **Real-Time Updates**: No batch processing required - scores update immediately when evidence changes
3. **Performance**: PostgreSQL views are much faster than R script processing
4. **Transparency**: All scoring logic visible in database queries
5. **Maintainability**: No separate R environment required

## API Integration

The scoring system integrates seamlessly with the FastAPI backend:

```json
{
  "approved_symbol": "COL4A5",
  "evidence_count": 3,
  "evidence_score": 78.67,
  "sources": ["PanelApp", "GenCC", "PubTator"]
}
```

The `evidence_score` field is populated directly from the `gene_scores.percentage_score` view.

## Future Enhancements

1. **Materialized Views**: For very large datasets, views can be materialized and refreshed periodically
2. **Source Weights**: Global source weights could be added to the final calculation
3. **Temporal Scoring**: Evidence age could influence scoring
4. **Custom Classifications**: Additional classification schemes could be added easily

## Troubleshooting

### Common Issues

1. **Scores showing 0.0**: Check that evidence data contains the expected fields
2. **All scores identical**: Verify percentile calculation is working within sources
3. **Missing sources**: Ensure source names match exactly in classification mappings

### Debugging Queries

```sql
-- Check source count extraction
SELECT * FROM evidence_source_counts WHERE approved_symbol = 'PKD1';

-- Check percentile calculation  
SELECT * FROM evidence_count_percentiles WHERE approved_symbol = 'PKD1';

-- Check classification weights
SELECT * FROM evidence_classification_weights WHERE approved_symbol = 'PKD1';

-- Check final normalized scores
SELECT * FROM evidence_normalized_scores WHERE approved_symbol = 'PKD1';
```

---

**This implementation provides a robust, transparent, and scalable evidence scoring system that accurately reflects the strength and consistency of evidence across multiple data sources.**