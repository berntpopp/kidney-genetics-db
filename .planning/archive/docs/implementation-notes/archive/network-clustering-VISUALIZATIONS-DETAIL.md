# Network & Clustering Visualizations - Detailed Specification

**Supplement to**: `network-clustering-analysis-assessment.md`
**Priority**: CRITICAL
**Date**: 2025-10-08

## Executive Summary

This document specifies **EXACTLY** what visualizations and functional enrichment analysis we're implementing. The original assessment focused too heavily on graph topology and missed the critical **biological interpretation** layer.

---

## 1. What We're Actually Building (Visual Mockup)

### 1.1 Main Network View (STRING-DB Style)

```
┌─────────────────────────────────────────────────────────────────┐
│  Protein Interaction Network for "Tubulopathy" genes            │
├─────────────────────────────────────────────────────────────────┤
│  Controls: [Layout ▼] [Min Score: 400 ———●———] [Detect Clusters]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│        ●──────●                    Cluster 1 (Ciliopathy)        │
│        │ SLC9A3 NPHP1               ●──●──●──●                   │
│        │         │                  │           \                │
│        ●─────────●──────●          ●──●        ●─●              │
│      HNF4A     CLCN5    │        /     \      /                 │
│                          ●─────●──────●──────●                  │
│                          │   WT1    PAX2   LMX1B                │
│   Cluster 2 (Transport)  │                                       │
│                          ●  Cluster 3 (Development)              │
│                          │                                       │
│  [Seed gene: square]  [Cluster colors: see legend]             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Stats: 42 nodes | 127 edges | 3 clusters | Modularity: 0.45   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Enrichment Analysis Panel (CRITICAL - NEW!)

```
┌─────────────────────────────────────────────────────────────────┐
│  Functional Enrichment for Cluster 1 (17 genes)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [HPO Terms] [GO Biological Process] [KEGG Pathways]            │
│                                                                  │
│  Top Enriched HPO Phenotypes:                                   │
│  ┌────────────────────────────────────────┬─────────┬────────┐  │
│  │ Term                                   │ P-value │ Genes  │  │
│  ├────────────────────────────────────────┼─────────┼────────┤  │
│  │ HP:0000107 Renal cyst                  │ 1.2e-12 │ 14/17  │  │
│  │ HP:0000083 Renal insufficiency         │ 3.4e-10 │ 12/17  │  │
│  │ HP:0000097 Focal segmental...          │ 5.1e-08 │ 9/17   │  │
│  └────────────────────────────────────────┴─────────┴────────┘  │
│                                                                  │
│  Visualization:                                                 │
│                                                                  │
│  Renal cyst          ████████████████████████ 14                │
│  Renal insufficiency ██████████████████       12                │
│  Focal segmental...  ████████████             9                 │
│                                                                  │
│  [Export CSV] [Show Dotplot] [Show Heatmap]                     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Enrichment Dotplot (ClusterProfiler Style)

```
┌─────────────────────────────────────────────────────────────────┐
│  HPO Enrichment Dotplot (All Clusters)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                   Cluster 1    Cluster 2    Cluster 3           │
│                                                                  │
│  Renal cyst         ●●●           ○            ○                │
│                   (14/17)                                        │
│                                                                  │
│  Tubulopathy         ●●          ●●●           ○                │
│                                (12/15)                           │
│                                                                  │
│  Proteinuria          ●          ●●          ●●●                │
│                                           (10/12)                │
│                                                                  │
│  ● = p < 0.001                                                  │
│  Circle size = Gene ratio  |  Color intensity = -log10(p-value) │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 Cluster Dendrogram + Heatmap

```
┌─────────────────────────────────────────────────────────────────┐
│  Hierarchical Clustering (Leiden Algorithm)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dendrogram:                      Clinical Group                │
│                                   ┌─ Tubulopathy                │
│      ┌──────────────┐             ├─ Glomerulopathy             │
│      │              │             ├─ CAKUT                      │
│   ┌──┴──┐        ┌──┴───┐        └─ Cystic/Cilio              │
│   │     │        │      │                                       │
│  C1    C2       C3     C4        Heatmap (STRING PPI scores):  │
│  ▓▓    ▓▓       ░░     ▓▓                                       │
│                                   WT1  [▓▓▓▓▓▓▓▓░░░░]            │
│  Legend:                          PAX2 [▓▓▓▓▓▓░░░░░░]            │
│  ▓▓ = High PPI                    SIX2 [▓▓▓▓░░░░░░░░]            │
│  ░░ = Low PPI                     ...                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Functional Enrichment Analysis (CRITICAL ADDITION)

