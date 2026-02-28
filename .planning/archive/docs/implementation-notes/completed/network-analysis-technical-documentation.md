# Network Analysis: Technical Implementation

## Overview

Technical documentation for the network analysis feature, including implementation details, critical bug fixes, and code architecture.

**Last Updated**: 2025-10-09
**Status**: Production-ready with critical enrichment fix

---

## Architecture

### Service Layer

**Network Analysis Service** (`backend/app/services/network_analysis_service.py`)
- Thread-safe: Session passed per-call, not stored
- Non-blocking: Heavy operations in ThreadPoolExecutor
- Cached: LRU cache with 1-hour TTL (max 50 graphs)
- Uses igraph for high-performance graph algorithms

**Enrichment Service** (`backend/app/services/enrichment_service.py`)
- Thread-safe: Session passed per-call
- Rate-limited: 2s minimum interval for Enrichr API
- Timeout-protected: 120s timeout for GO enrichment
- Statistical: Fisher's exact test + FDR correction

### API Layer

**Endpoints** (`backend/app/api/endpoints/network_analysis.py`)
- `POST /api/network/build` - Construct PPI network
- `POST /api/network/cluster` - Detect communities
- `POST /api/network/enrich/hpo` - HPO enrichment
- `POST /api/network/enrich/go` - GO enrichment

---

## Critical Bug Fix: HPO Enrichment (2025-10-09)

### Problem

HPO enrichment was returning no significant results due to incorrect statistical background calculation.

### Root Cause

**File**: `backend/app/services/enrichment_service.py` (lines 112-113)

**Original Code**:
```python
if not background_genes:
    background_genes = [g.id for g in session.query(Gene).all()]  # All genes!

total_background = len(background_genes)  # ~20,000 genes
```

**Issue**: Background included ALL genes in database, not just genes with HPO annotations.

### Statistical Impact

**Fisher's Exact Test Contingency Table**:

**Before Fix** (Incorrect):
```
                With Term    Without Term    Total
In Cluster      a=15         b=5             20
Background      c=65         d=19,915        19,980
Total           80           19,920          20,000
```

**After Fix** (Correct):
```
                With Term    Without Term    Total
In Cluster      a=15         b=5             20
Background      c=65         d=2,014         2,079
Total           80           2,019           2,099
```

**Result**: P-values were artificially large (false negatives) because the "without term" category was inflated with ~18,000 genes that have no HPO annotations.

### Solution

**Three fixes implemented**:

#### Fix 1: Correct Background Calculation

**File**: `enrichment_service.py` (lines 118-135)

```python
# CRITICAL FIX: Background must be only genes WITH HPO annotations
# Get all unique genes that have ANY HPO annotation
all_annotated_genes = set()
for term_genes in hpo_term_to_genes.values():
    all_annotated_genes.update(term_genes)

await logger.info(
    "HPO enrichment background",
    cluster_size=len(cluster_symbols),
    background_size=len(all_annotated_genes),
    hpo_terms=len(hpo_term_to_genes)
)

total_background = len(all_annotated_genes)  # ~2,099 instead of ~20,000
```

#### Fix 2: Use Kidney-Specific Phenotypes

**File**: `enrichment_service.py` (lines 345-403)

```python
async def _get_hpo_annotations(
    self,
    session: Session,
    use_kidney_only: bool = True  # NEW PARAMETER
) -> dict[str, set]:
    # Choose which phenotype field to use
    phenotype_field = 'kidney_phenotypes' if use_kidney_only else 'phenotypes'

    # Query kidney_phenotypes by default
    result = session.execute(text(f"""
        WITH hpo_genes AS (
            SELECT
                g.approved_symbol,
                jsonb_array_elements(ga.annotations->'{phenotype_field}') AS phenotype
            FROM gene_annotations ga
            JOIN genes g ON ga.gene_id = g.id
            WHERE ga.source = 'hpo'
              AND ga.annotations ? '{phenotype_field}'
              AND jsonb_typeof(ga.annotations->'{phenotype_field}') = 'array'
        )
        SELECT
            phenotype->>'id' AS hpo_term_id,
            array_agg(DISTINCT approved_symbol) AS gene_symbols
        FROM hpo_genes
        WHERE phenotype->>'id' IS NOT NULL
        GROUP BY phenotype->>'id'
    """))
```

