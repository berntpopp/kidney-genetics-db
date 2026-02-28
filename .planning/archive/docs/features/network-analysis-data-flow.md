# Network Analysis & Clustering: Data Flow

## Overview

The network analysis feature performs protein-protein interaction (PPI) network construction, community detection, and functional enrichment analysis. All data is pre-computed and stored in the database during pipeline runs; network analysis queries this cached data without making external API calls (except for GO enrichment).

---

## Data Sources

### 1. STRING Database (Protein-Protein Interactions)

**Source**: Local flat files from STRING v12.0
**Location**: `backend/data/string/`
**Files**:
- `9606.protein.info.v12.0.txt` - Protein-to-gene mappings
- `9606.protein.physical.links.v12.0.txt` - Physical interaction scores

**Pipeline**: `backend/app/pipeline/sources/annotations/string_ppi.py`
**Storage**: `gene_annotations` table, `source='string_ppi'`

**Data Structure**:
```json
{
  "interactions": [
    {
      "partner_symbol": "WT1",
      "string_score": 950,
      "partner_gene_id": 123
    }
  ],
  "ppi_score": 45.6,
  "interaction_count": 12
}
```

**Update Frequency**: Manual (when new STRING release available)

---

### 2. HPO - Human Phenotype Ontology

**Source**: HPO API at `https://ontology.jax.org/api`
**Pipeline**: `backend/app/pipeline/sources/annotations/hpo.py`
**Storage**: `gene_annotations` table, `source='hpo'`

**Data Structure**:
```json
{
  "phenotypes": [
    {"id": "HP:0000107", "name": "Renal cyst"},
    {"id": "HP:0001250", "name": "Seizure"}
  ],
  "phenotype_count": 2,
  "kidney_phenotypes": [
    {"id": "HP:0000107", "name": "Renal cyst"}
  ],
  "kidney_phenotype_count": 1,
  "has_kidney_phenotype": true
}
```

**Key Point**: Stores **both** all phenotypes AND kidney-filtered subset.
**Update Frequency**: Daily/weekly via pipeline

---

### 3. GO/KEGG - Gene Ontology (Real-time)

**Source**: Enrichr API via GSEApy library
**Pipeline**: None - **not stored** in database
**Storage**: Never cached

**Gene Sets Available**:
- GO_Biological_Process_2023
- GO_Molecular_Function_2023
- GO_Cellular_Component_2023
- KEGG_2021_Human
- Reactome_2022
- WikiPathway_2023_Human

**Rate Limiting**: 2-second minimum interval between calls
**Timeout**: 120 seconds per request

---

## Data Flow

### Phase 1: Network Construction

**Service**: `backend/app/services/network_analysis_service.py`

1. Query `gene_annotations` where `source='string_ppi'`
2. Extract interactions from JSONB with score ≥ min_threshold
3. Build igraph with vertices (genes) and edges (interactions)
4. Edge weights normalized to 0-1 range

**Performance**: <1s for 500 genes
**Caching**: 1-hour in-memory cache

---

### Phase 2: Community Detection (Clustering)

**Algorithms Available**:
- **Leiden** (recommended): High-quality, fast
- **Louvain**: Classic modularity optimization
- **Walktrap**: Random walk-based

**Process**:
1. Run clustering algorithm on graph structure
2. Calculate modularity score
3. Return gene-to-cluster mapping

**Performance**: <2s for 500 genes
**Data Source**: Graph from Phase 1 (no external data)

---

### Phase 3: Functional Enrichment

#### 3A. HPO Enrichment (Pre-stored)

**Service**: `backend/app/services/enrichment_service.py`

**Process**:
1. Query `gene_annotations` where `source='hpo'`
2. Extract HPO terms using PostgreSQL JSONB operators
3. **Use `kidney_phenotypes` field** (kidney-specific filtering)
4. For each HPO term, run Fisher's exact test:
   - Contingency table: cluster vs background
   - **Background**: Only genes with HPO annotations (~2,099)