### 2.1 Why This is Essential

**Problem**: Network clusters are meaningless without biological interpretation.

**Example**:
- Cluster 1 has 17 genes with dense connections
- **So what?** What do they DO biologically?
- **Answer**: HPO enrichment shows they're all ciliopathy genes
- **Insight**: This cluster represents a disease module

### 2.2 Enrichment Data Sources

| Source | Status | Use Case | Implementation |
|--------|--------|----------|----------------|
| **HPO (Human Phenotype Ontology)** | ✅ HAVE DATA | Kidney phenotypes | `backend/app/core/hpo/` |
| **Clinical Groups** | ✅ HAVE DATA (v1) | Tubulopathy, glomerulopathy, etc. | From v1 analysis |
| **GO (Gene Ontology)** | ❌ NEED | Molecular function, biological process | Add GOA tools/GSEApy |
| **KEGG Pathways** | ❌ NEED | Metabolic/signaling pathways | GSEApy API |
| **Reactome** | ❌ OPTIONAL | Detailed pathway diagrams | Phase 3 |

### 2.3 Enrichment Algorithm

**Fisher's Exact Test** (over-representation analysis):

```
Cluster genes (17)     All genes (571)
─────────────────────────────────────
With HPO term: 14      80
Without term:   3     491
─────────────────────────────────────
P-value = Fisher's exact test
FDR = Benjamini-Hochberg correction
```

**Implementation Options**:

1. **GSEApy** (Recommended - Phase 1):
   ```python
   import gseapy as gp

   enr = gp.enrichr(
       gene_list=['WT1', 'PAX2', 'SIX2', ...],  # Cluster genes
       gene_sets='GO_Biological_Process_2023',
       organism='human',
       outdir='results'
   )

   # Returns: term, p-value, adjusted p-value, genes, ...
   ```

2. **Manual with scipy** (Fallback):
   ```python
   from scipy.stats import fisher_exact
   import statsmodels.stats.multitest as multi

   # For each HPO term:
   odds_ratio, p_value = fisher_exact([[a, b], [c, d]])

   # Multiple testing correction:
   reject, pvals_corrected = multi.fdrcorrection(p_values)
   ```

### 2.4 Backend Service Design

**New Module**: `backend/app/services/enrichment_service.py`