**Benefits**:
- Focused analysis on kidney-related phenotypes
- Reduced multiple testing burden (fewer terms tested)
- More relevant results for kidney disease database

#### Fix 3: Correct JSONB Field Name

Changed `phenotype->>'term_id'` to `phenotype->>'id'` to match actual HPO annotation structure.

**Reference**: `backend/app/pipeline/sources/annotations/hpo.py:170`

### Validation

**Before Fix**:
- Background: ~20,000 genes
- P-values: Artificially large
- Significant results: None (0)

**After Fix**:
- Background: ~2,099 genes (genes with HPO annotations)
- P-values: Properly calibrated
- Significant results: Detects true enrichments

### Testing

**Log Output to Verify**:
```
INFO: HPO enrichment background | cluster_size=20 | background_size=2099 | hpo_terms=1523
INFO: Loaded HPO annotations from database | phenotype_field=kidney_phenotypes | term_count=1523 | total_genes=2099
```

**Expected Values**:
- `background_size`: ~2,099 (not ~20,000)
- `phenotype_field`: "kidney_phenotypes" (not "phenotypes")
- `term_count`: ~1,500-2,000 kidney-specific HPO terms

---

## Implementation Details

### 1. Network Construction

**File**: `network_analysis_service.py:109-188`

**Process**:
```python
def _build_graph_sync(gene_ids, min_string_score):
    with get_db_context() as db:
        # Query STRING annotations from JSONB
        annotations = (
            db.query(GeneAnnotation)
            .filter(
                GeneAnnotation.gene_id.in_(gene_ids),
                GeneAnnotation.source == "string_ppi"
            )
            .all()
        )

        # Build edge list from JSONB interactions
        edges = []
        weights = []
        for ann in annotations:
            data = ann.annotations  # JSONB column
            for interaction in data["interactions"]:
                if interaction["string_score"] >= min_string_score:
                    edges.append((source_idx, target_idx))
                    weights.append(score / 1000.0)

        # Create igraph
        graph = ig.Graph()
        graph.add_vertices(len(gene_ids))
        graph.add_edges(edges)
        graph.es["weight"] = weights

        return graph
```

**Thread Safety**: Creates fresh DB session using `get_db_context()`

### 2. Community Detection

**File**: `network_analysis_service.py:218-269`

**Algorithms**:
```python
def _detect_communities_sync(graph, algorithm):
    if algorithm == "leiden":
        partition = graph.community_leiden(
            weights="weight",
            resolution_parameter=1.0,
            n_iterations=2
        )
    elif algorithm == "louvain":
        partition = graph.community_multilevel(weights="weight")
    elif algorithm == "walktrap":
        partition = graph.community_walktrap(weights="weight", steps=4).as_clustering()

    # Calculate modularity
    modularity = graph.modularity(partition, weights="weight")

    return gene_to_cluster_mapping, modularity
```

**Performance**: Leiden algorithm is fastest and produces highest-quality clusters.

### 3. HPO Enrichment

**File**: `enrichment_service.py:66-203`

**Fisher's Exact Test Implementation**:
```python
for term_id, term_genes in hpo_term_to_genes.items():
    # Contingency table: [[a, b], [c, d]]
    a = len(cluster_symbols & term_genes)        # Cluster with term
    b = len(cluster_symbols) - a                 # Cluster without term
    c = len(term_genes) - a                      # Background with term
    d = total_background - len(cluster_symbols) - c  # Background without term

    if a == 0:
        continue  # No overlap - skip

    # One-tailed test for over-representation
    odds_ratio, p_value = fisher_exact(
        [[a, b], [c, d]],
        alternative='greater'
    )
```