5. Apply Benjamini-Hochberg FDR correction
6. Return terms with FDR < threshold (default: 0.05)

**Statistical Method**: Fisher's exact test (one-tailed, over-representation)
**Performance**: <3s for typical cluster
**Data Source**: Pre-stored kidney phenotypes

#### 3B. GO Enrichment (Real-time API)

**Process**:
1. Get gene symbols from database
2. **Call Enrichr API** via GSEApy (real-time)
3. Parse results and apply FDR threshold
4. Return enriched terms

**Statistical Method**: Enrichr's combined score algorithm
**Performance**: 10-30s (API latency)
**Data Source**: Live external API call

---

## Database Statistics

From production database (2025-10-09):

| Source | Gene Count | Purpose |
|--------|-----------|---------|
| `string_ppi` | 1,721 | Network construction |
| `hpo` | 2,099 | HPO enrichment |
| `hgnc` | 2,099 | Gene metadata |
| `gnomad` | 2,095 | Constraint scores |
| `gtex` | 2,032 | Expression data |
| `descartes` | 1,959 | Kidney expression |
| `clinvar` | 477 | Variant pathogenicity |
| `mpo_mgi` | 4,996 | Mouse phenotypes |

**Total unique genes with annotations**: 4,996

---

## Performance Metrics

| Operation | Target | Actual |
|-----------|--------|--------|
| Network Construction | <1s (500 genes) | ~300ms |
| Clustering | <2s (500 genes) | ~10ms (cached) |
| HPO Enrichment | <3s | ~1-2s |
| GO Enrichment | <30s | 10-30s (API) |
| **Total Workflow** | <35s | **15-35s** |

---

## Critical Implementation Details

### 1. HPO Enrichment Uses Kidney-Specific Phenotypes

**Query** (`enrichment_service.py:366-385`):
```sql
WITH hpo_genes AS (
    SELECT
        g.approved_symbol,
        jsonb_array_elements(ga.annotations->'kidney_phenotypes') AS phenotype
    FROM gene_annotations ga
    JOIN genes g ON ga.gene_id = g.id
    WHERE ga.source = 'hpo'
)
SELECT
    phenotype->>'id' AS hpo_term_id,
    array_agg(DISTINCT approved_symbol) AS gene_symbols
FROM hpo_genes
GROUP BY phenotype->>'id'
```

**Why**: Focuses enrichment on kidney-related terms, reducing multiple testing burden.

### 2. Background Calculation Fix (2025-10-09)

**Previous Bug**: Used all genes in database (~20,000) as background
**Fixed**: Uses only genes with HPO annotations (~2,099)

**Impact**: Corrected statistical power for enrichment detection

### 3. GO Terms Are Never Stored

GO enrichment always makes live API calls. This ensures:
- Latest GO annotations
- No storage overhead
- Flexibility in gene set selection

**Trade-off**: Slower performance, subject to API rate limits

---

## Data Freshness

| Component | Update Method | Freshness |
|-----------|--------------|-----------|
| STRING PPI | Manual file download | Months (per release) |
| HPO Annotations | Automated pipeline | Daily/weekly |
| Network Graph | On-demand construction | Real-time |
| GO Enrichment | Live API call | Real-time |

---

## References

- **STRING Database**: https://string-db.org/
- **HPO**: https://hpo.jax.org/
- **Enrichr**: https://maayanlab.cloud/Enrichr/
- **Fisher's Exact Test**: Standard over-representation analysis
- **Leiden Algorithm**: Traag et al., Scientific Reports (2019)

---

## Related Documentation

- Technical implementation: `docs/implementation-notes/active/network-analysis-technical.md`
- API endpoints: `backend/app/api/endpoints/network_analysis.py`
- Frontend component: `frontend/src/views/NetworkAnalysis.vue`
