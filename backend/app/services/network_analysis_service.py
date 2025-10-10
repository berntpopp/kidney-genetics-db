"""
Network Analysis Service

Provides protein-protein interaction network analysis using igraph.
Integrates with existing STRING-DB annotations stored in JSONB.

CRITICAL DESIGN PATTERNS:
- Thread-safe: Session passed per-call, not stored
- Non-blocking: Heavy operations offloaded to thread pool
- Memory-safe: LRU cache with TTL prevents memory leaks
- Reuses: Singleton thread pool from database.py
"""

import asyncio
import threading
from typing import Any

import igraph as ig
from cachetools import TTLCache
from sqlalchemy.orm import Session

from app.core.database import get_db_context, get_thread_pool_executor
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation

logger = get_logger(__name__)


class NetworkAnalysisService:
    """
    Service for analyzing protein-protein interaction networks from STRING-DB data.

    Performance characteristics:
    - Graph construction: <1s for 500 nodes
    - Clustering: <2s for 500 nodes (Leiden algorithm)
    - Cache: LRU with 1-hour TTL, max 50 graphs (~2.5GB)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize network analysis service.

        IMPORTANT: Session NOT stored - passed per-call for thread safety.
        """
        self.config = config or self._load_default_config()
        self._executor = get_thread_pool_executor()  # Singleton from database.py

        # LRU cache with TTL - prevents memory leaks
        # Max 50 graphs @ ~50MB each = ~2.5GB max memory
        self._graph_cache = TTLCache(maxsize=50, ttl=3600)  # 1 hour TTL
        self._cache_lock = threading.Lock()

    async def build_network_from_string_data(
        self,
        gene_ids: list[int],
        session: Session,
        min_string_score: int = 400
    ) -> ig.Graph:
        """
        Construct igraph from STRING-DB annotations stored in database.

        Args:
            gene_ids: List of gene IDs to include in network
            session: Database session (passed per-call for thread safety)
            min_string_score: Minimum STRING confidence score (0-1000)

        Returns:
            igraph.Graph with:
            - Vertex attributes: gene_id
            - Edge attributes: weight (normalized), string_score (raw)

        Performance: <1s for 500 nodes, cached for 1 hour
        """
        # Check cache first
        cache_key = f"network:{len(gene_ids)}:{min_string_score}"

        with self._cache_lock:
            if cache_key in self._graph_cache:
                await logger.debug(
                    "Using cached network graph",
                    cache_key=cache_key,
                    nodes=len(gene_ids)
                )
                return self._graph_cache[cache_key]

        # Build graph in thread pool (non-blocking for event loop)
        loop = asyncio.get_event_loop()
        graph = await loop.run_in_executor(
            self._executor,
            self._build_graph_sync,
            gene_ids,
            min_string_score
        )

        # Cache result
        with self._cache_lock:
            self._graph_cache[cache_key] = graph

        await logger.info(
            "Built and cached network graph",
            nodes=graph.vcount(),
            edges=graph.ecount(),
            components=len(graph.connected_components())
        )

        return graph

    def _build_graph_sync(
        self,
        gene_ids: list[int],
        min_string_score: int
    ) -> ig.Graph:
        """
        Synchronous graph construction (runs in thread pool).

        THREAD-SAFE: Creates fresh session using get_db_context()
        """
        with get_db_context() as db:
            # Create empty igraph
            g = ig.Graph()
            g.add_vertices(len(gene_ids))
            g.vs["gene_id"] = gene_ids

            # Query STRING annotations from JSONB
            annotations = (
                db.query(GeneAnnotation)
                .filter(
                    GeneAnnotation.gene_id.in_(gene_ids),
                    GeneAnnotation.source == "string_ppi"
                )
                .all()
            )

            # Build gene_id → vertex index mapping
            gene_id_to_idx = {gid: idx for idx, gid in enumerate(gene_ids)}

            # Build edge list
            edges = []
            weights = []
            string_scores = []

            for ann in annotations:
                data = ann.annotations
                if not data or "interactions" not in data:
                    continue

                source_idx = gene_id_to_idx.get(ann.gene_id)
                if source_idx is None:
                    continue

                # Extract interactions from JSONB
                for interaction in data["interactions"]:
                    score = interaction.get("string_score", 0)

                    if score >= min_string_score:
                        # Get partner gene_id
                        partner_symbol = interaction.get("partner_symbol")
                        if not partner_symbol:
                            continue

                        partner_gene = (
                            db.query(Gene)
                            .filter_by(approved_symbol=partner_symbol)
                            .first()
                        )

                        if partner_gene and partner_gene.id in gene_id_to_idx:
                            target_idx = gene_id_to_idx[partner_gene.id]
                            edges.append((source_idx, target_idx))
                            weights.append(score / 1000.0)  # Normalize to 0-1
                            string_scores.append(score)

            # Add edges to graph
            if edges:
                g.add_edges(edges)
                g.es["weight"] = weights
                g.es["string_score"] = string_scores

            logger.sync_info(
                "Built network graph in thread pool",
                nodes=g.vcount(),
                edges=g.ecount(),
                components=len(g.connected_components()),
                min_score=min_string_score
            )

            return g

    async def detect_communities(
        self,
        graph: ig.Graph,
        session: Session,
        algorithm: str = "leiden"
    ) -> tuple[dict[int, int], float]:
        """
        Detect communities using igraph clustering algorithms.

        Args:
            graph: igraph.Graph to cluster
            session: Database session
            algorithm: "leiden" (default), "louvain", or "walktrap"

        Returns:
            Tuple of ({gene_id: cluster_id} mapping, modularity_score)

        Performance: <2s for 500 nodes with Leiden
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self._detect_communities_sync,
            graph,
            algorithm
        )
        return result

    def _detect_communities_sync(
        self,
        graph: ig.Graph,
        algorithm: str
    ) -> tuple[dict[int, int], float]:
        """
        Synchronous community detection (runs in thread pool).

        Returns:
            Tuple of ({gene_id: cluster_id} mapping, modularity_score)
        """
        if algorithm == "leiden":
            # Leiden algorithm (superior to Louvain)
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
            raise ValueError(f"Unknown algorithm: {algorithm}. Use 'leiden', 'louvain', or 'walktrap'")

        # Convert to {gene_id: cluster_id} mapping
        gene_to_cluster = {}
        for cluster_id, members in enumerate(partition):
            for vertex_idx in members:
                gene_id = graph.vs[vertex_idx]["gene_id"]
                gene_to_cluster[gene_id] = cluster_id

        # Calculate modularity
        modularity = graph.modularity(partition, weights="weight")

        logger.sync_info(
            f"Detected communities using {algorithm}",
            num_clusters=len(partition),
            algorithm=algorithm,
            modularity=round(modularity, 3),
            nodes=graph.vcount()
        )

        return gene_to_cluster, modularity

    async def get_k_hop_subgraph(
        self,
        graph: ig.Graph,
        seed_gene_ids: list[int],
        session: Session,
        k: int = 2
    ) -> ig.Graph:
        """
        Extract k-hop neighborhood subgraph around seed genes.

        Args:
            graph: Full network graph
            seed_gene_ids: Gene IDs to center subgraph around
            session: Database session
            k: Number of hops (default: 2)

        Returns:
            Subgraph containing seed genes and their k-hop neighbors
        """
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
        seed_gene_ids: list[int],
        k: int
    ) -> ig.Graph:
        """
        Synchronous k-hop subgraph extraction.
        """
        vertices_to_include = set()

        # Find seed vertices and their k-hop neighborhoods
        for seed_gene_id in seed_gene_ids:
            try:
                # Find vertex by gene_id attribute
                seed_vertices = [v for v in graph.vs if v["gene_id"] == seed_gene_id]
                if not seed_vertices:
                    logger.sync_debug(f"Seed gene {seed_gene_id} not in graph")
                    continue

                seed_vertex = seed_vertices[0]
                vertices_to_include.add(seed_vertex.index)

                # Get k-hop neighborhood using BFS
                neighborhood = graph.neighborhood(
                    vertices=seed_vertex.index,
                    order=k,
                    mode="all"  # Undirected
                )
                vertices_to_include.update(neighborhood)

            except (ValueError, IndexError) as e:
                logger.sync_debug(
                    f"Error finding seed gene {seed_gene_id}: {e}"
                )
                continue

        # Extract subgraph
        if not vertices_to_include:
            # Return empty graph if no seeds found
            return ig.Graph()

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
        session: Session,
        metrics: list[str] = None
    ) -> dict[int, dict[str, float]]:
        """
        Calculate centrality metrics for all nodes.

        Args:
            graph: Network graph
            session: Database session
            metrics: List of metrics to calculate
                    (default: ["degree", "betweenness", "closeness"])

        Returns:
            {gene_id: {metric_name: value}}
        """
        if metrics is None:
            metrics = ["degree", "betweenness", "closeness"]

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
        metrics: list[str]
    ) -> dict[int, dict[str, float]]:
        """
        Synchronous centrality calculation.

        igraph is 10-50x faster than NetworkX for these operations.
        """
        results = {v["gene_id"]: {} for v in graph.vs}

        if "degree" in metrics:
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

        logger.sync_info(
            "Calculated centrality metrics",
            metrics=metrics,
            node_count=graph.vcount()
        )

        return results

    async def filter_network(
        self,
        graph: ig.Graph,
        session: Session,
        min_degree: int = 1,
        remove_isolated: bool = True,
        largest_component_only: bool = False
    ) -> ig.Graph:
        """
        Filter network graph by removing low-degree and isolated nodes.

        Args:
            graph: Network graph to filter
            session: Database session
            min_degree: Minimum node degree threshold (default: 1)
            remove_isolated: Remove nodes with degree=0 (default: True)
            largest_component_only: Keep only largest connected component (default: False)

        Returns:
            Filtered subgraph

        Best Practices:
            - Remove isolated nodes (degree=0) to reduce visual clutter
            - Set min_degree=2 to show only nodes with multiple interactions
            - Use largest_component_only=True for cleaner visualization
        """
        loop = asyncio.get_event_loop()
        filtered_graph = await loop.run_in_executor(
            self._executor,
            self._filter_network_sync,
            graph,
            min_degree,
            remove_isolated,
            largest_component_only
        )
        return filtered_graph

    def _filter_network_sync(
        self,
        graph: ig.Graph,
        min_degree: int,
        remove_isolated: bool,
        largest_component_only: bool
    ) -> ig.Graph:
        """
        Synchronous network filtering (runs in thread pool).
        """
        if graph.vcount() == 0:
            return graph

        vertices_to_keep = set(range(graph.vcount()))

        # Filter by degree
        if remove_isolated or min_degree > 0:
            degrees = graph.degree()
            threshold = max(1 if remove_isolated else 0, min_degree)
            vertices_to_keep = {
                v.index for v in graph.vs
                if degrees[v.index] >= threshold
            }

        # Keep only largest component if requested
        if largest_component_only and vertices_to_keep:
            components = graph.connected_components()
            if len(components) > 0:
                largest_component = max(components, key=len)
                vertices_to_keep = vertices_to_keep & set(largest_component)

        if not vertices_to_keep:
            logger.sync_warning("All vertices filtered out, returning empty graph")
            return ig.Graph()

        # Create filtered subgraph
        filtered_graph = graph.subgraph(list(vertices_to_keep))

        logger.sync_info(
            "Filtered network graph",
            original_nodes=graph.vcount(),
            filtered_nodes=filtered_graph.vcount(),
            removed_nodes=graph.vcount() - filtered_graph.vcount(),
            min_degree=min_degree,
            remove_isolated=remove_isolated
        )

        return filtered_graph

    async def filter_clusters_by_size(
        self,
        gene_to_cluster: dict[int, int],
        session: Session,
        min_cluster_size: int = 3
    ) -> dict[int, int]:
        """
        Filter out small clusters below size threshold.

        Args:
            gene_to_cluster: {gene_id: cluster_id} mapping
            session: Database session
            min_cluster_size: Minimum cluster size (default: 3)

        Returns:
            Filtered {gene_id: cluster_id} mapping with small clusters removed

        Best Practices:
            - Use min_cluster_size=3 to remove singleton and doublet clusters
            - Use min_cluster_size=5-10 for large networks with many clusters
        """
        loop = asyncio.get_event_loop()
        filtered_mapping = await loop.run_in_executor(
            self._executor,
            self._filter_clusters_by_size_sync,
            gene_to_cluster,
            min_cluster_size
        )
        return filtered_mapping

    def _filter_clusters_by_size_sync(
        self,
        gene_to_cluster: dict[int, int],
        min_cluster_size: int
    ) -> dict[int, int]:
        """
        Synchronous cluster size filtering.
        """
        # Count cluster sizes
        cluster_sizes = {}
        for _gene_id, cluster_id in gene_to_cluster.items():
            cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1

        # Filter clusters below threshold
        clusters_to_keep = {
            cluster_id for cluster_id, size in cluster_sizes.items()
            if size >= min_cluster_size
        }

        # Create filtered mapping with renumbered cluster IDs
        filtered_mapping = {}
        cluster_id_remap = {}
        next_cluster_id = 0

        for gene_id, cluster_id in gene_to_cluster.items():
            if cluster_id in clusters_to_keep:
                # Renumber cluster IDs sequentially
                if cluster_id not in cluster_id_remap:
                    cluster_id_remap[cluster_id] = next_cluster_id
                    next_cluster_id += 1
                filtered_mapping[gene_id] = cluster_id_remap[cluster_id]

        original_clusters = len(cluster_sizes)
        filtered_clusters = len(cluster_id_remap)
        removed_genes = len(gene_to_cluster) - len(filtered_mapping)

        logger.sync_info(
            "Filtered small clusters",
            original_clusters=original_clusters,
            filtered_clusters=filtered_clusters,
            removed_clusters=original_clusters - filtered_clusters,
            removed_genes=removed_genes,
            min_cluster_size=min_cluster_size
        )

        return filtered_mapping

    def _load_default_config(self) -> dict[str, Any]:
        """
        Load configuration from YAML using centralized config system.

        Uses get_config() to load from network_analysis.yaml.
        """
        from app.core.datasource_config import get_config

        cfg = get_config()
        na_config = cfg.network_analysis

        return {
            # Leiden algorithm parameters
            "leiden_resolution": na_config.get("clustering", {}).get("leiden", {}).get("resolution", 1.0),
            "leiden_iterations": na_config.get("clustering", {}).get("leiden", {}).get("iterations", 2),
            # Louvain algorithm parameters
            "louvain_resolution": na_config.get("clustering", {}).get("louvain", {}).get("resolution", 1.0),
            # Walktrap algorithm parameters
            "walktrap_steps": na_config.get("clustering", {}).get("walktrap", {}).get("steps", 4),
            # Network construction
            "min_string_score": na_config.get("network", {}).get("min_string_score", 400),
            "max_graph_size": na_config.get("network", {}).get("max_nodes", 2000),
            # Filtering defaults (from config, not hardcoded)
            "default_min_degree": na_config.get("filtering", {}).get("default_min_degree", 0),
            "default_min_cluster_size": na_config.get("filtering", {}).get("default_min_cluster_size", 1),
            "default_remove_isolated": na_config.get("filtering", {}).get("default_remove_isolated", False),
            "default_largest_component_only": na_config.get("filtering", {}).get("default_largest_component_only", False),
            # Cache settings
            "cache_ttl_seconds": na_config.get("network", {}).get("cache_ttl_hours", 1) * 3600,
            "max_cached_graphs": na_config.get("network", {}).get("max_cached_graphs", 50)
        }

    def clear_cache(self) -> None:
        """
        Clear all cached graphs.

        Useful for testing or when memory needs to be freed.
        """
        with self._cache_lock:
            cleared_count = len(self._graph_cache)
            self._graph_cache.clear()

        logger.sync_info(f"Cleared {cleared_count} cached graphs")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            {
                "current_size": int,
                "max_size": int,
                "ttl_seconds": int,
                "hit_rate": float  # If tracking is enabled
            }
        """
        with self._cache_lock:
            return {
                "current_size": len(self._graph_cache),
                "max_size": self._graph_cache.maxsize,
                "ttl_seconds": self._graph_cache.ttl,
                "utilization": len(self._graph_cache) / self._graph_cache.maxsize
            }