```python
"""
Functional enrichment analysis for gene clusters.

Integrates with:
- HPO API (existing app/core/hpo/)
- GSEApy (GO, KEGG, Reactome)
- Custom clinical groups
"""

import asyncio
from typing import Dict, List, Any
import gseapy as gp
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import fdrcorrection

from app.core.logging import get_logger
from app.core.hpo.annotations import HPOAnnotations
from app.models.gene import Gene

logger = get_logger(__name__)


class EnrichmentService:
    """Service for functional enrichment analysis."""

    def __init__(self):
        """Initialize WITHOUT session (pass session per-call for thread safety)."""
        self.hpo_api = HPOAnnotations()
        self._executor = get_thread_pool_executor()  # Use singleton from database.py

        # Rate limiting for GSEApy/Enrichr API
        self._last_enrichr_call = 0
        self._enrichr_min_interval = 2.0  # 2 seconds between calls
        self._enrichr_lock = threading.Lock()

    async def enrich_hpo_terms(
        self,
        cluster_genes: List[int],  # Gene IDs
        session: Session,  # ✅ Session passed per-call
        background_genes: List[int] = None,  # All genes (default: all in DB)
        fdr_threshold: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Perform HPO term enrichment for a gene cluster.

        Uses existing HPO annotations from database + HPO API.

        Returns:
        [
            {
                "term_id": "HP:0000107",
                "term_name": "Renal cyst",
                "p_value": 1.2e-12,
                "fdr": 2.3e-10,
                "gene_count": 14,
                "cluster_size": 17,
                "genes": ["WT1", "PAX2", ...],
                "enrichment_score": 8.5
            },
            ...
        ]
        """
        # Get gene symbols
        cluster_gene_objs = (
            session.query(Gene)
            .filter(Gene.id.in_(cluster_genes))
            .all()
        )
        cluster_symbols = [g.approved_symbol for g in cluster_gene_objs]

        if not background_genes:
            background_genes = [g.id for g in session.query(Gene).all()]

        # Get HPO annotations from database
        # (Uses JSONB operators to extract HPO terms)
        hpo_term_to_genes = await self._get_hpo_annotations(session)

        # Perform enrichment test for each HPO term
        results = []
        p_values = []

        for term_id, term_genes in hpo_term_to_genes.items():
            # Contingency table
            a = len(set(cluster_symbols) & term_genes)  # Cluster with term
            b = len(cluster_symbols) - a                 # Cluster without term
            c = len(term_genes) - a                      # Background with term
            d = len(background_genes) - len(cluster_symbols) - c  # Background without

            if a == 0:
                continue  # No overlap

            odds_ratio, p_value = fisher_exact([[a, b], [c, d]], alternative='greater')
            p_values.append(p_value)

            results.append({
                "term_id": term_id,
                "term_name": await self._get_hpo_term_name(term_id),
                "p_value": p_value,
                "gene_count": a,
                "cluster_size": len(cluster_symbols),
                "background_count": len(term_genes),
                "genes": list(set(cluster_symbols) & term_genes),
                "odds_ratio": odds_ratio
            })

        # Multiple testing correction
        if results:
            _, fdr_values = fdrcorrection([r["p_value"] for r in results])
            for i, result in enumerate(results):
                result["fdr"] = fdr_values[i]
                result["enrichment_score"] = -np.log10(result["fdr"])

        # Filter and sort
        results = [r for r in results if r["fdr"] < fdr_threshold]
        results.sort(key=lambda x: x["fdr"])

        logger.sync_info(
            f"HPO enrichment found {len(results)} significant terms",
            cluster_size=len(cluster_symbols),
            threshold=fdr_threshold
        )

        return results

    async def enrich_go_terms(
        self,
        cluster_genes: List[int],
        session: Session,  # ✅ Session passed per-call
        gene_set: str = "GO_Biological_Process_2023",
        fdr_threshold: float = 0.05,
        timeout_seconds: int = 120  # ✅ ADD TIMEOUT
    ) -> List[Dict[str, Any]]:
        """
        Perform GO enrichment using GSEApy with timeout and rate limiting.

        Args:
            cluster_genes: Gene IDs in cluster
            session: Database session
            gene_set: GSEApy gene set name
            fdr_threshold: FDR cutoff
            timeout_seconds: Maximum time to wait for API response

        Returns: Enrichment results in same format as enrich_hpo_terms
        """
        # Get gene symbols
        genes = (
            session.query(Gene)
            .filter(Gene.id.in_(cluster_genes))
            .all()
        )
        gene_symbols = [g.approved_symbol for g in genes]

        # Run GSEApy enrichment with timeout (blocks, so offload to thread)
        loop = asyncio.get_event_loop()

        try:
            enr_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    self._run_gseapy_enrichr_safe,  # ✅ Uses rate limiting
                    gene_symbols,
                    gene_set
                ),
                timeout=timeout_seconds
            )

            if enr_result is None:
                # API failed, return empty
                logger.sync_warning("GSEApy enrichment returned None")
                return []

        except asyncio.TimeoutError:
            logger.sync_error(
                f"GSEApy enrichment timed out after {timeout_seconds}s",
                gene_count=len(gene_symbols),
                gene_set=gene_set
            )
            return []
        except Exception as e:
            logger.sync_error(f"GSEApy enrichment failed: {e}")
            return []

        # Convert to our format
        results = []
        for _, row in enr_result.results.iterrows():
            if row['Adjusted P-value'] > fdr_threshold:
                continue

            results.append({
                "term_id": row['Term'],
                "term_name": row['Term'],  # GSEApy uses same for both
                "p_value": row['P-value'],
                "fdr": row['Adjusted P-value'],
                "gene_count": len(row['Genes'].split(';')),
                "cluster_size": len(gene_symbols),
                "genes": row['Genes'].split(';'),
                "enrichment_score": -np.log10(row['Adjusted P-value']),
                "combined_score": row['Combined Score']  # Enrichr-specific
            })

        logger.sync_info(
            f"GO enrichment found {len(results)} significant terms",
            gene_set=gene_set,
            cluster_size=len(gene_symbols)
        )

        return results

    def _run_gseapy_enrichr_safe(self, gene_list: List[str], gene_set: str):
        """
        Synchronous GSEApy call with rate limiting (runs in thread pool).

        ✅ Rate limits API calls to prevent Enrichr IP blocking
        ✅ Handles API failures gracefully
        """
        import time

        # Rate limiting: Wait if called too recently
        with self._enrichr_lock:
            now = time.time()
            elapsed = now - self._last_enrichr_call
            if elapsed < self._enrichr_min_interval:
                sleep_time = self._enrichr_min_interval - elapsed
                logger.sync_debug(f"Rate limiting: sleeping {sleep_time:.2f}s before Enrichr call")
                time.sleep(sleep_time)

            self._last_enrichr_call = time.time()

        # Call GSEApy (has built-in retry=5)
        try:
            result = gp.enrichr(
                gene_list=gene_list,
                gene_sets=gene_set,
                organism='human',
                outdir=None  # Don't save files
            )
            return result
        except Exception as e:
            logger.sync_error(f"GSEApy API error: {e}")
            # Return None to signal failure
            return None

    async def _get_hpo_annotations(self, session: Session) -> Dict[str, set]:
        """
        Get HPO term → genes mapping from database using JSONB operators.

        Returns: {"HP:0000107": {"WT1", "PAX2", ...}, ...}
        """
        from sqlalchemy import text

        # ✅ Use PostgreSQL JSONB operators to extract HPO terms from nested structure
        result = session.execute(text("""
            WITH hpo_genes AS (
                SELECT
                    g.approved_symbol,
                    jsonb_array_elements(ga.annotations->'phenotypes') AS phenotype
                FROM gene_annotations ga
                JOIN genes g ON ga.gene_id = g.id
                WHERE ga.source = 'hpo'
                  AND ga.annotations ? 'phenotypes'
            )
            SELECT
                phenotype->>'term_id' AS hpo_term_id,
                array_agg(DISTINCT approved_symbol) AS gene_symbols
            FROM hpo_genes
            GROUP BY phenotype->>'term_id'
        """))

        hpo_to_genes = {}
        for row in result:
            hpo_to_genes[row.hpo_term_id] = set(row.gene_symbols)

        logger.sync_info(f"Loaded {len(hpo_to_genes)} HPO terms from database")
        return hpo_to_genes

    async def _get_hpo_term_name(self, hpo_id: str) -> str:
        """Get HPO term name from API or cache."""
        term_info = await self.hpo_api.get_term(hpo_id)
        return term_info.name if term_info else hpo_id
```

