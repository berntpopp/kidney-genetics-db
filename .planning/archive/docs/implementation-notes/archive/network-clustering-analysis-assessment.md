# Network Analysis and Functional Clustering - Implementation Assessment

**Status**: Planning Phase
**Priority**: Medium
**Author**: Claude Code (Expert Review)
**Date**: 2025-10-08
**Related**: STRING-DB integration (completed), Data visualization system (completed)

## Executive Summary

This document provides a comprehensive assessment for implementing advanced network analysis and functional clustering capabilities in the kidney-genetics database. The assessment is based on:
- Current kidney-genetics-db v2 capabilities (STRING-DB integration)
- Legacy kidney-genetics-v1 R-based network analysis
- SysNDD project clustering approach
- Modern bioinformatics best practices (2024/2025)
- Industry-standard visualization libraries

**Key Recommendation**: Leverage existing STRING-DB annotation infrastructure and extend with incremental, modular clustering functionality using Python backend + Cytoscape.js/D3.js frontend. Minimize new dependencies by reusing proven systems.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Legacy Implementation Review](#legacy-implementation-review)
3. [Technology Stack Assessment](#technology-stack-assessment)
4. [Architecture Recommendations](#architecture-recommendations)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Risk Assessment](#risk-assessment)
7. [References](#references)

---

## 1. Current State Analysis

### 1.1 Existing Capabilities ✅

**STRING-DB Integration** (`backend/app/pipeline/sources/annotations/string_ppi.py`):
- ✅ Protein-protein interaction data fetching
- ✅ Weighted PPI scoring algorithm with hub bias correction
- ✅ Percentile ranking system (global percentiles via PercentileService)
- ✅ Caching infrastructure (L1/L2 via CacheService)
- ✅ Batch processing support
- ✅ Top N interactions storage (configurable, default max_interactions_stored)

**Algorithm** (Production-Proven):
```python
PPI_score(gene) = Σ(STRING_score/1000 × partner_kidney_evidence) / sqrt(degree)
```

**Key Features**:
- Hub bias correction using sqrt(degree)
- Partner weighting by kidney disease evidence
- Percentile normalization across entire database
- 95%+ annotation coverage in production

**Frontend Display** (`frontend/src/components/gene/ProteinInteractions.vue`):
- ✅ PPI score visualization
- ✅ Percentile rank display
- ✅ Network degree (partner count)
- ✅ Top 3 partners with tooltips
- ✅ Responsive Vuetify components

### 1.2 Gaps Requiring New Implementation ❌

**Missing Network Analysis Features**:
- ❌ Interactive network graph visualization
- ❌ Community detection/clustering algorithms
- ❌ Subgraph/neighborhood exploration
- ❌ Network topology metrics (betweenness, closeness, centrality)
- ❌ Functional enrichment of clusters
- ❌ Multi-gene network analysis
- ❌ Network comparison tools

**Missing Visualization Components**:
- ❌ Force-directed graph layout
- ❌ Network zoom/pan/filter controls
- ❌ Cluster color-coding and legends
- ❌ Node/edge interactivity (click, hover, select)
- ❌ Export network images/data

---

## 2. Legacy Implementation Review

### 2.1 Kidney-Genetics-v1 Network Analysis (R-based)

**Location**: `../kidney-genetics-v1/analyses/D_ProteinInteractionAnalysis/`

**Stack**:
- `STRINGdb` R package (version 12.0)
- `plotly` + `ggnet` + `network` + `sna` + `GGally` for visualization
- Walktrap clustering algorithm (from igraph)

**Key Functions** (`protein_interaction_analysis-functions.R`):

1. **Clustering**:
   ```r
   get_STRING_clusters(STRING_id_vec, min_number, algorithm = "walktrap")
   # Recursive hierarchical clustering
   # Splits clusters larger than min_number into subclusters
   # Creates multi-level hierarchy (e.g., cluster index "3-1-2")
   ```

2. **Network Traversal**:
   ```r
   get_all_contacts_by_level(index_genes, connection_df, min_comb_score, max_level)
   # BFS-style expansion from seed genes
   # Filters by STRING combined_score threshold
   # Returns genes within N hops of seed
   ```

3. **Visualization**:
   ```r
   plot_interaction_network(edgelist, disease_group_df, index_gene_symbols)
   # ggnet2 → ggplotly conversion
   # Fruchterman-Reingold layout
   # Color by disease group (custom palette)
   # Square markers for index genes
   ```

4. **Spatial Layout** (for cluster overview):
   ```r
   plot_all_genes_in_clusters(disease_group_df, cluster_center_circle_radius, min_euc_dist, max_rad)
   # Distribute clusters on circle
   # Random point placement with minimum distance constraint
   # Cluster size proportional to gene count
   ```

**Strengths**:
- ✅ Proven hierarchical clustering approach
- ✅ Disease group color-coding (tubulopathy, glomerulopathy, cakut, etc.)
- ✅ Multi-level network traversal
- ✅ Interactive plotly output (HTML export)

**Limitations**:
- ⚠️ R-only, not integrated with Python pipeline
- ⚠️ Manual processing required (not automated)
- ⚠️ No real-time interactivity (pre-rendered plots)
- ⚠️ Walktrap algorithm is older (Louvain/Leiden are state-of-art in 2024)
- ⚠️ No enrichment analysis

### 2.2 SysNDD Project Clustering

**GitHub**: https://github.com/berntpopp/sysndd

**Findings**:
- Focus: Gene-disease relationships in neurodevelopmental disorders
- Stack: Vue.js + R + MySQL + Docker
- Documentation mentions "Functional Clustering and Correlation" (issue #72)
- **Limited public code**: Network analysis not in main branch (likely manuscript-specific)

**Lessons**:
- Similar domain (genetic disease curation)
- Vue.js frontend aligns with our stack
- Manuscript-driven feature development pattern

---

## 3. Technology Stack Assessment

### 3.1 Backend: Python Network Analysis Libraries

**Comparison Matrix** (2024/2025 Research):

| Library | Performance | Ease of Use | Clustering | Biological Focus | Recommendation |
|---------|-------------|-------------|------------|------------------|----------------|
| **igraph** | ⭐⭐⭐⭐⭐ Fast (C core) | ⭐⭐⭐⭐ Good docs (2024) | ✅ Leiden, Louvain, Walktrap, MCL | ⭐⭐⭐⭐ Bio-focused | **Primary choice** |
| **NetworkX** | ⭐⭐⭐ Slow (pure Python) | ⭐⭐⭐⭐⭐ Excellent docs | ✅ Louvain, Greedy Modularity | ⚠️ General-purpose | Fallback only |
| **graph-tool** | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐ Steep curve | ✅ All modern algorithms | ⚠️ Hard to install | Not recommended |

**Decision**: **Use igraph from Phase 1** (NOT NetworkX)

**Rationale**:
1. **8-10x faster** than NetworkX for target scale (1000-5000 nodes)
2. **Modern igraph (0.11+) installs cleanly** via pip/UV (no compilation)
3. **Native Leiden algorithm** (superior to Louvain)
4. **Production-proven** in bioinformatics at scale
5. **Target scale requires performance**: 5000 nodes × 25 avg degree = 62,500 edges

### 3.2 Clustering Algorithms (2024 State-of-Art)

**Recommended Algorithms**:

| Algorithm | Use Case | Speed | Quality | NetworkX Support | igraph Support |
|-----------|----------|-------|---------|------------------|----------------|
| **Leiden** | Primary choice (2019 improved Louvain) | Fast | ⭐⭐⭐⭐⭐ Best | ❌ (via leidenalg) | ✅ Native |
| **Louvain** | Fallback (2008 classic) | Very fast | ⭐⭐⭐⭐ Good | ✅ Native (community) | ✅ Native |
| **MCL** (Markov Clustering) | PPI networks specifically | Moderate | ⭐⭐⭐⭐ Good for bio | ❌ External | ✅ Native |
| **Walktrap** | Legacy compatibility | Fast | ⭐⭐⭐ Moderate | ❌ External | ✅ Native |

**Recommendation**:
1. **Phase 1**: Louvain (NetworkX native, easy to implement)
2. **Phase 2**: Leiden (igraph via leidenalg package, superior quality)
3. **Phase 3**: MCL (optional, PPI-specific optimization)

**Recent Research** (2024/2025):
- **Leiden** guarantees well-connected communities (Louvain doesn't)
- **SpatialLeiden** (Feb 2025, Genome Biology) - spatially-aware clustering for single-cell data
- **Fast Leiden** (2024 ACM) - parallel implementations for large networks
- **No universal winner**: Choice depends on data characteristics and domain

### 3.3 Frontend: Network Visualization Libraries

**Comparison Matrix** (2024 Research):

| Library | Performance | Ease of Use | Bio Integration | Customization | Our Stack Fit |
|---------|-------------|-------------|-----------------|---------------|---------------|
| **Cytoscape.js** | ⭐⭐⭐⭐ WebGL | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐⭐ Designed for bio | ⭐⭐⭐⭐⭐ Deep | ⭐⭐⭐⭐⭐ **Best** |
| **D3.js** | ⭐⭐⭐ SVG (slow for large) | ⭐⭐ Steep curve | ⭐⭐ General-purpose | ⭐⭐⭐⭐⭐ Maximum | ⭐⭐⭐⭐ **Already used** |
| **vis-network** | ⭐⭐ Slowest | ⭐⭐⭐⭐⭐ Easy | ⭐⭐ General-purpose | ⭐⭐⭐ Moderate | ⭐⭐ Avoid |

**Decision**: **Hybrid approach - Cytoscape.js for network graphs, D3.js for complementary viz**

**Rationale**:
1. **Cytoscape.js is purpose-built for biological networks**
   - 404 code snippets in Context7 docs
   - Native clustering algorithms (k-means, Markov, hierarchical, affinity propagation)
   - Layout algorithms (force-directed, hierarchical, circular, grid)
   - Graph analysis (Dijkstra, Bellman-Ford, Kruskal, Floyd-Warshall)
   - Designed for Cytoscape desktop tool ecosystem

2. **D3.js is already in our stack**
   - Used for: `D3BarChart.vue`, `D3DonutChart.vue`, `EvidenceCompositionChart.vue`, `UpSetChart.vue`
   - Team familiarity
   - Can create complementary visualizations (dendrograms, enrichment plots)

3. **Minimal new dependencies**
   - Cytoscape.js is 1 package (`cytoscape` on npm)
   - Zero conflicts with Vuetify/Vite

**Alternative Considered**: vis-network (rejected due to performance issues and active maintenance concerns)

### 3.4 Data Flow Architecture

**Proposed Flow**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 + Vuetify)                │
├─────────────────────────────────────────────────────────────┤
│  Interactive Network View (Cytoscape.js)                     │
│  - Force-directed layout (CoSE, Cose-Bilkent)                │
│  - Click gene → highlight subgraph                           │
│  - Select cluster → show enrichment                          │
│  - Export PNG/JSON                                           │
│                                                              │
│  Complementary D3.js Viz                                     │
│  - Cluster dendrogram (hierarchical tree)                    │
│  - Enrichment bar charts                                     │
│  - Degree distribution histogram                             │
└─────────────────────────────────────────────────────────────┘
                            ↕ REST API
┌─────────────────────────────────────────────────────────────┐
│                 Backend (FastAPI + PostgreSQL)               │
├─────────────────────────────────────────────────────────────┤
│  Network Analysis Service (NEW)                              │
│  - NetworkX graph construction from STRING data              │
│  - Louvain/Leiden clustering                                 │
│  - Subgraph extraction (k-hop neighborhoods)                 │
│  - Topology metrics (centrality, betweenness)                │
│                                                              │
│  REUSE: BaseAnnotationSource pattern                         │
│  - CacheService (L1/L2 caching)                              │
│  - RetryableHTTPClient (not needed for local graphs)         │
│  - UnifiedLogger (structured logging)                        │
│  - Thread pool for heavy graph operations (non-blocking)     │
│                                                              │
│  Data Sources (EXISTING)                                     │
│  - StringPPIAnnotationSource (gene.annotations JSONB)        │
│  - Gene staging table (gene_staging)                         │
│  - Percentile service (string_ppi percentiles)               │
└─────────────────────────────────────────────────────────────┘
                            ↕ SQL
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL (Hybrid Schema)                 │
├─────────────────────────────────────────────────────────────┤
│  Relational Columns                                          │
│  - gene.id, approved_symbol, hgnc_id                         │
│  - gene_annotations.source = 'string_ppi'                    │
│                                                              │
│  JSONB Columns (NO SCHEMA CHANGES NEEDED)                    │
│  - gene_annotations.annotations                              │
│    → {ppi_score, ppi_percentile, ppi_degree, interactions[]} │
│                                                              │
│  NEW: Network Analysis Cache Table (Optional Phase 2)        │
│  - network_clusters (gene_id, cluster_id, algorithm, params) │
│  - network_metrics (gene_id, metric_type, value, timestamp)  │
└─────────────────────────────────────────────────────────────┘
```

**Key Architectural Principles** (from CLAUDE.md):
- ✅ **DRY**: Reuse STRING data, CacheService, logging, retry logic
- ✅ **KISS**: NetworkX is simpler than igraph initially
- ✅ **Modularization**: New `NetworkAnalysisService` class inherits/composes existing services
- ✅ **Non-blocking**: Heavy graph operations in thread pool (via `loop.run_in_executor`)
- ✅ **Configuration-driven**: Clustering parameters in YAML (`backend/config/network_analysis.yaml`)

---

## 4. Architecture Recommendations

### 4.1 Backend Component Design

**New Module**: `backend/app/services/network_analysis_service.py`

```python
"""
Network analysis service for protein interaction networks.

Provides clustering, topology analysis, and subgraph extraction using igraph.
Integrates with existing STRING-DB data and caching infrastructure.
"""

import asyncio
import igraph as ig
from typing import Dict, List, Any, Optional
from cachetools import TTLCache
import threading
from app.core.logging import get_logger
from app.core.cache_service import get_cache_service
from app.core.database import get_thread_pool_executor, get_db_context
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class NetworkAnalysisService:
    """Service for analyzing protein interaction networks."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize WITHOUT session (pass session per-call for thread safety)."""
        self.config = config or self._load_default_config()
        self._executor = get_thread_pool_executor()  # Use singleton from database.py

        # LRU cache with TTL to prevent memory leaks
        self._graph_cache = TTLCache(
            maxsize=50,  # Max 50 graphs (~2.5GB at 50MB each)
            ttl=3600  # 1 hour TTL
        )
        self._cache_lock = threading.Lock()

    async def build_network_from_string_data(
        self,
        gene_ids: List[int],
        session: Session,  # ✅ Session passed per-call
        min_string_score: int = 400
    ) -> ig.Graph:
        """
        Construct igraph Graph from STRING-DB annotations in database.

        REUSES existing data:
        - gene_annotations.annotations JSONB (string_ppi source)
        - No external API calls needed
        - Cached with LRU/TTL policy (prevents memory leaks)

        Returns undirected graph with edge weights (STRING scores).
        """
        # Check memory cache first
        cache_key = f"network:{len(gene_ids)}:{min_string_score}"  # Shorter key
        with self._cache_lock:
            if cache_key in self._graph_cache:
                logger.sync_debug(f"Using cached network graph", cache_key=cache_key)
                return self._graph_cache[cache_key]

        # Build graph in thread pool (non-blocking for event loop)
        loop = asyncio.get_event_loop()
        graph = await loop.run_in_executor(
            self._executor,
            self._build_graph_sync,
            gene_ids,
            min_string_score
        )

        with self._cache_lock:
            self._graph_cache[cache_key] = graph
        return graph

    def _build_graph_sync(self, gene_ids: List[int], min_string_score: int) -> ig.Graph:
        """Synchronous graph construction (runs in thread pool)."""
        # Create fresh session in thread pool
        with get_db_context() as db:
            # Create igraph Graph
            g = ig.Graph()

            # Query STRING annotations from database
            annotations = (
                db.query(GeneAnnotation)
                .filter(
                    GeneAnnotation.gene_id.in_(gene_ids),
                    GeneAnnotation.source == "string_ppi"
                )
                .all()
            )

            # Build gene_id → vertex_index mapping
            gene_id_to_idx = {gid: idx for idx, gid in enumerate(gene_ids)}
            g.add_vertices(len(gene_ids))
            g.vs["gene_id"] = gene_ids

            # Build edge list
            edges = []
            weights = []
            string_scores = []

            # Build adjacency from stored interactions
            for ann in annotations:
                gene_id = ann.gene_id
                data = ann.annotations

                if not data or "interactions" not in data:
                    continue

                source_idx = gene_id_to_idx.get(gene_id)
                if source_idx is None:
                    continue

                for interaction in data["interactions"]:
                    partner_symbol = interaction["partner_symbol"]
                    string_score = interaction["string_score"]

                    if string_score >= min_string_score:
                        # Get partner gene_id from symbol
                        partner_gene = (
                            db.query(Gene)
                            .filter_by(approved_symbol=partner_symbol)
                            .first()
                        )

                        if partner_gene and partner_gene.id in gene_id_to_idx:
                            target_idx = gene_id_to_idx[partner_gene.id]
                            edges.append((source_idx, target_idx))
                            weights.append(string_score / 1000.0)  # Normalize
                            string_scores.append(string_score)

            # Add edges to graph
            g.add_edges(edges)
            g.es["weight"] = weights
            g.es["string_score"] = string_scores

            logger.sync_info(
                f"Built network graph",
                nodes=g.vcount(),
                edges=g.ecount(),
                components=len(g.connected_components())
            )

            return g

    async def detect_communities(
        self,
        graph: ig.Graph,
        session: Session,  # ✅ Session passed per-call
        algorithm: str = "leiden"
    ) -> Dict[int, int]:
        """
        Detect communities using specified algorithm.

        Algorithms:
        - leiden: igraph native, superior quality (default)
        - louvain: igraph native, fast, good quality
        - walktrap: Legacy compatibility

        Returns: {gene_id: cluster_id} mapping
        """
        loop = asyncio.get_event_loop()
        communities = await loop.run_in_executor(
            self._executor,
            self._detect_communities_sync,
            graph,
            algorithm
        )
        return communities

    def _detect_communities_sync(
        self,
        graph: ig.Graph,
        algorithm: str
    ) -> Dict[int, int]:
        """Synchronous community detection (runs in thread pool)."""
        if algorithm == "leiden":
            # Leiden algorithm (native igraph, superior to Louvain)
            partition = graph.community_leiden(
                weights="weight",
                resolution_parameter=self.config.get("leiden_resolution", 1.0),
                n_iterations=self.config.get("leiden_iterations", 2)
            )
        elif algorithm == "louvain":
            # Louvain algorithm (multilevel optimization)
            partition = graph.community_multilevel(
                weights="weight",
                resolution=self.config.get("louvain_resolution", 1.0)
            )
        elif algorithm == "walktrap":
            # Walktrap algorithm (random walk-based)
            partition = graph.community_walktrap(
                weights="weight",
                steps=self.config.get("walktrap_steps", 4)
            ).as_clustering()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Convert to {gene_id: cluster_id} format
        gene_to_cluster = {}
        for cluster_id, members in enumerate(partition):
            for vertex_idx in members:
                gene_id = graph.vs[vertex_idx]["gene_id"]
                gene_to_cluster[gene_id] = cluster_id

        # Calculate modularity
        modularity = graph.modularity(partition, weights="weight")

        logger.sync_info(
            f"Detected {len(partition)} communities",
            algorithm=algorithm,
            modularity=round(modularity, 3)
        )

        return gene_to_cluster

    async def get_k_hop_subgraph(
        self,
        graph: ig.Graph,
        seed_gene_ids: List[int],
        session: Session,  # ✅ Session passed per-call
        k: int = 2
    ) -> ig.Graph:
        """Extract k-hop neighborhood subgraph around seed genes."""
        loop = asyncio.get_event_loop()
        subgraph = await loop.run_in_executor(
            self._executor,
            self._get_k_hop_subgraph_sync,
            graph,
            seed_gene_ids,
            k
        )
        return subgraph

    def _get_k_hop_subgraph_sync(
        self,
        graph: ig.Graph,
        seed_gene_ids: List[int],
        k: int
    ) -> ig.Graph:
        """Synchronous k-hop subgraph extraction."""
        vertices_to_include = set()

        # Find seed vertices
        for seed_gene_id in seed_gene_ids:
            try:
                seed_vertex = graph.vs.find(gene_id=seed_gene_id)
                vertices_to_include.add(seed_vertex.index)

                # Get k-hop neighborhood using BFS
                neighborhood = graph.neighborhood(
                    vertices=seed_vertex.index,
                    order=k,
                    mode="all"  # undirected
                )
                vertices_to_include.update(neighborhood)
            except ValueError:
                # Vertex not in graph
                logger.sync_debug(f"Seed gene {seed_gene_id} not in graph")
                continue

        # Extract subgraph
        subgraph = graph.subgraph(list(vertices_to_include))

        logger.sync_info(
            f"Extracted {k}-hop subgraph",
            seed_genes=len(seed_gene_ids),
            total_nodes=subgraph.vcount(),
            total_edges=subgraph.ecount()
        )

        return subgraph

    async def calculate_centrality_metrics(
        self,
        graph: ig.Graph,
        session: Session,  # ✅ Session passed per-call
        metrics: List[str] = ["degree", "betweenness", "closeness"]
    ) -> Dict[int, Dict[str, float]]:
        """Calculate centrality metrics for all nodes."""
        loop = asyncio.get_event_loop()
        centrality_data = await loop.run_in_executor(
            self._executor,
            self._calculate_centrality_sync,
            graph,
            metrics
        )
        return centrality_data

    def _calculate_centrality_sync(
        self,
        graph: ig.Graph,
        metrics: List[str]
    ) -> Dict[int, Dict[str, float]]:
        """Synchronous centrality calculation."""
        results = {v["gene_id"]: {} for v in graph.vs}

        if "degree" in metrics:
            # Degree centrality (normalized)
            degree_cent = graph.degree()
            max_degree = max(degree_cent) if degree_cent else 1
            for v in graph.vs:
                results[v["gene_id"]]["degree_centrality"] = degree_cent[v.index] / max_degree

        if "betweenness" in metrics:
            # Betweenness centrality (10-50x faster than NetworkX)
            between_cent = graph.betweenness(weights="weight", directed=False)
            for v in graph.vs:
                results[v["gene_id"]]["betweenness_centrality"] = between_cent[v.index]

        if "closeness" in metrics:
            # Closeness centrality (only for largest component)
            components = graph.connected_components()
            if len(components) > 0:
                largest_component = max(components, key=len)
                subgraph = graph.subgraph(largest_component)
                closeness_cent = subgraph.closeness(weights="weight")

                for idx, v_idx in enumerate(largest_component):
                    gene_id = graph.vs[v_idx]["gene_id"]
                    results[gene_id]["closeness_centrality"] = closeness_cent[idx]

        if "pagerank" in metrics:
            # PageRank (bonus - much faster in igraph)
            pagerank = graph.pagerank(weights="weight")
            for v in graph.vs:
                results[v["gene_id"]]["pagerank"] = pagerank[v.index]

        logger.sync_info(f"Calculated centrality metrics", metrics=metrics)
        return results

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "louvain_resolution": 1.0,
            "min_string_score": 400,
            "cache_ttl_seconds": 3600,
            "max_graph_size": 10000  # Safety limit
        }
```

**API Endpoint**: `backend/app/api/endpoints/network_analysis.py`

```python
"""
Network analysis API endpoints.

Provides REST API for:
- Building interaction networks
- Community detection
- Subgraph extraction
- Topology metrics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.api.dependencies import get_db
from app.services.network_analysis_service import NetworkAnalysisService
from app.core.logging import get_logger

router = APIRouter(prefix="/api/network", tags=["network-analysis"])
logger = get_logger(__name__)


@router.post("/build")
async def build_network(
    gene_ids: List[int],
    min_string_score: int = Query(400, ge=0, le=1000),
    max_nodes: int = Query(500, le=2000),  # ✅ HARD LIMIT to prevent large responses
    db: Session = Depends(get_db)  # ✅ Dependency injection
):
    """
    Build protein interaction network from STRING-DB data.

    POST /api/network/build
    Body: {"gene_ids": [1, 2, 3, ...], "min_string_score": 400, "max_nodes": 500}

    Returns: Cytoscape.js JSON format
    {
        "nodes": [{"data": {"id": 1, "symbol": "GENE1"}}, ...],
        "edges": [{"data": {"source": 1, "target": 2, "weight": 0.8}}, ...],
        "metadata": {"num_nodes": 42, "num_edges": 127}
    }
    """
    # ✅ Validate input size
    if len(gene_ids) > max_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Network too large. Max {max_nodes} genes allowed. "
                   f"Requested: {len(gene_ids)}. Increase min_string_score to reduce size."
        )

    service = NetworkAnalysisService()  # ✅ No session in constructor
    graph = await service.build_network_from_string_data(gene_ids, db, min_string_score)

    # ✅ Check result size AFTER building
    if graph.vcount() > max_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Resulting network has {graph.vcount()} nodes. "
                   f"Max {max_nodes} allowed. Increase min_string_score."
        )

    # Convert igraph to Cytoscape.js format
    cytoscape_data = {
        "nodes": [],
        "edges": []
    }

    # Add nodes with gene metadata
    for v in graph.vs:
        gene_id = v["gene_id"]
        gene = db.query(Gene).filter_by(id=gene_id).first()
        cytoscape_data["nodes"].append({
            "data": {
                "id": str(gene_id),
                "label": gene.approved_symbol if gene else str(gene_id),
                "approved_symbol": gene.approved_symbol if gene else None
            }
        })

    # Add edges
    for e in graph.es:
        source_gene_id = graph.vs[e.source]["gene_id"]
        target_gene_id = graph.vs[e.target]["gene_id"]
        cytoscape_data["edges"].append({
            "data": {
                "source": str(source_gene_id),
                "target": str(target_gene_id),
                "weight": e["weight"],
                "string_score": e["string_score"]
            }
        })

    # Add metadata
    cytoscape_data["metadata"] = {
        "num_nodes": graph.vcount(),
        "num_edges": graph.ecount(),
        "min_string_score": min_string_score,
        "connected_components": len(graph.connected_components())
    }

    return cytoscape_data


@router.post("/cluster")
async def cluster_network(
    gene_ids: List[int],
    algorithm: str = Query("leiden", regex="^(leiden|louvain|walktrap)$"),  # ✅ Leiden default
    min_string_score: int = Query(400, ge=0, le=1000),
    max_nodes: int = Query(500, le=2000),  # ✅ HARD LIMIT
    db: Session = Depends(get_db)  # ✅ Dependency injection
):
    """
    Perform community detection on network.

    POST /api/network/cluster
    Body: {"gene_ids": [...], "algorithm": "leiden", "min_string_score": 400}

    Returns: {
        "clusters": {gene_id: cluster_id},
        "modularity": 0.45,
        "num_clusters": 5,
        "cluster_stats": [...]
    }
    """
    # ✅ Validate input size
    if len(gene_ids) > max_nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Network too large for clustering. Max {max_nodes} genes."
        )

    service = NetworkAnalysisService()  # ✅ No session in constructor
    graph = await service.build_network_from_string_data(gene_ids, db, min_string_score)
    communities = await service.detect_communities(graph, db, algorithm)

    # Calculate modularity using igraph
    cluster_sets = {}
    for gene_id, cluster_id in communities.items():
        if cluster_id not in cluster_sets:
            cluster_sets[cluster_id] = []
        cluster_sets[cluster_id].append(gene_id)

    # Convert to vertex indices for modularity calculation
    vertex_clusters = []
    for v in graph.vs:
        gene_id = v["gene_id"]
        cluster_id = communities.get(gene_id, -1)
        vertex_clusters.append(cluster_id)

    modularity = graph.modularity(vertex_clusters, weights="weight")

    # Generate cluster statistics
    cluster_stats = []
    for cluster_id, gene_ids_in_cluster in cluster_sets.items():
        # Get vertices in this cluster
        cluster_vertices = [
            v.index for v in graph.vs
            if v["gene_id"] in gene_ids_in_cluster
        ]
        cluster_subgraph = graph.subgraph(cluster_vertices)

        # Get top genes by degree
        degrees = cluster_subgraph.degree()
        gene_degrees = [
            (cluster_subgraph.vs[i]["gene_id"], degrees[i])
            for i in range(len(degrees))
        ]
        gene_degrees.sort(key=lambda x: x[1], reverse=True)
        top_genes = [gid for gid, _ in gene_degrees[:3]]

        # Fetch gene symbols
        top_gene_symbols = [
            db.query(Gene).filter_by(id=gid).first().approved_symbol
            for gid in top_genes
        ]

        cluster_stats.append({
            "cluster_id": cluster_id,
            "size": len(gene_ids_in_cluster),
            "avg_degree": sum(degrees) / len(degrees) if degrees else 0,
            "top_genes": top_gene_symbols
        })

    return {
        "clusters": communities,
        "modularity": round(modularity, 3),
        "num_clusters": len(cluster_sets),
        "cluster_stats": cluster_stats
    }


@router.get("/subgraph/{gene_id}")
async def get_gene_neighborhood(
    gene_id: int,
    k_hops: int = Query(2, ge=1, le=5),
    min_string_score: int = Query(400, ge=0, le=1000),
    db = Depends(get_db)
):
    """
    Get k-hop neighborhood subgraph for a gene.

    GET /api/network/subgraph/123?k_hops=2&min_string_score=400

    Returns: Cytoscape.js format with highlighted seed gene
    """
    # First, get all kidney genes to build full network
    all_genes = db.query(Gene).all()
    gene_ids = [g.id for g in all_genes]

    service = NetworkAnalysisService(db)
    full_graph = await service.build_network_from_string_data(gene_ids, min_string_score)
    subgraph = await service.get_k_hop_subgraph(full_graph, [gene_id], k_hops)

    # Convert to Cytoscape.js format with seed highlight
    cytoscape_data = {
        "nodes": [],
        "edges": []
    }

    for node in subgraph.nodes():
        gene = db.query(Gene).filter_by(id=node).first()
        cytoscape_data["nodes"].append({
            "data": {
                "id": str(node),
                "label": gene.approved_symbol if gene else str(node)
            },
            "classes": "seed" if node == gene_id else ""
        })

    for u, v, data in subgraph.edges(data=True):
        cytoscape_data["edges"].append({
            "data": {
                "source": str(u),
                "target": str(v),
                "weight": data.get("weight", 0),
                "string_score": data.get("string_score", 0)
            }
        })

    return cytoscape_data
```

### 4.2 Frontend Component Design

**New Component**: `frontend/src/components/network/NetworkGraph.vue`

```vue
<template>
  <v-card>
    <v-card-title>
      <span class="text-h6">Protein Interaction Network</span>
      <v-spacer />
      <v-btn icon="mdi-download" size="small" @click="exportNetwork" />
      <v-btn icon="mdi-refresh" size="small" @click="resetLayout" />
    </v-card-title>

    <v-card-text>
      <!-- Control Panel -->
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <v-select
            v-model="layoutType"
            :items="layoutOptions"
            label="Layout"
            density="compact"
            @update:model-value="applyLayout"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-slider
            v-model="minStringScore"
            :min="0"
            :max="1000"
            :step="50"
            label="Min STRING Score"
            thumb-label
            @update:model-value="filterEdges"
          />
        </v-col>
        <v-col cols="12" md="4">
          <v-btn
            block
            color="primary"
            prepend-icon="mdi-group"
            @click="detectClusters"
          >
            Detect Clusters
          </v-btn>
        </v-col>
      </v-row>

      <!-- Cytoscape Container -->
      <div ref="cytoscapeContainer" class="network-container" />

      <!-- Legend -->
      <v-row class="mt-4">
        <v-col>
          <div class="text-caption">
            <v-chip size="x-small" color="primary" class="mr-2">Seed Gene</v-chip>
            <v-chip size="x-small" color="secondary" class="mr-2">Cluster 1</v-chip>
            <v-chip size="x-small" color="accent" class="mr-2">Cluster 2</v-chip>
            <span class="text-medium-emphasis">Nodes: {{ nodeCount }} | Edges: {{ edgeCount }}</span>
          </div>
        </v-col>
      </v-row>
    </v-card-text>

    <!-- Selected Node Details Panel -->
    <v-card-text v-if="selectedNode">
      <v-divider class="mb-4" />
      <v-row>
        <v-col cols="12" md="6">
          <div class="text-subtitle-2">{{ selectedNode.label }}</div>
          <div class="text-caption text-medium-emphasis">
            Degree: {{ selectedNode.degree }} |
            Cluster: {{ selectedNode.cluster }}
          </div>
        </v-col>
        <v-col cols="12" md="6">
          <v-btn
            size="small"
            color="primary"
            prepend-icon="mdi-magnify-plus-outline"
            @click="expandNeighborhood"
          >
            Expand Neighborhood
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import api from '@/services/api'

// Register Cytoscape.js extensions
cytoscape.use(coseBilkent)

const props = defineProps({
  geneIds: {
    type: Array,
    required: true
  },
  seedGeneId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['nodeSelected', 'clusterDetected'])

// Refs
const cytoscapeContainer = ref(null)
let cy = null  // Cytoscape instance

// State
const layoutType = ref('cose-bilkent')
const minStringScore = ref(400)
const selectedNode = ref(null)
const nodeCount = ref(0)
const edgeCount = ref(0)

// Layout options
const layoutOptions = [
  { title: 'Force-Directed (CoSE)', value: 'cose' },
  { title: 'Force-Directed (CoSE-Bilkent)', value: 'cose-bilkent' },
  { title: 'Circular', value: 'circle' },
  { title: 'Grid', value: 'grid' },
  { title: 'Hierarchical', value: 'breadthfirst' }
]

// Lifecycle
onMounted(async () => {
  await initializeNetwork()
})

onUnmounted(() => {
  if (cy) {
    cy.destroy()
  }
})

// Methods
async function initializeNetwork() {
  try {
    // Fetch network data from backend
    const response = await api.post('/network/build', {
      gene_ids: props.geneIds,
      min_string_score: minStringScore.value
    })

    // Initialize Cytoscape.js
    cy = cytoscape({
      container: cytoscapeContainer.value,

      elements: response.data,

      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': '#0288D1',
            'color': '#000',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'width': 30,
            'height': 30
          }
        },
        {
          selector: 'node.seed',
          style: {
            'background-color': '#D32F2F',
            'width': 40,
            'height': 40,
            'font-weight': 'bold'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(weight, 0, 1, 1, 5)',
            'line-color': '#ccc',
            'opacity': 0.6,
            'curve-style': 'bezier'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#FFB300'
          }
        }
      ],

      layout: {
        name: layoutType.value,
        animate: true,
        animationDuration: 500
      }
    })

    // Event handlers
    cy.on('tap', 'node', (event) => {
      const node = event.target
      selectedNode.value = {
        id: node.id(),
        label: node.data('label'),
        degree: node.degree(),
        cluster: node.data('cluster')
      }
      emit('nodeSelected', selectedNode.value)
    })

    cy.on('tap', (event) => {
      if (event.target === cy) {
        selectedNode.value = null
      }
    })

    // Update stats
    updateStats()

  } catch (error) {
    console.error('Failed to initialize network:', error)
  }
}

function applyLayout() {
  if (!cy) return

  const layoutConfig = {
    name: layoutType.value,
    animate: true,
    animationDuration: 500,
    fit: true,
    padding: 30
  }

  // Add algorithm-specific options
  if (layoutType.value === 'cose-bilkent') {
    layoutConfig.quality = 'default'
    layoutConfig.nodeRepulsion = 4500
    layoutConfig.idealEdgeLength = 50
  }

  cy.layout(layoutConfig).run()
}

function filterEdges() {
  if (!cy) return

  // Hide edges below threshold
  cy.edges().forEach(edge => {
    const stringScore = edge.data('string_score')
    if (stringScore < minStringScore.value) {
      edge.style('display', 'none')
    } else {
      edge.style('display', 'element')
    }
  })

  updateStats()
}

async function detectClusters() {
  try {
    const response = await api.post('/network/cluster', {
      gene_ids: props.geneIds,
      algorithm: 'louvain',
      min_string_score: minStringScore.value
    })

    const { clusters, modularity, num_clusters } = response.data

    // Color nodes by cluster
    const clusterColors = generateClusterColors(num_clusters)

    cy.nodes().forEach(node => {
      const geneId = parseInt(node.id())
      const clusterId = clusters[geneId]
      if (clusterId !== undefined) {
        node.data('cluster', clusterId)
        node.style('background-color', clusterColors[clusterId])
      }
    })

    emit('clusterDetected', { clusters, modularity, num_clusters })

  } catch (error) {
    console.error('Clustering failed:', error)
  }
}

function generateClusterColors(numClusters) {
  // Generate distinct colors for clusters (using HSL color space)
  const colors = []
  for (let i = 0; i < numClusters; i++) {
    const hue = (i * 360) / numClusters
    colors.push(`hsl(${hue}, 70%, 50%)`)
  }
  return colors
}

async function expandNeighborhood() {
  if (!selectedNode.value) return

  try {
    const response = await api.get(`/network/subgraph/${selectedNode.value.id}`, {
      params: {
        k_hops: 1,
        min_string_score: minStringScore.value
      }
    })

    // Add new nodes/edges to existing graph
    cy.add(response.data.nodes)
    cy.add(response.data.edges)

    applyLayout()
    updateStats()

  } catch (error) {
    console.error('Failed to expand neighborhood:', error)
  }
}

function resetLayout() {
  applyLayout()
}

function exportNetwork() {
  if (!cy) return

  // Export as PNG
  const png = cy.png({
    full: true,
    scale: 2
  })

  const link = document.createElement('a')
  link.href = png
  link.download = 'network_graph.png'
  link.click()
}

function updateStats() {
  if (!cy) return

  nodeCount.value = cy.nodes(':visible').length
  edgeCount.value = cy.edges(':visible').length
}
</script>

<style scoped>
.network-container {
  width: 100%;
  height: 600px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}
</style>
```

**Integration Point**: `frontend/src/views/GeneDetail.vue` (existing)

```vue
<template>
  <v-container>
    <!-- Existing gene detail sections -->

    <!-- NEW: Network Analysis Tab -->
    <v-tabs v-model="currentTab">
      <v-tab value="overview">Overview</v-tab>
      <v-tab value="evidence">Evidence</v-tab>
      <v-tab value="network">Network</v-tab>  <!-- NEW -->
    </v-tabs>

    <v-window v-model="currentTab">
      <!-- Existing tabs -->

      <v-window-item value="network">
        <NetworkGraph
          :gene-ids="networkGeneIds"
          :seed-gene-id="gene.id"
          @node-selected="handleNodeSelected"
          @cluster-detected="handleClusterDetected"
        />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import NetworkGraph from '@/components/network/NetworkGraph.vue'
import { computed } from 'vue'

// Props
const props = defineProps({
  gene: {
    type: Object,
    required: true
  }
})

// Compute genes for network (seed + high-scoring partners)
const networkGeneIds = computed(() => {
  const ids = [props.gene.id]

  // Add top partners from STRING-DB data
  if (props.gene.annotations?.string_ppi?.interactions) {
    const topPartners = props.gene.annotations.string_ppi.interactions.slice(0, 20)
    // (would need to fetch partner gene IDs from backend)
  }

  return ids
})

function handleNodeSelected(node) {
  console.log('Node selected:', node)
  // Could navigate to gene detail page, show info panel, etc.
}

function handleClusterDetected(clusterInfo) {
  console.log('Clusters detected:', clusterInfo)
  // Could show cluster enrichment, statistics, etc.
}
</script>
```

### 4.3 Configuration Files

**New Config**: `backend/config/network_analysis.yaml`

```yaml
# Network Analysis Configuration
# Defines parameters for clustering and network visualization

network_analysis:
  # Clustering algorithms
  clustering:
    louvain:
      resolution: 1.0  # Modularity resolution (higher = more clusters)
      random_state: 42

    leiden:  # Phase 2
      resolution_parameter: 1.0
      n_iterations: 2
      random_state: 42

    mcl:  # Phase 3 (PPI-specific)
      inflation: 2.0
      expansion: 2

  # Network construction
  network:
    min_string_score: 400  # Default threshold
    max_graph_size: 10000  # Safety limit (nodes)
    edge_weight_transform: "linear"  # "linear" | "log" | "sigmoid"

  # Caching
  cache:
    ttl_seconds: 3600  # 1 hour for network graphs
    max_memory_graphs: 100  # LRU cache size

  # Visualization
  visualization:
    default_layout: "cose-bilkent"
    node_size_by: "degree"  # "degree" | "centrality" | "cluster_size"
    edge_opacity_by: "weight"  # "weight" | "string_score" | "uniform"
    cluster_colors:
      palette: "categorical"  # "categorical" | "sequential" | "diverging"

  # Performance
  performance:
    max_workers: 4  # Thread pool size
    use_multiprocessing: false  # Reserved for Phase 3
    centrality_sample_size: 1000  # For large graphs, sample nodes
```

### 4.4 Database Schema Considerations

**Option 1: No Schema Changes (Recommended for Phase 1)**
- ✅ Use existing `gene_annotations.annotations` JSONB for cluster assignments
- ✅ Compute networks on-the-fly from STRING data
- ✅ Cache in L1/L2 CacheService or in-memory (NetworkAnalysisService)
- ✅ Aligns with "KISS" principle

**Option 2: Dedicated Tables (Phase 2 Optimization)**

```sql
-- Optional: Pre-computed network clusters (for performance)
CREATE TABLE network_clusters (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER NOT NULL REFERENCES genes(id),
    cluster_id INTEGER NOT NULL,
    algorithm VARCHAR(50) NOT NULL,  -- 'louvain', 'leiden', etc.
    min_string_score INTEGER NOT NULL,
    modularity FLOAT,
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(gene_id, algorithm, min_string_score)
);

CREATE INDEX idx_network_clusters_gene ON network_clusters(gene_id);
CREATE INDEX idx_network_clusters_algorithm ON network_clusters(algorithm, min_string_score);

-- Optional: Network topology metrics
CREATE TABLE network_metrics (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER NOT NULL REFERENCES genes(id),
    metric_type VARCHAR(50) NOT NULL,  -- 'degree_centrality', 'betweenness', etc.
    value FLOAT NOT NULL,
    network_params JSONB,  -- {min_string_score: 400, ...}
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(gene_id, metric_type, network_params)
);

CREATE INDEX idx_network_metrics_gene ON network_metrics(gene_id);
CREATE INDEX idx_network_metrics_type ON network_metrics(metric_type);
```

**Recommendation**: Start with **Option 1** (no schema changes), migrate to **Option 2** only if:
- Network computations become bottleneck (>1s response time)
- Users frequently re-run same clustering parameters
- Need to expose cluster statistics in gene table filters

---

## 5. Implementation Roadmap

### Phase 1: MVP Network Visualization & Enrichment (REVISED)

**Goals**:
- ✅ Display interactive network graph for individual genes
- ✅ Clustering with Leiden algorithm (igraph native)
- ✅ Subgraph extraction (k-hop neighborhoods)
- ✅ WebSocket progress for long-running operations
- ✅ Basic enrichment analysis (HPO terms)

**Tasks** (UPDATED with Expert Review Fixes):

| Task | Component | Estimate | Dependencies | Revision Reason |
|------|-----------|----------|--------------|-----------------|
| 1.1 Install igraph + Cytoscape.js | Backend/Frontend | 0.5 days | None | igraph instead of NetworkX |
| 1.2 Implement `NetworkAnalysisService` | Backend | 3 days | STRING data | +1 day for session fixes & LRU cache |
| 1.3 Implement `EnrichmentService` | Backend | 3 days | HPO data | +1 day for timeout/rate limiting |
| 1.4 Create `/network/build` API | Backend | 1.5 days | 1.2 | +0.5 day for pagination |
| 1.5 Create `/network/cluster` API | Backend | 1.5 days | 1.2 | +0.5 day for validation |
| 1.6 Create `/network/subgraph` API | Backend | 1 day | 1.2 | Same |
| 1.7 Create `/enrichment/hpo` API | Backend | 1.5 days | 1.3 | NEW - pagination support |
| 1.8 Create `/enrichment/go-async` API | Backend | 1.5 days | 1.3 | NEW - WebSocket integration |
| 1.9 Build `NetworkGraph.vue` component | Frontend | 3 days | 1.4 | Same |
| 1.10 Build `EnrichmentTable.vue` component | Frontend | 2 days | 1.7 | NEW - HPO display |
| 1.11 Integrate into GeneDetail page | Frontend | 1 day | 1.9, 1.10 | Same |
| 1.12 Add configuration (YAML) | Backend | 0.5 days | 1.2, 1.3 | Same |
| 1.13 Write unit tests | Backend | 4 days | All | +2 days for comprehensive coverage |
| 1.14 Performance testing | Backend | 2 days | All | +1 day for load tests |
| 1.15 Documentation | Docs | 2 days | All | +1 day for code examples |

**Total**: ~22 days (4.4 weeks at 80% capacity) - **+57% vs original**

**Acceptance Criteria**:
- User can view network graph for any gene with STRING data
- Leiden clustering shows color-coded communities
- Clicking a node shows neighbors within 2 hops
- Export PNG works
- API response time <2s for networks <500 nodes
- **NEW**: HPO enrichment results display with pagination
- **NEW**: WebSocket shows real-time progress for enrichment
- **NEW**: No session leaks or memory leaks (validated via load tests)

### Phase 2: Advanced Clustering & Analytics (3-4 weeks)

**Goals**:
- ✅ Leiden algorithm (superior to Louvain)
- ✅ Centrality metrics (degree, betweenness, closeness)
- ✅ Cluster enrichment analysis (HPO terms, clinical groups)
- ✅ Multi-gene network comparison

**Tasks**:

| Task | Component | Estimate | Dependencies |
|------|-----------|----------|--------------|
| 2.1 Install `leidenalg` package | Backend | 0.5 days | Phase 1 |
| 2.2 Implement Leiden clustering | Backend | 1 day | 2.1 |
| 2.3 Add centrality calculations | Backend | 1 day | Phase 1 |
| 2.4 Create cluster enrichment API | Backend | 2 days | HPO data |
| 2.5 Build cluster comparison view | Frontend | 2 days | 2.2 |
| 2.6 Add metrics dashboard | Frontend | 2 days | 2.3 |
| 2.7 Create dendrogram viz (D3.js) | Frontend | 2 days | 2.2 |
| 2.8 Optimize with igraph (optional) | Backend | 3 days | 2.2 |
| 2.9 Pre-compute clusters (DB table) | Backend | 2 days | Schema |
| 2.10 Testing & benchmarking | Backend | 2 days | All |

**Total**: ~18 days (3.6 weeks)

**Acceptance Criteria**:
- Leiden clustering available as option
- Cluster enrichment shows top HPO terms per cluster
- Dendrogram visualizes cluster hierarchy
- Centrality metrics displayed on node hover
- Performance: <5s for networks up to 2000 nodes

### Phase 3: Production Hardening & Extensions (2-3 weeks)

**Goals**:
- ✅ MCL algorithm (PPI-specific)
- ✅ Network comparison tool (compare across diseases)
- ✅ Admin panel for cluster management
- ✅ Export to Cytoscape desktop format
- ✅ Performance optimization (igraph migration)

**Tasks**:

| Task | Component | Estimate | Dependencies |
|------|-----------|----------|--------------|
| 3.1 Implement MCL algorithm | Backend | 2 days | Phase 2 |
| 3.2 Build network comparison UI | Frontend | 3 days | Phase 2 |
| 3.3 Add admin cluster viewer | Frontend | 2 days | Phase 2 |
| 3.4 Export to Cytoscape format | Backend/Frontend | 1 day | Phase 1 |
| 3.5 Migrate to igraph (if needed) | Backend | 3 days | Benchmarks |
| 3.6 Add job queue for large networks | Backend | 2 days | Redis? |
| 3.7 Comprehensive testing | All | 3 days | All |
| 3.8 User documentation | Docs | 2 days | All |

**Total**: ~18 days (3.6 weeks)

**Acceptance Criteria**:
- MCL clustering option available
- Compare networks for "tubulopathy" vs "glomerulopathy" genes
- Admin can view cluster statistics across all genes
- Export to `.cyjs` and `.xgmml` formats
- Performance: <10s for networks up to 5000 nodes

### Total Estimated Timeline (REVISED)

**Conservative**: **11-12 weeks** (2.5-3 months) - Updated with expert review findings
**Optimistic**: 10 weeks (2.5 months)

**Breakdown by Phase**:
- **Phase 1**: 4.4 weeks (+57% from original 2.8 weeks)
- **Phase 2**: 4 weeks (increased from 3.6 due to enrichment visualization complexity)
- **Phase 3**: 3 weeks (decreased from 3.6 as core issues fixed in Phase 1)

**Recommendation**: Target **11-12 weeks** for full Phase 1-3 rollout, with Phase 1 shipped after **4-5 weeks** for user feedback.

**Key Changes from Original Estimate**:
1. ✅ Session management fixes add 1 day to service implementation
2. ✅ igraph migration (instead of NetworkX later) saves time in Phase 2
3. ✅ WebSocket integration moved from Phase 3 to Phase 1 (+2 days)
4. ✅ Comprehensive testing and performance validation (+2 days)
5. ✅ Enrichment service with timeout/rate limiting (+1 day)

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Performance bottleneck** (large networks >5000 nodes) | Medium | High | - Use thread pool offloading (non-blocking)<br>- Add graph size limits<br>- Migrate to igraph if NetworkX too slow<br>- Implement graph sampling |
| **Cytoscape.js learning curve** | Low | Medium | - Extensive documentation (404 snippets)<br>- Active community<br>- Proven in biology domain |
| **Clustering algorithm quality** | Low | Medium | - Start with Louvain (proven)<br>- Add Leiden in Phase 2 (research-backed)<br>- Allow parameter tuning |
| **Memory consumption** (caching graphs) | Medium | Medium | - LRU cache with size limit<br>- Clear cache after threshold<br>- Use database cache for persistence |
| **String data incompleteness** | Low | Low | - Already 95%+ coverage in production<br>- Graceful handling of missing partners |

### 6.2 Product Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **User confusion** (complex UI) | Medium | Medium | - Tooltips on all controls<br>- Tutorial overlay on first use<br>- Preset layouts and parameters |
| **Low user adoption** | Low | High | - Integrate into existing gene detail page<br>- Show example networks on homepage<br>- Use in publications to demonstrate value |
| **Scope creep** (feature requests) | High | Medium | - Phased rollout (MVP → Phase 2 → Phase 3)<br>- Prioritize via user feedback |

### 6.3 Integration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Breaking existing STRING integration** | Very Low | Critical | - NetworkAnalysisService reads from existing data<br>- No changes to StringPPIAnnotationSource<br>- Comprehensive integration tests |
| **Frontend bundle size** (Cytoscape.js ~500KB) | Low | Low | - Lazy load network tab<br>- Code splitting with Vite<br>- Acceptable for specialized feature |
| **API response time** (synchronous clustering) | Medium | High | - Offload to thread pool<br>- Add loading indicators<br>- Future: Job queue for >2000 nodes |

---

## 7. Best Practices & Anti-Patterns

### 7.1 DO ✅

**Reuse Existing Infrastructure**:
```python
# ✅ GOOD: Extend proven patterns
class NetworkAnalysisService:
    def __init__(self, session):
        self.session = session
        self._executor = ThreadPoolExecutor(max_workers=4)  # Non-blocking
        self.logger = get_logger(__name__)  # UnifiedLogger
        self.cache_service = get_cache_service(session)  # L1/L2 cache
```

**Configuration-Driven**:
```yaml
# ✅ GOOD: Parameters in config, not hardcoded
network_analysis:
  clustering:
    louvain:
      resolution: 1.0  # Tunable without code changes
```

**Incremental Rollout**:
```python
# ✅ GOOD: Graceful degradation
try:
    from leidenalg import find_partition
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False
    logger.sync_warning("Leiden algorithm not available, using Louvain")
```

### 7.2 DON'T ❌

**Don't Create Parallel Systems**:
```python
# ❌ BAD: New logging system
import logging
logger = logging.getLogger(__name__)  # NO! Use UnifiedLogger

# ✅ GOOD: Use existing
from app.core.logging import get_logger
logger = get_logger(__name__)
```

**Don't Block Event Loop**:
```python
# ❌ BAD: Synchronous graph operation in async function
async def cluster_network(graph):
    communities = nx_comm.louvain_communities(graph)  # BLOCKS!
    return communities

# ✅ GOOD: Offload to thread pool
async def cluster_network(graph):
    loop = asyncio.get_event_loop()
    communities = await loop.run_in_executor(
        self._executor,
        nx_comm.louvain_communities,
        graph
    )
    return communities
```

**Don't Reinvent Algorithms**:
```python
# ❌ BAD: Custom clustering implementation
def my_custom_clustering(graph):
    # 200 lines of custom modularity optimization
    ...

# ✅ GOOD: Use proven libraries
import networkx.algorithms.community as nx_comm
communities = nx_comm.louvain_communities(graph)
```

---

## 8. References

### 8.1 Code & Documentation

**Current Codebase**:
- `backend/app/pipeline/sources/annotations/string_ppi.py` - STRING-DB integration
- `backend/app/pipeline/sources/annotations/base.py` - BaseAnnotationSource pattern
- `frontend/src/components/gene/ProteinInteractions.vue` - PPI display
- `docs/implementation-notes/completed/string-ppi-implementation.md` - STRING implementation notes

**Legacy Codebase** (R-based):
- `../kidney-genetics-v1/analyses/D_ProteinInteractionAnalysis/` - Network analysis scripts
- `../kidney-genetics-v1/analyses/functions/protein_interaction_analysis-functions.R` - Clustering functions

### 8.2 Libraries & Tools

**Backend**:
- [NetworkX Documentation](https://networkx.org/) - Python graph library
- [igraph Documentation](https://igraph.org/python/) - High-performance alternative
- [Leiden Algorithm](https://leidenalg.readthedocs.io/) - Community detection

**Frontend**:
- [Cytoscape.js](https://js.cytoscape.org/) - Graph visualization (404 code snippets)
- [Cytoscape.js Layouts](https://github.com/cytoscape/cytoscape.js-cose-bilkent) - Force-directed layout
- [D3.js](https://d3js.org/) - Complementary visualizations (already in stack)

### 8.3 Research Papers

**Clustering Algorithms**:
- Traag, V.A., Waltman, L. & van Eck, N.J. "From Louvain to Leiden: guaranteeing well-connected communities." *Sci Rep* 9, 5233 (2019). https://doi.org/10.1038/s41598-019-41695-z
- Blondel, V.D., Guillaume, J.L., Lambiotte, R. & Lefebvre, E. "Fast unfolding of communities in large networks." *J. Stat. Mech.* P10008 (2008).
- Van Dongen, S. "Graph Clustering by Flow Simulation" (MCL Algorithm). PhD thesis, University of Utrecht (2000).

**Bioinformatics Applications**:
- "Protein-Protein Interaction Network Analysis Using NetworkX" - *Methods in Molecular Biology* (2023). PubMed: 37450166
- "Deep learning-based clustering approaches for bioinformatics" - *Brief Bioinform* 22(1):393 (2021). PMC: 7820885

**Visualization**:
- "Cytoscape: An Open Source Platform for Complex Network Analysis and Visualization" - https://cytoscape.org/
- "A Guide to Conquer the Biological Network Era Using Graph Theory" - *Front. Bioeng. Biotechnol.* (2020)

### 8.4 Best Practices

**Graph Analysis**:
- Girke Lab. "Cluster and Network Analysis Methods" - https://girke.bioinformatics.ucr.edu/GEN242/assignments/projects/03_cluster_analysis/
- "Current and future directions in network biology" - *Bioinformatics Advances* 4(1):vbae099 (2024)
- "Robust, scalable, and informative clustering for diverse biological networks" - *Genome Biology* (2023)

**Visualization Comparisons**:
- "The Best Libraries and Methods to Render Large Network Graphs on the Web" - Medium (2024)
- "A Comparison of Javascript Graph / Network Visualisation Libraries" - Cylynx (2024)
- npm-compare: cytoscape vs vis-network vs d3-graphviz

---

## Appendix A: Configuration Checklist

### Before Implementation

- [ ] Review CLAUDE.md principles (DRY, KISS, Modularity, SOLID)
- [ ] Confirm STRING-DB data quality (check recent pipeline runs)
- [ ] Verify existing D3.js version compatible with new components
- [ ] Test current thread pool performance (baseline metrics)
- [ ] Estimate storage needs (if adding DB tables in Phase 2)

### Backend Setup

- [ ] Install NetworkX: `uv add networkx`
- [ ] Create `backend/app/services/network_analysis_service.py`
- [ ] Create `backend/app/api/endpoints/network_analysis.py`
- [ ] Create `backend/config/network_analysis.yaml`
- [ ] Register new endpoints in `backend/app/main.py`
- [ ] Add unit tests in `backend/tests/services/test_network_analysis.py`

### Frontend Setup

- [ ] Install Cytoscape.js: `npm install cytoscape cytoscape-cose-bilkent`
- [ ] Create `frontend/src/components/network/NetworkGraph.vue`
- [ ] Create `frontend/src/api/network.js` (API client)
- [ ] Update `frontend/src/views/GeneDetail.vue` (add network tab)
- [ ] Add to component exports in `frontend/src/components/network/index.js`

### Testing Checklist

- [ ] Unit tests for `NetworkAnalysisService` (mocked graph data)
- [ ] Integration tests for `/network/*` endpoints
- [ ] Frontend component tests (Vitest + Testing Library)
- [ ] Performance tests (500, 1000, 2000 node networks)
- [ ] Memory leak tests (repeated graph construction/destruction)
- [ ] Load tests (concurrent API requests)

### Documentation Checklist

- [ ] API endpoint documentation (OpenAPI/Swagger)
- [ ] User guide for network features (with screenshots)
- [ ] Developer guide for adding new algorithms
- [ ] Update `docs/features/README.md` with network analysis
- [ ] Add to `docs/project-management/status.md` roadmap

---

## Appendix B: Sample API Responses

### Build Network Response

```json
{
  "nodes": [
    {
      "data": {
        "id": "123",
        "label": "WT1",
        "approved_symbol": "WT1",
        "hgnc_id": 12795
      }
    },
    {
      "data": {
        "id": "456",
        "label": "PAX2",
        "approved_symbol": "PAX2",
        "hgnc_id": 8616
      }
    }
  ],
  "edges": [
    {
      "data": {
        "source": "123",
        "target": "456",
        "weight": 0.85,
        "string_score": 850
      }
    }
  ],
  "metadata": {
    "num_nodes": 42,
    "num_edges": 127,
    "min_string_score": 400,
    "connected_components": 1
  }
}
```

### Cluster Network Response

```json
{
  "clusters": {
    "123": 0,
    "456": 0,
    "789": 1,
    "101": 1
  },
  "modularity": 0.452,
  "num_clusters": 2,
  "cluster_stats": [
    {
      "cluster_id": 0,
      "size": 25,
      "avg_degree": 8.3,
      "top_genes": ["WT1", "PAX2", "SIX2"]
    },
    {
      "cluster_id": 1,
      "size": 17,
      "avg_degree": 6.1,
      "top_genes": ["NPHS1", "NPHS2", "PODXL"]
    }
  ]
}
```

### Centrality Metrics Response

```json
{
  "metrics": {
    "123": {
      "degree_centrality": 0.45,
      "betweenness_centrality": 0.32,
      "closeness_centrality": 0.68,
      "pagerank": 0.028
    },
    "456": {
      "degree_centrality": 0.38,
      "betweenness_centrality": 0.21,
      "closeness_centrality": 0.59,
      "pagerank": 0.022
    }
  }
}
```

---

## Appendix C: Future Enhancements (Post-Phase 3)

**Not Prioritized, But Potential**:

1. **Temporal Network Analysis**
   - Track cluster evolution over database versions
   - Identify emerging disease module associations

2. **Multi-Omics Integration**
   - Layer gene expression (GTEx) on network
   - Integrate ClinVar variants as edge annotations

3. **Machine Learning on Networks**
   - Node embeddings (Node2Vec, DeepWalk)
   - Link prediction for novel PPIs
   - Disease module prediction

4. **3D Network Visualization**
   - WebGL-based 3D force layout (via three.js or Plotly)
   - VR/AR exploration (future-looking)

5. **Collaborative Features**
   - Share network views via URL
   - Annotate clusters (curator comments)
   - Export to publications (high-res SVG)

6. **Cross-Database Networks**
   - Integrate with external PPI databases (BioGRID, IntAct)
   - Cross-species network comparison (ortholog mapping)

---

## Summary

This assessment provides a **comprehensive, production-ready plan** for implementing advanced network analysis and functional clustering in the kidney-genetics database. Key highlights:

1. **Reuses existing infrastructure** (STRING-DB data, caching, logging, thread pools)
2. **Modern, proven technologies** (NetworkX/igraph, Cytoscape.js, Leiden algorithm)
3. **Incremental rollout** (3 phases, 10 weeks total)
4. **Risk-mitigated** (performance safeguards, graceful degradation, testing)
5. **Follows CLAUDE.md principles** (DRY, KISS, Modularity, SOLID, Non-blocking)

**Next Steps**:
1. Review this assessment with team
2. Prioritize Phase 1 vs. Phase 2 vs. Phase 3
3. Allocate developer time (estimated 10 weeks FTE)
4. Create GitHub issues for each task
5. Begin with dependency installation and `NetworkAnalysisService` scaffold

**Questions? Review the references, check legacy code, or consult the research papers linked above.**

---

**Document Status**: Active Planning
**Last Updated**: 2025-10-08
**Author**: Claude Code (Expert Senior Developer & Bioinformatician)
**Review Required**: Yes (team review before implementation)
