# HPO-Based Gene Classification Plan

## Overview
This document outlines the implementation plan for adding HPO phenotype-based classification to genes in the kidney genetics database. The classification system analyzes HPO terms associated with each gene to categorize them across three dimensions: clinical groups (kidney disease types), onset groups (age of manifestation), and syndromic assessment (isolated vs syndromic presentation).

## Key Design Principles
- **DRY (Don't Repeat Yourself)**: Reuse existing HPO pipeline modules and functions
- **KISS (Keep It Simple)**: Store classifications directly in HPO annotations
- **Configuration-driven**: No hardcoded values, all terms and thresholds in config
- **Mathematically sound**: Probabilistic scoring with transparent confidence metrics
- **Gene-level analysis**: Aggregate all HPO terms for a gene (not disease-specific)

## Classification Dimensions

### 1. Clinical Groups (Kidney Disease Types)
Categorize genes based on their predominant kidney disease manifestation:

- **complement**: Complement-mediated kidney diseases
- **cakut**: Congenital anomalies of kidney and urinary tract
- **glomerulopathy**: Glomerular diseases
- **cyst_cilio**: Cystic and ciliopathy disorders
- **tubulopathy**: Tubular disorders
- **nephrolithiasis**: Kidney stones and nephrocalcinosis
- **cancer**: Hereditary kidney cancer syndromes

### 2. Onset Groups
Classify based on typical age of disease onset:

- **adult**: Adult onset (HP:0003581 and descendants)
- **pediatric**: Pediatric/neonatal onset (HP:0410280, HP:0003623 and descendants)
- **congenital**: Congenital/antenatal onset (HP:0003577, HP:0030674 and descendants)

### 3. Syndromic Assessment
Determine if the gene causes isolated kidney disease or syndromic features:

- **is_syndromic**: Boolean flag for presence of extra-renal features
- **extra_renal_categories**: List of affected organ systems
  - growth (HP:0001507 - Growth abnormality)
  - skeletal (HP:0000924 - Skeletal system abnormality)
  - neurologic (HP:0000707 - Abnormality of nervous system)
  - head_neck (HP:0000152 - Head and neck abnormality)

## Implementation Architecture

### Phase 1: Configuration Extension

#### Location: `app/core/datasource_config.py`

Add classification configuration to the HPO section:

```python
"HPO": {
    # ... existing config ...
    
    "clinical_groups": {
        "complement": {
            "signature_terms": [
                "HP:0000093",  # Proteinuria
                "HP:0000100",  # Nephrotic syndrome
                "HP:0001970",  # Tubulointerstitial nephritis
                "HP:0000796",  # Urethral obstruction
                "HP:0003259"   # Elevated serum creatinine
            ],
            "name": "Complement-mediated kidney diseases",
            "weight": 1.0
        },
        "cakut": {
            "signature_terms": [
                "HP:0000107",  # Renal cyst
                "HP:0000085",  # Horseshoe kidney
                "HP:0000089",  # Renal hypoplasia
                "HP:0000072",  # Hydroureter
                "HP:0000126"   # Hydronephrosis
            ],
            "name": "Congenital anomalies of kidney and urinary tract",
            "weight": 1.0
        },
        # ... other groups ...
    },
    
    "onset_groups": {
        "adult": {
            "root_term": "HP:0003581",
            "name": "Adult onset"
        },
        "pediatric": {
            "root_terms": ["HP:0410280", "HP:0003623"],
            "name": "Pediatric/Neonatal onset"
        },
        "congenital": {
            "root_terms": ["HP:0003577", "HP:0030674"],
            "name": "Congenital/Antenatal onset"
        }
    },
    
    "syndromic_indicators": {
        "growth": "HP:0001507",
        "skeletal": "HP:0000924",
        "neurologic": "HP:0000707",
        "head_neck": "HP:0000152"
    },
    
    # Confidence thresholds
    "classification_confidence": {
        "min_terms_low": 5,
        "min_terms_medium": 10,
        "min_terms_high": 15
    }
}
```

### Phase 2: HPO Annotation Source Extension

#### Location: `app/pipeline/sources/annotations/hpo.py`

Add classification methods to the existing HPOAnnotationSource class:

```python
class HPOAnnotationSource(BaseAnnotationSource):
    # ... existing code ...
    
    # Add class-level caches for classification terms
    _clinical_descendants_cache = None
    _onset_descendants_cache = None
    _syndromic_descendants_cache = None
    _classification_cache_time = None
    
    async def get_classification_term_descendants(self, classification_type: str) -> dict[str, set[str]]:
        """
        Get all descendant terms for classification categories.
        Reuses existing HPO pipeline for term traversal.
        """
        # Check cache (24-hour TTL like kidney terms)
        if self._should_refresh_classification_cache():
            await self._refresh_classification_caches()
        
        # Return appropriate cache
        if classification_type == "onset_groups":
            return self._onset_descendants_cache
        elif classification_type == "syndromic_indicators":
            return self._syndromic_descendants_cache
        
        return {}
    
    async def classify_gene_phenotypes(self, phenotypes: list[dict]) -> dict[str, Any]:
        """
        Classify phenotypes into clinical, onset, and syndromic groups.
        
        Args:
            phenotypes: List of HPO phenotype dictionaries
            
        Returns:
            Classification results with scores and confidence
        """
        phenotype_ids = {p.get("id") for p in phenotypes if p.get("id")}
        
        classification = {
            "clinical_group": await self._classify_clinical_group(phenotype_ids, phenotypes),
            "onset_group": await self._classify_onset_group(phenotype_ids),
            "syndromic_assessment": await self._assess_syndromic_features(phenotype_ids)
        }
        
        return classification
    
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        # ... existing code ...
        
        # Add classification if we have phenotypes
        classification = {}
        classification_confidence = "none"
        
        if phenotypes:
            classification = await self.classify_gene_phenotypes(phenotypes)
            classification_confidence = self._calculate_confidence(len(phenotypes))
        
        return {
            # ... existing fields ...
            "phenotypes": phenotypes,
            "kidney_phenotypes": kidney_phenotypes,
            
            # NEW: Classification fields
            "classification": classification,
            "classification_confidence": classification_confidence,
            
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
```

### Phase 3: Classification Algorithm Implementation

#### Clinical Group Classification
Uses signature HPO terms characteristic of each kidney disease group:

```python
async def _classify_clinical_group(self, phenotype_ids: set[str], phenotypes: list[dict]) -> dict:
    """
    Classify into clinical kidney disease groups based on signature terms.
    """
    from app.core.datasource_config import get_source_parameter
    
    config = get_source_parameter("HPO", "clinical_groups", {})
    
    scores = {}
    all_matches = {}
    
    for group_key, group_config in config.items():
        signature_terms = set(group_config.get("signature_terms", []))
        
        # Direct matches with signature terms
        matches = phenotype_ids.intersection(signature_terms)
        
        # Calculate score based on matches and weight
        weight = group_config.get("weight", 1.0)
        if signature_terms:
            score = (len(matches) / len(signature_terms)) * weight
        else:
            score = 0.0
            
        scores[group_key] = round(score, 3)
        if matches:
            all_matches[group_key] = list(matches)
    
    # Normalize scores to sum to 1.0
    total_score = sum(scores.values())
    if total_score > 0:
        scores = {k: round(v/total_score, 3) for k, v in scores.items()}
    
    # Determine primary group (highest score)
    primary = max(scores, key=scores.get) if scores and max(scores.values()) > 0 else None
    
    return {
        "primary": primary,
        "scores": scores,
        "supporting_terms": all_matches.get(primary, []) if primary else []
    }
```

#### Onset Group Classification
Uses HPO term hierarchy to identify onset-related phenotypes:

```python
async def _classify_onset_group(self, phenotype_ids: set[str]) -> dict:
    """
    Classify based on age of onset using HPO term hierarchy.
    """
    # Get cached descendants for onset groups
    onset_descendants = await self.get_classification_term_descendants("onset_groups")
    
    scores = {}
    for group_key, descendant_terms in onset_descendants.items():
        matches = phenotype_ids.intersection(descendant_terms)
        scores[group_key] = len(matches)
    
    # Normalize scores to probabilities
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v/total, 3) for k, v in scores.items()}
    
    primary = max(scores, key=scores.get) if scores and max(scores.values()) > 0 else None
    
    return {
        "primary": primary,
        "scores": scores
    }
```

#### Syndromic Assessment
Identifies extra-renal manifestations to determine if gene causes syndromic disease:

```python
async def _assess_syndromic_features(self, phenotype_ids: set[str]) -> dict:
    """
    Assess syndromic features based on extra-renal phenotypes.
    """
    # Get descendants for syndromic indicator terms
    syndromic_descendants = await self.get_classification_term_descendants("syndromic_indicators")
    
    # Get kidney term descendants for exclusion
    kidney_term_ids = await self.get_kidney_term_descendants()
    
    # Find non-kidney phenotypes
    non_kidney_phenotypes = phenotype_ids - kidney_term_ids
    
    extra_renal_features = {}
    for category, descendant_terms in syndromic_descendants.items():
        matches = non_kidney_phenotypes.intersection(descendant_terms)
        if matches:
            extra_renal_features[category] = len(matches)
    
    # Calculate syndromic score (0-1 range)
    total_extra_renal = sum(extra_renal_features.values())
    syndromic_score = min(1.0, total_extra_renal / 10) if total_extra_renal > 0 else 0.0
    
    is_syndromic = syndromic_score >= 0.3  # Threshold for syndromic classification
    
    return {
        "is_syndromic": is_syndromic,
        "extra_renal_categories": list(extra_renal_features.keys()),
        "extra_renal_term_counts": extra_renal_features,
        "syndromic_score": round(syndromic_score, 3)
    }
```

### Phase 4: Confidence Calculation

```python
def _calculate_confidence(self, phenotype_count: int) -> str:
    """
    Calculate classification confidence based on number of phenotypes.
    """
    from app.core.datasource_config import get_source_parameter
    
    thresholds = get_source_parameter("HPO", "classification_confidence", {})
    
    if phenotype_count >= thresholds.get("min_terms_high", 15):
        return "high"
    elif phenotype_count >= thresholds.get("min_terms_medium", 10):
        return "medium"
    elif phenotype_count >= thresholds.get("min_terms_low", 5):
        return "low"
    else:
        return "insufficient"
```

### Phase 5: API Response Structure

The HPO annotation will include classification data:

```json
{
  "gene_symbol": "PKD1",
  "ncbi_gene_id": "5310",
  "has_hpo_data": true,
  "phenotypes": [
    {"id": "HP:0005562", "name": "Multiple renal cysts", "definition": "..."},
    {"id": "HP:0001737", "name": "Pancreatic cysts", "definition": "..."}
  ],
  "phenotype_count": 31,
  "kidney_phenotypes": [...],
  "kidney_phenotype_count": 11,
  "has_kidney_phenotype": true,
  
  "classification": {
    "clinical_group": {
      "primary": "cyst_cilio",
      "scores": {
        "cyst_cilio": 0.650,
        "cakut": 0.150,
        "glomerulopathy": 0.050,
        "tubulopathy": 0.100,
        "complement": 0.025,
        "nephrolithiasis": 0.025
      },
      "supporting_terms": ["HP:0005562", "HP:0000107", "HP:0001737"]
    },
    "onset_group": {
      "primary": "adult",
      "scores": {
        "adult": 0.700,
        "pediatric": 0.200,
        "congenital": 0.100
      }
    },
    "syndromic_assessment": {
      "is_syndromic": true,
      "extra_renal_categories": ["neurologic", "skeletal"],
      "extra_renal_term_counts": {
        "neurologic": 3,
        "skeletal": 2
      },
      "syndromic_score": 0.500
    }
  },
  "classification_confidence": "high",
  
  "diseases": [...],
  "disease_count": 2,
  "last_updated": "2025-01-26T08:00:00Z"
}
```

### Phase 6: Database Optimization

Create materialized view for efficient filtering and querying:

```sql
CREATE MATERIALIZED VIEW gene_hpo_classifications AS
SELECT 
    ga.gene_id,
    g.approved_symbol as gene_symbol,
    ga.annotations->>'ncbi_gene_id' as ncbi_gene_id,
    ga.annotations->'classification'->'clinical_group'->>'primary' as clinical_group,
    ga.annotations->'classification'->'clinical_group'->'scores' as clinical_scores,
    ga.annotations->'classification'->'onset_group'->>'primary' as onset_group,
    ga.annotations->'classification'->'onset_group'->'scores' as onset_scores,
    (ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean as is_syndromic,
    (ga.annotations->'classification'->'syndromic_assessment'->>'syndromic_score')::float as syndromic_score,
    ga.annotations->'classification'->'syndromic_assessment'->'extra_renal_categories' as extra_renal_categories,
    ga.annotations->>'classification_confidence' as confidence,
    (ga.annotations->>'phenotype_count')::integer as phenotype_count,
    (ga.annotations->>'kidney_phenotype_count')::integer as kidney_phenotype_count,
    ga.updated_at as last_classified
FROM gene_annotations ga
JOIN genes g ON ga.gene_id = g.id
WHERE ga.source = 'hpo'
  AND ga.annotations ? 'classification';

-- Create indexes for common queries
CREATE INDEX idx_gene_hpo_clinical_group ON gene_hpo_classifications(clinical_group);
CREATE INDEX idx_gene_hpo_onset_group ON gene_hpo_classifications(onset_group);
CREATE INDEX idx_gene_hpo_syndromic ON gene_hpo_classifications(is_syndromic);
CREATE INDEX idx_gene_hpo_confidence ON gene_hpo_classifications(confidence);
```

### Phase 7: Summary Fields for Gene Table

Add summary fields to the `get_summary_fields()` method:

```python
def get_summary_fields(self) -> dict[str, str]:
    """
    Get fields to include in materialized view.
    Returns mapping of JSONB paths to column names.
    """
    return {
        # ... existing fields ...
        "hpo_ncbi_gene_id": "annotations->>'ncbi_gene_id'",
        "has_hpo_phenotypes": "(annotations->>'has_hpo_data')::BOOLEAN",
        "hpo_phenotype_count": "(annotations->>'phenotype_count')::INTEGER",
        "hpo_disease_count": "(annotations->>'disease_count')::INTEGER",
        "has_kidney_phenotype": "(annotations->>'has_kidney_phenotype')::BOOLEAN",
        "kidney_phenotype_count": "(annotations->>'kidney_phenotype_count')::INTEGER",
        
        # NEW: Classification summary fields
        "hpo_clinical_group": "annotations->'classification'->'clinical_group'->>'primary'",
        "hpo_onset_group": "annotations->'classification'->'onset_group'->>'primary'",
        "hpo_is_syndromic": "(annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::BOOLEAN",
        "hpo_classification_confidence": "annotations->>'classification_confidence'"
    }
```

## Testing Strategy

### Unit Tests
1. Test classification algorithms with known genes:
   - PKD1 → should classify as `cyst_cilio`
   - HNF1B → should classify as `cakut`
   - COL4A5 → should classify as `glomerulopathy`

2. Test confidence calculations with varying phenotype counts

3. Test syndromic assessment with known syndromic vs isolated genes

### Integration Tests
1. Full pipeline test from HPO API to stored classification
2. Verify caching behavior for term descendants
3. Test batch processing of multiple genes
4. Validate API response structure

### Validation Against Known Data
1. Compare classifications with ClinGen expert panel assignments
2. Validate onset groups against OMIM clinical synopsis
3. Cross-reference syndromic assessment with GeneReviews

## Performance Considerations

### Caching Strategy
- Cache classification term descendants for 24 hours (like kidney terms)
- Use class-level caches shared across all instances
- Implement lazy loading for classification caches

### Batch Processing
- Process genes in batches of 10 (existing HPO API limit)
- Reuse existing exponential backoff for API rate limiting
- Parallelize classification calculations where possible

## Migration Path

### Step 1: Deploy Configuration
1. Add classification config to datasource_config.py
2. Deploy without activating classification

### Step 2: Implement Classification Logic
1. Add classification methods to HPOAnnotationSource
2. Test with individual genes
3. Validate classifications against known examples

### Step 3: Backfill Existing Data
1. Run update for all genes with existing HPO annotations
2. Monitor for API rate limits
3. Verify classification distribution

### Step 4: Create Database Views
1. Create materialized view for classifications
2. Add indexes for common queries
3. Schedule regular refresh of materialized view

### Step 5: API Integration
1. Ensure classification data appears in API responses
2. Add filtering endpoints for classification groups
3. Update frontend to display classifications

## Future Enhancements

### Planned Improvements
1. **Machine learning refinement**: Use validated classifications to train model
2. **Disease-specific classification**: When disease-HPO associations available
3. **Temporal analysis**: Track classification changes over time
4. **Multi-dimensional scoring**: Combine with other evidence sources
5. **Expert review integration**: Allow manual classification overrides

### Extensibility
- Easy to add new clinical groups via configuration
- Support for custom classification dimensions
- Pluggable scoring algorithms
- Integration with external ontologies (MONDO, Orphanet)

## References

### Original Implementation
- Location: `kidney-genetics-v1/analyses/C_AnnotateMergedTable/C_AnnotateMergedTable.R`
- Lines: 438-921 (Clinical groups), 734-822 (Onset groups), 825-921 (Syndromic assessment)

### HPO Resources
- HPO Browser: https://hpo.jax.org/
- HPO API: https://ontology.jax.org/api
- HPO Documentation: https://hpo-annotation-qc.readthedocs.io/

### Clinical Group Sources
- ClinGen Kidney Groups: https://clinicalgenome.org/working-groups/clinical-domain/
- PanelApp: https://panelapp.genomicsengland.co.uk/
- Australian Genomics PanelApp: https://panelapp.agha.umccr.org/