### 2.5 API Endpoints

**New Endpoints**: `backend/app/api/endpoints/enrichment.py`

```python
"""
Enrichment analysis API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from app.api.dependencies import get_db
from app.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


@router.post("/hpo")
async def enrich_hpo(
    gene_ids: List[int],
    fdr_threshold: float = Query(0.05, ge=0, le=1),
    db = Depends(get_db)
):
    """
    Perform HPO phenotype enrichment for gene list.

    POST /api/enrichment/hpo
    Body: {"gene_ids": [1, 2, 3, ...], "fdr_threshold": 0.05}

    Returns: [
        {
            "term_id": "HP:0000107",
            "term_name": "Renal cyst",
            "p_value": 1.2e-12,
            "fdr": 2.3e-10,
            "gene_count": 14,
            ...
        },
        ...
    ]
    """
    service = EnrichmentService(db)
    results = await service.enrich_hpo_terms(gene_ids, fdr_threshold=fdr_threshold)
    return {"results": results, "total": len(results)}


@router.post("/go")
async def enrich_go(
    gene_ids: List[int],
    gene_set: str = Query("GO_Biological_Process_2023"),
    fdr_threshold: float = Query(0.05, ge=0, le=1),
    db = Depends(get_db)
):
    """
    Perform GO enrichment using GSEApy.

    Available gene sets:
    - GO_Biological_Process_2023
    - GO_Molecular_Function_2023
    - GO_Cellular_Component_2023
    - KEGG_2021_Human
    - Reactome_2022
    """
    service = EnrichmentService(db)
    results = await service.enrich_go_terms(gene_ids, gene_set, fdr_threshold)
    return {"results": results, "gene_set": gene_set, "total": len(results)}


@router.post("/cluster-enrichment")
async def enrich_clusters(
    clusters: Dict[int, List[int]],  # {cluster_id: [gene_ids]}
    enrichment_type: str = Query("hpo", regex="^(hpo|go|kegg)$"),
    db = Depends(get_db)
):
    """
    Perform enrichment for multiple clusters at once.

    Returns: {
        "cluster_1": [...enrichment results...],
        "cluster_2": [...enrichment results...],
        ...
    }
    """
    service = EnrichmentService(db)
    results = {}

    for cluster_id, gene_ids in clusters.items():
        if enrichment_type == "hpo":
            results[f"cluster_{cluster_id}"] = await service.enrich_hpo_terms(gene_ids)
        elif enrichment_type == "go":
            results[f"cluster_{cluster_id}"] = await service.enrich_go_terms(gene_ids)

    return results
```