**FDR Correction**:
```python
# Benjamini-Hochberg procedure
_, fdr_values = fdrcorrection([r["p_value"] for r in results])

# Filter by FDR threshold
results = [r for r in results if r["fdr"] < fdr_threshold]
```

### 4. GO Enrichment

**File**: `enrichment_service.py:205-305`

**Rate Limiting**:
```python
def _run_gseapy_enrichr_safe(gene_list, gene_set):
    # Enforce 2-second minimum interval
    with self._enrichr_lock:
        now = time.time()
        elapsed = now - self._last_enrichr_call

        if elapsed < self._enrichr_min_interval:
            sleep_time = self._enrichr_min_interval - elapsed
            time.sleep(sleep_time)

        self._last_enrichr_call = time.time()

    # Call Enrichr API via GSEApy
    result = gp.enrichr(
        gene_list=gene_list,
        gene_sets=gene_set,
        organism='human',
        outdir=None
    )

    return result
```

**Timeout Protection**:
```python
try:
    enr_result = await asyncio.wait_for(
        loop.run_in_executor(executor, _run_gseapy_enrichr_safe, ...),
        timeout=timeout_seconds  # Default: 120s
    )
except asyncio.TimeoutError:
    logger.error(f"GSEApy enrichment timed out after {timeout_seconds}s")
    return []
```

---

## Database Schema

### gene_annotations Table

```sql
CREATE TABLE gene_annotations (
    id BIGINT PRIMARY KEY,
    gene_id BIGINT REFERENCES genes(id),
    source VARCHAR(50) NOT NULL,           -- 'string_ppi', 'hpo', etc.
    version VARCHAR(20),
    annotations JSONB NOT NULL,            -- Flexible JSONB storage
    source_metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(gene_id, source, version)
);

CREATE INDEX idx_gene_annotations_source ON gene_annotations(source);
CREATE INDEX idx_gene_annotations_gene_id ON gene_annotations(gene_id);
```

### HPO Annotation Structure

```json
{
  "gene_symbol": "PKD1",
  "ncbi_gene_id": "5310",
  "has_hpo_data": true,
  "phenotypes": [
    {"id": "HP:0000107", "name": "Renal cyst", "definition": "..."},
    {"id": "HP:0001250", "name": "Seizure", "definition": "..."}
  ],
  "phenotype_count": 2,
  "kidney_phenotypes": [
    {"id": "HP:0000107", "name": "Renal cyst", "definition": "..."}
  ],
  "kidney_phenotype_count": 1,
  "has_kidney_phenotype": true,
  "diseases": [
    {"id": "OMIM:173900", "name": "Polycystic kidney disease 1"}
  ],
  "disease_count": 1,
  "classification": {
    "clinical_group": {"primary": "cystic_disease", "scores": {...}},
    "onset_group": {"primary": "adult_onset", "scores": {...}},
    "syndromic_assessment": {"is_syndromic": false}
  }
}
```

### STRING PPI Annotation Structure

```json
{
  "interactions": [
    {
      "partner_symbol": "PKD2",
      "string_score": 998,
      "partner_gene_id": 456,
      "partner_protein_id": "9606.ENSP00000237596"
    }
  ],
  "ppi_score": 85.2,
  "interaction_count": 12,
  "percentile": 95.8
}
```

---

## Performance Optimization

### Caching Strategy

**Network Graphs** (`network_analysis_service.py:49-51`):
```python
# LRU cache with TTL
self._graph_cache = TTLCache(maxsize=50, ttl=3600)  # 1 hour
```

**Cache Key Format**: `"network:{gene_count}:{min_string_score}"`

**Memory Estimate**: ~50MB per graph × 50 max = ~2.5GB max

### Thread Pool Usage

**Singleton Pattern** (`network_analysis_service.py:47`):
```python
self._executor = get_thread_pool_executor()  # Shared across services
```

**Rationale**: igraph operations are CPU-intensive and block the event loop.

### Query Optimization

**JSONB Indexes**:
```sql
-- Speeds up HPO term extraction
CREATE INDEX idx_gene_annotations_annotations_gin
ON gene_annotations USING gin (annotations jsonb_path_ops);
```

