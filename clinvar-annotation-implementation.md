# ClinVar Annotation Implementation Plan

## Overview

Implement ClinVar variant annotation for genes using NCBI's eUtils API to fetch pathogenic variant counts and classifications, replacing the previous file download approach with real-time API queries.

## Key Findings from API Testing

### API Endpoints
1. **Search API** (esearch): `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
   - Purpose: Get ClinVar variant IDs for a gene
   - Example: `?db=clinvar&term=PKD1[gene]+AND+single_gene[prop]&retmax=50000&retmode=json`
   - Returns: List of ClinVar variant IDs

2. **Summary API** (esummary): `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi`
   - Purpose: Get variant details including clinical significance
   - Example: `?db=clinvar&id=123,456,789&retmode=json`
   - Returns: Detailed variant information with germline classifications

### Batch Size Limits
- **esearch**: Can retrieve up to 10,000 IDs per request (tested with PKD1: 5,695 variants)
- **esummary**: Reliably works with **500 IDs per batch** (GET method)
  - 500 IDs: ✅ Works reliably
  - 750 IDs: ❌ Fails (likely URL length limit ~4000 chars)
  - 1000 IDs: ❌ Fails
  - POST method: Not functional for this endpoint

## Response Parsing Strategy

### ClinVar API Response Structure
The esummary endpoint returns comprehensive variant data with the following key fields:

#### Per-Variant Data Structure
```json
{
  "uid": "4075751",
  "accession": "VCV004075751",
  "title": "NM_001009944.3(PKD1):c.12188_12189del (p.Leu4063fs)",
  "obj_type": "Deletion",  // Variant type
  "germline_classification": {
    "description": "Pathogenic",  // Clinical significance
    "review_status": "criteria provided, single submitter",
    "last_evaluated": "2025/05/01 00:00",
    "trait_set": [  // Associated conditions
      {
        "trait_name": "Polycystic kidney disease, adult type",
        "trait_xrefs": [
          {"db_source": "OMIM", "db_id": "173900"},
          {"db_source": "MedGen", "db_id": "C3149841"}
        ]
      }
    ]
  },
  "variation_set": [
    {
      "cdna_change": "c.12188_12189del",
      "variation_name": "NM_001009944.3(PKD1):c.12188_12189del (p.Leu4063fs)",
      "variant_type": "Deletion",
      "variation_xrefs": [  // External database references
        {"db_source": "dbSNP", "db_id": "28934595"}
      ]
    }
  ]
}
```

### Key Fields for Our Use Case

1. **Clinical Significance** (`germline_classification.description`):
   - Pathogenic
   - Likely pathogenic
   - Uncertain significance
   - Likely benign
   - Benign
   - Pathogenic/Likely pathogenic (combined)
   - Conflicting classifications of pathogenicity

2. **Review Status** (`germline_classification.review_status`) - Confidence levels:
   - **Level 4** (Highest confidence):
     - "practice guideline"
     - "reviewed by expert panel"
   - **Level 3** (High confidence):
     - "criteria provided, multiple submitters, no conflicts"
   - **Level 2** (Moderate confidence):
     - "criteria provided, conflicting classifications"
     - "criteria provided, single submitter"
   - **Level 1** (Low confidence):
     - "no assertion for the individual variant"
     - "no assertion criteria provided"

3. **Variant Type** (`obj_type`):
   - single nucleotide variant
   - Deletion
   - Duplication
   - Insertion
   - Indel
   - etc.

4. **Associated Traits** (`germline_classification.trait_set`):
   - Disease names with OMIM and MedGen IDs
   - Useful for identifying kidney-specific variants

### Parsing Implementation

```python
def parse_clinvar_variant(variant_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse single variant from ClinVar esummary response."""
    result = {
        'variant_id': variant_data.get('uid'),
        'accession': variant_data.get('accession'),
        'classification': 'Not classified',
        'review_status': 'No data',
        'variant_type': variant_data.get('obj_type'),
        'traits': []
    }
    
    # Extract germline classification
    if 'germline_classification' in variant_data:
        gc = variant_data['germline_classification']
        result['classification'] = gc.get('description', 'Not provided')
        result['review_status'] = gc.get('review_status', 'No assertion')
        
        # Parse associated conditions/traits
        if 'trait_set' in gc:
            for trait in gc['trait_set']:
                result['traits'].append({
                    'name': trait.get('trait_name'),
                    'omim_id': next((x['db_id'] for x in trait.get('trait_xrefs', []) 
                                    if x['db_source'] == 'OMIM'), None)
                })
    
    return result

def aggregate_variants(variants: List[Dict]) -> Dict[str, Any]:
    """Aggregate variants into summary statistics."""
    stats = {
        'total_count': len(variants),
        'pathogenic_count': 0,
        'likely_pathogenic_count': 0,
        'vus_count': 0,
        'benign_count': 0,
        'likely_benign_count': 0,
        'conflicting_count': 0,
        'high_confidence_count': 0,  # Review level 3+
    }
    
    # Review confidence mapping
    high_confidence_statuses = {
        'practice guideline',
        'reviewed by expert panel',
        'criteria provided, multiple submitters, no conflicts'
    }
    
    for variant in variants:
        classification = variant['classification'].lower()
        
        # Count by classification
        if 'pathogenic' in classification and 'likely' not in classification:
            stats['pathogenic_count'] += 1
        elif 'likely pathogenic' in classification:
            stats['likely_pathogenic_count'] += 1
        elif 'uncertain' in classification:
            stats['vus_count'] += 1
        elif 'benign' in classification and 'likely' not in classification:
            stats['benign_count'] += 1
        elif 'likely benign' in classification:
            stats['likely_benign_count'] += 1
        elif 'conflicting' in classification:
            stats['conflicting_count'] += 1
        
        # Count high confidence variants
        if variant['review_status'] in high_confidence_statuses:
            stats['high_confidence_count'] += 1
    
    # Calculate percentages
    if stats['total_count'] > 0:
        stats['high_confidence_percentage'] = (
            stats['high_confidence_count'] / stats['total_count'] * 100
        )
        stats['pathogenic_percentage'] = (
            (stats['pathogenic_count'] + stats['likely_pathogenic_count']) 
            / stats['total_count'] * 100
        )
    
    return stats
```

## Implementation Architecture

### ClinVar Annotation Source Class

```python
# backend/app/pipeline/sources/annotations/clinvar.py

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, timezone
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.models import Gene
from app.core.logging import get_logger

logger = get_logger(__name__)

class ClinVarAnnotationSource(BaseAnnotationSource):
    """
    ClinVar variant annotation source using NCBI eUtils API.
    
    Fetches pathogenic variant counts and classifications for genes.
    Uses a two-step process:
    1. Search for all variant IDs for a gene
    2. Fetch variant details in batches
    
    Key metrics:
    - Total variant count
    - Pathogenic/Likely pathogenic count
    - Benign/Likely benign count
    - VUS (Variant of Uncertain Significance) count
    - Conflicting interpretations count
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_name = "clinvar"
        self.namespace = "clinvar_annotations"
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.batch_size = 500  # Maximum reliable batch size for esummary
        self.search_batch_size = 10000  # Maximum for esearch
    
    def get_cache_ttl(self) -> int:
        """ClinVar updates weekly, cache for 7 days"""
        return 7 * 24 * 3600
    
    async def fetch_annotation(self, gene: Gene) -> Optional[Dict[str, Any]]:
        """
        Fetch ClinVar annotation for a gene.
        
        Returns variant counts by clinical significance:
        - P: Pathogenic
        - LP: Likely pathogenic
        - B: Benign
        - LB: Likely benign
        - VUS: Uncertain significance
        - Conflicting: Conflicting interpretations
        """
        try:
            # Step 1: Search for all variant IDs
            variant_ids = await self._search_variants(gene.approved_symbol)
            
            if not variant_ids:
                return {
                    "gene_symbol": gene.approved_symbol,
                    "total_variants": 0,
                    "variant_summary": "No variants",
                    "pathogenic_count": 0,
                    "likely_pathogenic_count": 0,
                    "vus_count": 0,
                    "benign_count": 0,
                    "likely_benign_count": 0,
                    "conflicting_count": 0,
                    "has_pathogenic": False,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            
            # Step 2: Fetch variant details in batches
            classifications = await self._fetch_variant_classifications(variant_ids)
            
            # Step 3: Count by classification
            counts = self._count_classifications(classifications)
            
            # Format summary string (like old format: "P:24; LP:15; VUS:221")
            summary_parts = []
            if counts["pathogenic"] > 0:
                summary_parts.append(f"P:{counts['pathogenic']}")
            if counts["likely_pathogenic"] > 0:
                summary_parts.append(f"LP:{counts['likely_pathogenic']}")
            if counts["vus"] > 0:
                summary_parts.append(f"VUS:{counts['vus']}")
            if counts["benign"] > 0:
                summary_parts.append(f"B:{counts['benign']}")
            if counts["likely_benign"] > 0:
                summary_parts.append(f"LB:{counts['likely_benign']}")
            if counts["conflicting"] > 0:
                summary_parts.append(f"Conflicting:{counts['conflicting']}")
            
            variant_summary = "; ".join(summary_parts) if summary_parts else "No classified variants"
            
            return {
                "gene_symbol": gene.approved_symbol,
                "total_variants": len(variant_ids),
                "variant_summary": variant_summary,
                "pathogenic_count": counts["pathogenic"],
                "likely_pathogenic_count": counts["likely_pathogenic"],
                "vus_count": counts["vus"],
                "benign_count": counts["benign"],
                "likely_benign_count": counts["likely_benign"],
                "conflicting_count": counts["conflicting"],
                "other_count": counts["other"],
                "has_pathogenic": counts["pathogenic"] > 0 or counts["likely_pathogenic"] > 0,
                "pathogenic_total": counts["pathogenic"] + counts["likely_pathogenic"],
                "benign_total": counts["benign"] + counts["likely_benign"],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch ClinVar data for {gene.approved_symbol}: {e}")
            return None
    
    async def _search_variants(self, gene_symbol: str) -> List[str]:
        """
        Search for all ClinVar variant IDs for a gene.
        
        Uses esearch API with single_gene[prop] to ensure variants
        are specific to this gene (not incidental findings).
        """
        cache_key = f"search:{gene_symbol}"
        
        async def fetch():
            all_ids = []
            retstart = 0
            
            while True:
                # Build search query
                params = {
                    "db": "clinvar",
                    "term": f"{gene_symbol}[gene] AND single_gene[prop]",
                    "retmax": self.search_batch_size,
                    "retstart": retstart,
                    "retmode": "json"
                }
                
                url = f"{self.base_url}/esearch.fcgi"
                response = await self.http_client.get(url, params=params)
                data = response.json()
                
                if "esearchresult" not in data:
                    logger.warning(f"No search results for {gene_symbol}")
                    break
                
                result = data["esearchresult"]
                id_list = result.get("idlist", [])
                all_ids.extend(id_list)
                
                # Check if we have all results
                total_count = int(result.get("count", 0))
                if len(all_ids) >= total_count or len(id_list) < self.search_batch_size:
                    break
                
                retstart += self.search_batch_size
                
                # Rate limiting
                await asyncio.sleep(0.34)  # NCBI recommends max 3 requests/second
            
            logger.info(f"Found {len(all_ids)} ClinVar variants for {gene_symbol}")
            return all_ids
        
        return await self.get_cached_or_fetch(cache_key, fetch)
    
    async def _fetch_variant_classifications(self, variant_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch classification details for variants in batches.
        
        Processes variants in batches of 500 (API limit).
        """
        classifications = []
        
        for i in range(0, len(variant_ids), self.batch_size):
            batch = variant_ids[i:i + self.batch_size]
            batch_data = await self._fetch_batch_summaries(batch)
            classifications.extend(batch_data)
            
            # Rate limiting between batches
            if i + self.batch_size < len(variant_ids):
                await asyncio.sleep(0.34)
        
        return classifications
    
    async def _fetch_batch_summaries(self, variant_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch summaries for a batch of variant IDs.
        
        Returns list of classification data for each variant.
        """
        if not variant_ids:
            return []
        
        # Join IDs with commas for API
        id_string = ",".join(variant_ids)
        
        params = {
            "db": "clinvar",
            "id": id_string,
            "retmode": "json"
        }
        
        url = f"{self.base_url}/esummary.fcgi"
        
        try:
            response = await self.http_client.get(url, params=params)
            data = response.json()
            
            if "result" not in data:
                logger.warning(f"No results in esummary response")
                return []
            
            results = []
            for vid in variant_ids:
                if vid in data["result"]:
                    variant = data["result"][vid]
                    
                    # Extract germline classification
                    classification = None
                    review_status = None
                    
                    if "germline_classification" in variant:
                        germ_class = variant["germline_classification"]
                        classification = germ_class.get("description", "").lower()
                        review_status = germ_class.get("review_status", "")
                    
                    # Some variants might have somatic classification instead
                    elif "somatic_clinical_impact" in variant:
                        som_class = variant["somatic_clinical_impact"]
                        classification = som_class.get("description", "").lower()
                        review_status = som_class.get("review_status", "")
                    
                    results.append({
                        "id": vid,
                        "classification": classification,
                        "review_status": review_status,
                        "title": variant.get("title", ""),
                        "accession": variant.get("accession", "")
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch batch summaries: {e}")
            return []
    
    def _count_classifications(self, classifications: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count variants by classification type.
        
        Maps ClinVar classifications to standard categories.
        """
        counts = {
            "pathogenic": 0,
            "likely_pathogenic": 0,
            "vus": 0,
            "benign": 0,
            "likely_benign": 0,
            "conflicting": 0,
            "other": 0
        }
        
        for item in classifications:
            classification = item.get("classification", "").lower()
            
            if not classification:
                counts["other"] += 1
            elif "pathogenic" in classification and "likely" in classification:
                counts["likely_pathogenic"] += 1
            elif "pathogenic" in classification:
                counts["pathogenic"] += 1
            elif "benign" in classification and "likely" in classification:
                counts["likely_benign"] += 1
            elif "benign" in classification:
                counts["benign"] += 1
            elif "uncertain" in classification or "unknown" in classification:
                counts["vus"] += 1
            elif "conflicting" in classification:
                counts["conflicting"] += 1
            else:
                counts["other"] += 1
        
        return counts
```

### Configuration

Add to `datasource_config.py`:

```python
"ClinVar": {
    "enabled": True,
    "api_url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
    "batch_size": 500,
    "search_batch_size": 10000,
    "rate_limit": 3,  # Max 3 requests per second per NCBI guidelines
    "cache_ttl": 604800,  # 7 days in seconds
    "update_frequency": "weekly",
    "classification_mapping": {
        "pathogenic": ["pathogenic"],
        "likely_pathogenic": ["likely pathogenic", "likely_pathogenic"],
        "uncertain": ["uncertain significance", "unknown significance", "vus"],
        "benign": ["benign"],
        "likely_benign": ["likely benign", "likely_benign"],
        "conflicting": ["conflicting", "conflicting interpretations"]
    }
}
```

### Database Schema

The annotation will be stored in the existing gene_annotations JSONB structure:

```sql
-- Example stored annotation
{
  "gene_symbol": "PKD1",
  "total_variants": 5695,
  "variant_summary": "P:324; LP:189; VUS:4821; B:45; LB:89",
  "pathogenic_count": 324,
  "likely_pathogenic_count": 189,
  "vus_count": 4821,
  "benign_count": 45,
  "likely_benign_count": 89,
  "conflicting_count": 227,
  "other_count": 0,
  "has_pathogenic": true,
  "pathogenic_total": 513,
  "benign_total": 134,
  "last_updated": "2025-08-26T12:00:00Z"
}
```

## API Integration

### Endpoints

Add ClinVar-specific endpoints:

```python
# backend/app/api/endpoints/annotations.py

@router.get("/clinvar/gene/{gene_symbol}")
async def get_clinvar_annotation(
    gene_symbol: str,
    session: SessionDep,
    force_refresh: bool = False
):
    """Get ClinVar variant counts for a gene"""
    gene = await crud.gene.get_by_symbol(session, gene_symbol)
    if not gene:
        raise HTTPException(404, f"Gene {gene_symbol} not found")
    
    # Check cache first
    if not force_refresh:
        cached = await crud.gene_annotation.get_by_gene_and_source(
            session, gene.id, "clinvar"
        )
        if cached and cached.is_fresh():
            return cached.annotations
    
    # Fetch fresh data
    source = ClinVarAnnotationSource(
        db_session=session,
        cache_service=cache_service,
        http_client=http_client
    )
    
    annotation = await source.fetch_annotation(gene)
    
    if annotation:
        # Save to database
        await crud.gene_annotation.upsert(
            session,
            gene_id=gene.id,
            source="clinvar",
            annotations=annotation
        )
    
    return annotation

@router.get("/clinvar/statistics")
async def get_clinvar_statistics(session: SessionDep):
    """Get overall ClinVar annotation statistics"""
    stats = await session.execute("""
        SELECT 
            COUNT(DISTINCT gene_id) as annotated_genes,
            SUM((annotations->>'pathogenic_count')::int) as total_pathogenic,
            SUM((annotations->>'vus_count')::int) as total_vus,
            AVG((annotations->>'total_variants')::int) as avg_variants_per_gene
        FROM gene_annotations
        WHERE source = 'clinvar'
    """)
    return stats.first()
```

## Frontend Display

### Gene Information Card Addition

Add ClinVar section to the Gene Information card:

```vue
<!-- Add to GeneDetail.vue after HPO section -->
<div v-if="clinvarData" class="mt-2">
  <v-divider class="my-1" />
  <div class="text-caption text-medium-emphasis mb-1">ClinVar Variants:</div>
  
  <div class="d-flex align-center flex-wrap ga-1">
    <!-- Total variants -->
    <v-tooltip location="bottom">
      <template #activator="{ props }">
        <v-chip
          color="grey"
          variant="outlined"
          size="x-small"
          density="compact"
          v-bind="props"
        >
          {{ clinvarData.total_variants }} total
        </v-chip>
      </template>
      <div class="pa-2">
        <div class="font-weight-medium">Total ClinVar Variants</div>
        <div class="text-caption">
          All variants reported for {{ gene.approved_symbol }}
        </div>
      </div>
    </v-tooltip>
    
    <!-- Pathogenic/LP chip -->
    <v-tooltip 
      v-if="clinvarData.pathogenic_total > 0" 
      location="bottom"
    >
      <template #activator="{ props }">
        <v-chip
          color="error"
          variant="tonal"
          size="x-small"
          density="compact"
          v-bind="props"
        >
          P/LP: {{ clinvarData.pathogenic_total }}
        </v-chip>
      </template>
      <div class="pa-2">
        <div class="font-weight-medium">Pathogenic Variants</div>
        <div class="text-caption">
          Pathogenic: {{ clinvarData.pathogenic_count }}<br>
          Likely Pathogenic: {{ clinvarData.likely_pathogenic_count }}
        </div>
      </div>
    </v-tooltip>
    
    <!-- VUS chip -->
    <v-tooltip 
      v-if="clinvarData.vus_count > 0" 
      location="bottom"
    >
      <template #activator="{ props }">
        <v-chip
          color="warning"
          variant="outlined"
          size="x-small"
          density="compact"
          v-bind="props"
        >
          VUS: {{ clinvarData.vus_count }}
        </v-chip>
      </template>
      <div class="pa-2">
        <div class="font-weight-medium">Uncertain Significance</div>
        <div class="text-caption">
          Variants with uncertain clinical significance
        </div>
      </div>
    </v-tooltip>
    
    <!-- Benign chip -->
    <v-tooltip 
      v-if="clinvarData.benign_total > 0" 
      location="bottom"
    >
      <template #activator="{ props }">
        <v-chip
          color="success"
          variant="outlined"
          size="x-small"
          density="compact"
          v-bind="props"
        >
          B/LB: {{ clinvarData.benign_total }}
        </v-chip>
      </template>
      <div class="pa-2">
        <div class="font-weight-medium">Benign Variants</div>
        <div class="text-caption">
          Benign: {{ clinvarData.benign_count }}<br>
          Likely Benign: {{ clinvarData.likely_benign_count }}
        </div>
      </div>
    </v-tooltip>
  </div>
</div>
```

## Implementation Timeline

### Phase 1: Core Implementation (Days 1-2)
1. Create ClinVarAnnotationSource class
2. Implement eUtils API integration
3. Add rate limiting and error handling
4. Test with various genes (different variant counts)

### Phase 2: Database Integration (Day 3)
1. Add to annotation pipeline
2. Implement caching strategy
3. Create API endpoints
4. Add to scheduled updates

### Phase 3: Frontend Display (Day 4)
1. Add to Gene Information card
2. Create variant count badges
3. Add tooltips with details
4. Test UI responsiveness

### Phase 4: Testing & Optimization (Day 5)
1. Test batch processing for large genes
2. Optimize caching strategy
3. Add comprehensive error handling
4. Performance testing

## Testing Strategy

### Unit Tests
```python
def test_clinvar_search():
    """Test variant ID search"""
    source = ClinVarAnnotationSource()
    ids = await source._search_variants("PKD1")
    assert len(ids) > 5000  # PKD1 has ~5695 variants
    
def test_batch_processing():
    """Test batch size limits"""
    source = ClinVarAnnotationSource()
    # Test with exactly 500 IDs
    batch_500 = await source._fetch_batch_summaries(ids[:500])
    assert len(batch_500) == 500
    
def test_classification_counting():
    """Test classification categorization"""
    source = ClinVarAnnotationSource()
    classifications = [
        {"classification": "Pathogenic"},
        {"classification": "Likely pathogenic"},
        {"classification": "Uncertain significance"},
        {"classification": "Benign"}
    ]
    counts = source._count_classifications(classifications)
    assert counts["pathogenic"] == 1
    assert counts["likely_pathogenic"] == 1
    assert counts["vus"] == 1
    assert counts["benign"] == 1
```

### Integration Tests
- Test full pipeline for genes with varying variant counts:
  - Small (<100 variants)
  - Medium (100-1000 variants)
  - Large (>5000 variants like PKD1)
- Test error handling for invalid gene symbols
- Test caching behavior

## Performance Considerations

### Optimization Strategies
1. **Caching**: 7-day TTL for variant data
2. **Batch Processing**: Process up to 500 variants per API call
3. **Rate Limiting**: Max 3 requests/second per NCBI guidelines
4. **Async Processing**: Use asyncio for concurrent batch fetching
5. **Database Indexing**: Index on gene_id and source for fast lookups

### Expected Performance
- Small genes (<100 variants): ~1 second
- Medium genes (100-1000 variants): ~2-3 seconds  
- Large genes (>5000 variants): ~15-20 seconds (with caching: <100ms)

## Error Handling

### API Failures
- Retry with exponential backoff (max 3 retries)
- Fall back to cached data if available
- Log errors for monitoring

### Rate Limiting
- Implement token bucket algorithm
- Queue requests when rate limit approached
- Add jitter to prevent thundering herd

## Monitoring

### Metrics to Track
- API response times
- Cache hit rates
- Error rates by gene
- Total variants processed per day
- Rate limit violations

### Alerts
- API failures > 5% in 5 minutes
- Cache hit rate < 80%
- Processing time > 30 seconds for any gene

## Future Enhancements

1. **Variant Details**: Fetch full variant details on demand
2. **Filtering**: Filter by variant type, consequence, review status
3. **Trending**: Track changes in classifications over time
4. **Batch Updates**: Update multiple genes concurrently
5. **Export**: Generate reports with variant lists
6. **WebSocket Updates**: Real-time progress for large genes
7. **GraphQL API**: More flexible querying of variant data

## References

- [NCBI E-utilities Documentation](https://www.ncbi.nlm.nih.gov/books/NBK25499/)
- [ClinVar API Documentation](https://www.ncbi.nlm.nih.gov/clinvar/docs/api/)
- [E-utilities Rate Limiting Guidelines](https://www.ncbi.nlm.nih.gov/books/NBK25497/)
- [ClinVar Data Model](https://www.ncbi.nlm.nih.gov/clinvar/docs/details/)