---

## 3. Frontend Visualization Components

### 3.1 Enrichment Results Table

**Component**: `frontend/src/components/enrichment/EnrichmentTable.vue`

```vue
<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-chart-box</v-icon>
      Functional Enrichment Results
    </v-card-title>

    <v-card-text>
      <!-- Filter Controls -->
      <v-row>
        <v-col cols="12" md="4">
          <v-select
            v-model="enrichmentType"
            :items="enrichmentTypes"
            label="Enrichment Type"
            density="compact"
            @update:model-value="loadEnrichment"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model="searchTerm"
            label="Search terms"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            clearable
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-slider
            v-model="fdrThreshold"
            :min="0.001"
            :max="0.1"
            :step="0.001"
            label="FDR threshold"
            thumb-label
          />
        </v-col>
      </v-row>

      <!-- Results Table -->
      <v-data-table
        :headers="headers"
        :items="filteredResults"
        :loading="loading"
        density="compact"
        :items-per-page="10"
      >
        <template #item.term_name="{ item }">
          <v-tooltip location="top">
            <template #activator="{ props }">
              <span v-bind="props" class="term-link">
                {{ item.term_name }}
              </span>
            </template>
            <div class="pa-2">
              <div class="font-weight-bold">{{ item.term_id }}</div>
              <div class="text-caption">{{ item.term_name }}</div>
              <div class="text-caption mt-1">
                Genes: {{ item.genes.join(', ') }}
              </div>
            </div>
          </v-tooltip>
        </template>

        <template #item.fdr="{ item }">
          <v-chip
            :color="getFdrColor(item.fdr)"
            size="small"
            variant="flat"
          >
            {{ item.fdr.toExponential(2) }}
          </v-chip>
        </template>

        <template #item.gene_ratio="{ item }">
          <div class="d-flex align-center">
            <span>{{ item.gene_count }}/{{ item.cluster_size }}</span>
            <v-progress-linear
              :model-value="(item.gene_count / item.cluster_size) * 100"
              :color="getGeneRatioColor(item.gene_count / item.cluster_size)"
              height="6"
              class="ml-2"
              style="width: 60px"
            />
          </div>
        </template>

        <template #item.enrichment_score="{ item }">
          <v-sparkline
            :value="[item.enrichment_score]"
            :max="maxEnrichmentScore"
            color="primary"
            height="20"
            :width="40"
            line-width="2"
            type="bar"
          />
        </template>
      </v-data-table>

      <!-- Action Buttons -->
      <v-row class="mt-4">
        <v-col>
          <v-btn
            prepend-icon="mdi-chart-scatter-plot"
            color="primary"
            @click="showDotplot"
          >
            Show Dotplot
          </v-btn>
          <v-btn
            prepend-icon="mdi-chart-bar"
            color="secondary"
            class="ml-2"
            @click="showBarplot"
          >
            Show Barplot
          </v-btn>
          <v-btn
            prepend-icon="mdi-download"
            variant="outlined"
            class="ml-2"
            @click="exportCSV"
          >
            Export CSV
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

const props = defineProps({
  geneIds: {
    type: Array,
    required: true
  },
  clusterId: {
    type: Number,
    default: null
  }
})

const enrichmentType = ref('hpo')
const enrichmentTypes = [
  { title: 'HPO Phenotypes', value: 'hpo' },
  { title: 'GO Biological Process', value: 'go_bp' },
  { title: 'GO Molecular Function', value: 'go_mf' },
  { title: 'KEGG Pathways', value: 'kegg' }
]

const searchTerm = ref('')
const fdrThreshold = ref(0.05)
const results = ref([])
const loading = ref(false)

const headers = [
  { title: 'Term', value: 'term_name', width: '30%' },
  { title: 'FDR', value: 'fdr', width: '15%' },
  { title: 'Gene Ratio', value: 'gene_ratio', width: '20%' },
  { title: 'Enrichment', value: 'enrichment_score', width: '15%' },
  { title: 'Genes', value: 'gene_count', width: '10%' }
]

const filteredResults = computed(() => {
  let filtered = results.value.filter(r => r.fdr <= fdrThreshold.value)

  if (searchTerm.value) {
    const search = searchTerm.value.toLowerCase()
    filtered = filtered.filter(r =>
      r.term_name.toLowerCase().includes(search) ||
      r.term_id.toLowerCase().includes(search)
    )
  }

  return filtered
})

const maxEnrichmentScore = computed(() => {
  return Math.max(...results.value.map(r => r.enrichment_score), 10)
})

onMounted(() => {
  loadEnrichment()
})

async function loadEnrichment() {
  loading.value = true
  try {
    const endpoint = enrichmentType.value === 'hpo'
      ? '/enrichment/hpo'
      : '/enrichment/go'

    const params = enrichmentType.value === 'hpo'
      ? { fdr_threshold: fdrThreshold.value }
      : {
          gene_set: getGeneSetName(enrichmentType.value),
          fdr_threshold: fdrThreshold.value
        }

    const response = await api.post(endpoint, {
      gene_ids: props.geneIds,
      ...params
    })

    results.value = response.data.results
  } catch (error) {
    console.error('Failed to load enrichment:', error)
  } finally {
    loading.value = false
  }
}

function getGeneSetName(type) {
  const mapping = {
    'go_bp': 'GO_Biological_Process_2023',
    'go_mf': 'GO_Molecular_Function_2023',
    'go_cc': 'GO_Cellular_Component_2023',
    'kegg': 'KEGG_2021_Human'
  }
  return mapping[type]
}

function getFdrColor(fdr) {
  if (fdr < 0.001) return 'error'
  if (fdr < 0.01) return 'warning'
  return 'success'
}

function getGeneRatioColor(ratio) {
  if (ratio > 0.7) return 'error'
  if (ratio > 0.4) return 'warning'
  return 'primary'
}

function showDotplot() {
  // Emit event to parent to show dotplot dialog
  emit('show-dotplot', results.value)
}

function showBarplot() {
  emit('show-barplot', results.value)
}

function exportCSV() {
  const csv = convertToCSV(results.value)
  downloadCSV(csv, `enrichment_${enrichmentType.value}_cluster${props.clusterId}.csv`)
}
</script>

<style scoped>
.term-link {
  cursor: help;
  text-decoration: underline dotted;
}
</style>
```