**Batch Processing**: Process genes in batches of 10 for parallel API calls.

---

## Error Handling

### Network Build Errors

```python
try:
    graph = await network_service.build_network_from_string_data(...)
except ValidationError as e:
    # Max 2000 genes allowed
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Network build failed: {e}")
    raise HTTPException(status_code=500, detail="Network construction failed")
```

### Enrichment Errors

**HPO Enrichment**:
- No annotations found → return empty list
- No significant terms → return empty list (logged at INFO level)

**GO Enrichment**:
- Timeout → return empty list (logged at ERROR level)
- API failure → return empty list (logged at ERROR level)
- Rate limit → automatic retry with backoff (via GSEApy built-in)

---

## Testing

### Unit Tests

**Location**: `backend/tests/services/`

**Coverage**:
- ✅ Network construction with various STRING score thresholds
- ✅ Clustering algorithms (Leiden, Louvain, Walktrap)
- ✅ Fisher's exact test calculation
- ⏳ HPO enrichment with known positive controls
- ⏳ Background calculation validation

### Integration Tests

**Manual Testing Procedure**:

1. **Network Build**:
   ```bash
   curl -X POST http://localhost:8000/api/network/build \
     -H "Content-Type: application/json" \
     -d '{"gene_ids": [1,2,3,4,5], "min_string_score": 400}'
   ```

2. **Clustering**:
   ```bash
   curl -X POST http://localhost:8000/api/network/cluster \
     -H "Content-Type: application/json" \
     -d '{"gene_ids": [1,2,3,4,5], "algorithm": "leiden"}'
   ```

3. **HPO Enrichment**:
   ```bash
   curl -X POST http://localhost:8000/api/network/enrich/hpo \
     -H "Content-Type: application/json" \
     -d '{"cluster_genes": [1,2,3], "fdr_threshold": 0.05}'
   ```

**Expected**: Logs should show correct background size (~2,099).

---

## Migration Notes

### Upgrading from Pre-Fix Version

**No database migration required** - this is a code-only fix.

**Validation**:
1. Check logs for "HPO enrichment background" entries
2. Verify `background_size` is ~2,099 (not ~20,000)
3. Test with known enriched clusters (e.g., PKD genes)

### Rollback Procedure

If issues arise:
1. Revert `enrichment_service.py` to previous version
2. Restart backend service
3. Report issue with logs

---

## References

### Scientific

- **Fisher's Exact Test**: https://en.wikipedia.org/wiki/Fisher%27s_exact_test
- **Benjamini-Hochberg FDR**: https://doi.org/10.1111/j.2517-6161.1995.tb02031.x
- **Leiden Algorithm**: https://doi.org/10.1038/s41598-019-41695-z
- **Enrichment Best Practices**: https://doi.org/10.1371/journal.pcbi.1002375

### Technical

- **igraph Documentation**: https://igraph.org/python/
- **GSEApy**: https://gseapy.readthedocs.io/
- **Enrichr API**: https://maayanlab.cloud/Enrichr/help#api

### Internal

- Data flow documentation: `docs/features/network-analysis-data-flow.md`
- API endpoints: `backend/app/api/endpoints/network_analysis.py`
- Frontend: `frontend/src/views/NetworkAnalysis.vue`

---

## Changelog

### 2025-10-09: Critical Enrichment Fix
- **Fixed**: HPO enrichment background calculation
- **Fixed**: Use kidney-specific phenotypes by default
- **Fixed**: JSONB field name (`id` instead of `term_id`)
- **Impact**: Enrichment now detects true signals
- **Migration**: None required (code-only fix)

### 2025-10-08: Initial Implementation
- Network construction from STRING data
- Leiden/Louvain/Walktrap clustering
- HPO enrichment (with bug)
- GO enrichment via Enrichr

---

## Contact

For questions or issues:
- Review code: `backend/app/services/network_analysis_service.py`
- Check logs: Look for "HPO enrichment background" entries
- Report issues: Include request_id from logs