### 3.2 Enrichment Dotplot (D3.js)

**Component**: `frontend/src/components/enrichment/EnrichmentDotplot.vue`

```vue
<template>
  <v-card>
    <v-card-title>Enrichment Dotplot</v-card-title>
    <v-card-text>
      <div ref="dotplotContainer" class="dotplot-container" />

      <!-- Legend -->
      <div class="mt-4">
        <v-row>
          <v-col cols="12" md="6">
            <div class="text-caption">
              <strong>Dot Size:</strong> Gene Ratio (genes in term / cluster size)
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="text-caption">
              <strong>Color:</strong> -log10(FDR)
              <span class="ml-2">
                <span class="color-swatch" style="background: #ffffcc" />
                Low
                <span class="color-swatch ml-2" style="background: #fc4e2a" />
                High
              </span>
            </div>
          </v-col>
        </v-row>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  enrichmentData: {
    type: Array,
    required: true
  },
  topN: {
    type: Number,
    default: 20
  }
})

const dotplotContainer = ref(null)

onMounted(() => {
  renderDotplot()
})

watch(() => props.enrichmentData, () => {
  renderDotplot()
})

function renderDotplot() {
  if (!dotplotContainer.value || !props.enrichmentData.length) return

  // Clear previous
  d3.select(dotplotContainer.value).selectAll('*').remove()

  // Prepare data (top N terms)
  const data = props.enrichmentData
    .slice(0, props.topN)
    .map(d => ({
      term: d.term_name,
      gene_ratio: d.gene_count / d.cluster_size,
      fdr: d.fdr,
      enrichment_score: d.enrichment_score,
      gene_count: d.gene_count
    }))

  // Dimensions
  const margin = { top: 20, right: 100, bottom: 60, left: 200 }
  const width = 600 - margin.left - margin.right
  const height = 40 * data.length - margin.top - margin.bottom

  // Create SVG
  const svg = d3.select(dotplotContainer.value)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  // Scales
  const x = d3.scaleLinear()
    .domain([0, 1])
    .range([0, width])

  const y = d3.scaleBand()
    .domain(data.map(d => d.term))
    .range([0, height])
    .padding(0.3)

  const size = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.gene_ratio)])
    .range([3, 20])

  const color = d3.scaleSequential()
    .domain([0, d3.max(data, d => d.enrichment_score)])
    .interpolator(d3.interpolateYlOrRd)

  // Axes
  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).ticks(5))
    .append('text')
    .attr('x', width / 2)
    .attr('y', 35)
    .attr('fill', 'black')
    .text('Gene Ratio')

  svg.append('g')
    .call(d3.axisLeft(y))
    .selectAll('text')
    .style('font-size', '11px')

  // Dots
  svg.selectAll('circle')
    .data(data)
    .enter()
    .append('circle')
    .attr('cx', d => x(d.gene_ratio))
    .attr('cy', d => y(d.term) + y.bandwidth() / 2)
    .attr('r', d => size(d.gene_ratio))
    .attr('fill', d => color(d.enrichment_score))
    .attr('stroke', '#333')
    .attr('stroke-width', 0.5)
    .style('opacity', 0.8)
    .on('mouseover', function(event, d) {
      d3.select(this)
        .style('opacity', 1)
        .attr('stroke-width', 2)

      // Show tooltip
      showTooltip(event, d)
    })
    .on('mouseout', function() {
      d3.select(this)
        .style('opacity', 0.8)
        .attr('stroke-width', 0.5)

      hideTooltip()
    })
}

function showTooltip(event, d) {
  // Implement D3 tooltip
  // (or use Vuetify v-tooltip with dynamic positioning)
}

function hideTooltip() {
  // Hide tooltip
}
</script>

<style scoped>
.dotplot-container {
  width: 100%;
  min-height: 400px;
}

.color-swatch {
  display: inline-block;
  width: 20px;
  height: 12px;
  border: 1px solid #ccc;
}
</style>
```

---

## 4. Complete Visualization Suite Summary

### What Users Will See:

| Visualization | Technology | Purpose | Priority |
|---------------|-----------|---------|----------|
| **1. Interactive Network Graph** | Cytoscape.js | Explore PPI connections, expand neighborhoods | **P1** |
| **2. Enrichment Results Table** | Vuetify DataTable | Browse significant terms, filter by FDR | **P1** |
| **3. Enrichment Barplot** | D3.js | Compare top terms by -log10(p-value) | **P1** |
| **4. Enrichment Dotplot** | D3.js | Multi-dimensional view (size + color) | **P2** |
| **5. Cluster Heatmap** | D3.js | Gene × Term matrix, hierarchical clustering | **P2** |
| **6. Cluster Dendrogram** | D3.js | Hierarchical tree of clusters | **P2** |
| **7. Network + Enrichment Split** | Cytoscape.js + Vue | Side-by-side network and enrichment | **P2** |
| **8. UpSet Plot** | D3.js (venn alternative) | Gene set overlaps across clusters | **P3** |

### Comparison to STRING-DB:

| Feature | STRING-DB | Our Implementation |
|---------|-----------|-------------------|
| Network visualization | ✅ Yes | ✅ Cytoscape.js |
| Enrichment analysis | ✅ GO, KEGG | ✅ HPO, GO, KEGG (via GSEApy) |
| Enrichment table | ✅ With FDR | ✅ Interactive DataTable |
| Clustering | ✅ MCL | ✅ Louvain/Leiden (better) |
| Interactive | ✅ Yes | ✅ Yes (more customizable) |
| Export | ✅ PNG, SVG, TSV | ✅ PNG, JSON, CSV |
| **Domain-specific** | ❌ Generic | ✅ **Kidney-specific HPO terms!** |

---

## 5. Revised Implementation Phases

### Phase 1 (4 weeks) - CRITICAL PATH:

**Network + HPO Enrichment MVP**:
1. ✅ NetworkX graph construction (from STRING data)
2. ✅ Louvain clustering
3. ✅ Cytoscape.js network visualization
4. ✅ **EnrichmentService with HPO support** (NEW)
5. ✅ **EnrichmentTable component** (NEW)
6. ✅ **Enrichment Barplot** (NEW)
7. ✅ Integration into GeneDetail page

**Dependencies**:
- `networkx` (backend)
- `scipy`, `statsmodels` (enrichment stats)
- `cytoscape`, `cytoscape-cose-bilkent` (frontend)
- Existing HPO data (`backend/app/core/hpo/`)

### Phase 2 (3 weeks) - ENHANCED ANALYSIS:

1. ✅ GSEApy integration (GO, KEGG)
2. ✅ Leiden clustering (igraph)
3. ✅ **Enrichment Dotplot** (D3.js)
4. ✅ **Cluster Heatmap** (D3.js)
5. ✅ Multi-cluster enrichment comparison
6. ✅ Centrality metrics

### Phase 3 (3 weeks) - ADVANCED FEATURES:

1. ✅ Cluster dendrogram visualization
2. ✅ UpSet plot for gene set overlaps
3. ✅ Reactome pathway enrichment
4. ✅ Network comparison tool
5. ✅ Export to Cytoscape desktop format

---

## 6. What I Missed in Original Assessment

### Critical Omissions:

1. **❌ Functional Enrichment Analysis** - The ENTIRE biological interpretation layer
2. **❌ HPO Enrichment** - We ALREADY have this data!
3. **❌ Enrichment Visualizations** - Dotplot, barplot, heatmap
4. **❌ GO/KEGG Integration** - Standard practice in bioinformatics
5. **❌ Multi-cluster comparison** - Essential for understanding disease modules

### What I Got Right:

1. ✅ NetworkX → igraph migration path
2. ✅ Louvain → Leiden progression
3. ✅ Cytoscape.js for network visualization
4. ✅ Reusing existing infrastructure (STRING data, caching, logging)
5. ✅ Non-blocking architecture (thread pools)

---

## 7. Updated Dependencies

### Backend (Python):

```bash
# Phase 1
uv add networkx
uv add scipy
uv add statsmodels

# Phase 2
uv add gseapy  # GO, KEGG, Reactome enrichment
uv add igraph  # Leiden clustering

# Phase 3 (optional)
uv add python-igraph  # If switching from NetworkX
```

### Frontend (npm):

```bash
# Phase 1
npm install cytoscape cytoscape-cose-bilkent
npm install d3  # Already installed, verify version

# Phase 2
npm install d3-hierarchy  # For dendrograms (part of d3)

# No additional deps for Phase 3
```

---

## 8. Conclusion

The original assessment focused too much on **graph topology** and not enough on **biological interpretation**. Network visualization without functional enrichment is like showing a map without labels - technically accurate but biologically meaningless.

**This addendum specifies**:
1. ✅ Exact enrichment algorithms (Fisher's exact, FDR correction)
2. ✅ Data sources (HPO - HAVE, GO/KEGG - ADD)
3. ✅ Visualization types (table, barplot, dotplot, heatmap)
4. ✅ Code examples (backend service, frontend components)
5. ✅ Phased rollout (HPO first, GO/KEGG second)

**Next Steps**:
1. Review this addendum with the original assessment
2. Prioritize Phase 1 (Network + HPO enrichment)
3. Allocate 4 weeks for Phase 1 MVP
4. Begin with `EnrichmentService` backend implementation

---

**Document Status**: Active Planning (Supplement to main assessment)
**Last Updated**: 2025-10-08
**Review Required**: YES - integrate with main assessment
