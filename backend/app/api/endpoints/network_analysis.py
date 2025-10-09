"""
Network Analysis API endpoints - PPI networks and functional enrichment
"""

import time
from typing import Any

import igraph as ig
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.models.gene import Gene
from app.schemas.network import (
    GOEnrichmentRequest,
    GOEnrichmentResponse,
    HPOEnrichmentRequest,
    HPOEnrichmentResponse,
    NetworkBuildRequest,
    NetworkBuildResponse,
    NetworkClusterRequest,
    NetworkClusterResponse,
    SubgraphRequest,
)
from app.services.enrichment_service import EnrichmentService
from app.services.network_analysis_service import NetworkAnalysisService

router = APIRouter()
logger = get_logger(__name__)

# Service instances (stateless - no session stored)
network_service = NetworkAnalysisService()
enrichment_service = EnrichmentService()


def igraph_to_cytoscape(
    graph: ig.Graph,
    gene_id_to_symbol: dict[int, str],
    cluster_colors: dict[int, str] | None = None
) -> dict[str, Any]:
    """
    Convert igraph to Cytoscape.js JSON format.

    Args:
        graph: igraph.Graph with gene_id vertex attribute
        gene_id_to_symbol: Mapping of gene_id -> approved_symbol
        cluster_colors: Optional mapping of cluster_id -> color (hex)

    Returns:
        Cytoscape.js JSON with nodes and edges
    """
    elements = []

    # Add nodes
    for vertex in graph.vs:
        gene_id = vertex["gene_id"]
        symbol = gene_id_to_symbol.get(gene_id, f"Gene_{gene_id}")

        node_data = {
            "data": {
                "id": str(gene_id),
                "label": symbol,
                "gene_id": gene_id,
                "degree": vertex.degree(),
            }
        }

        # Add cluster color if provided
        if cluster_colors and "cluster_id" in vertex.attributes():
            cluster_id = vertex["cluster_id"]
            node_data["data"]["cluster_id"] = cluster_id
            if cluster_id in cluster_colors:
                node_data["data"]["color"] = cluster_colors[cluster_id]

        elements.append(node_data)

    # Add edges
    for edge in graph.es:
        source_id = graph.vs[edge.source]["gene_id"]
        target_id = graph.vs[edge.target]["gene_id"]

        edge_data = {
            "data": {
                "id": f"{source_id}_{target_id}",
                "source": str(source_id),
                "target": str(target_id),
                "weight": edge["weight"] if "weight" in edge.attributes() else 1.0,
                "string_score": edge["string_score"] if "string_score" in edge.attributes() else None,
            }
        }

        elements.append(edge_data)

    return {"elements": elements}


def generate_cluster_colors(num_clusters: int) -> dict[int, str]:
    """
    Generate distinct colors for clusters.

    Uses a categorical color palette for visual distinction.

    Args:
        num_clusters: Number of clusters to color

    Returns:
        {cluster_id: hex_color}
    """
    # Material Design categorical palette (up to 20 distinct colors)
    colors = [
        "#1f77b4",  # Blue
        "#ff7f0e",  # Orange
        "#2ca02c",  # Green
        "#d62728",  # Red
        "#9467bd",  # Purple
        "#8c564b",  # Brown
        "#e377c2",  # Pink
        "#7f7f7f",  # Gray
        "#bcbd22",  # Olive
        "#17becf",  # Cyan
        "#aec7e8",  # Light blue
        "#ffbb78",  # Light orange
        "#98df8a",  # Light green
        "#ff9896",  # Light red
        "#c5b0d5",  # Light purple
        "#c49c94",  # Light brown
        "#f7b6d2",  # Light pink
        "#c7c7c7",  # Light gray
        "#dbdb8d",  # Light olive
        "#9edae5",  # Light cyan
    ]

    # Cycle colors if more clusters than colors
    return {i: colors[i % len(colors)] for i in range(num_clusters)}


@router.post("/build", response_model=NetworkBuildResponse)
async def build_network(
    request: NetworkBuildRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Build protein-protein interaction network from STRING-DB data.

    Constructs network from gene_annotations.annotations JSONB column
    where source='string_ppi'.

    Performance: <1s for 500 nodes, cached for 1 hour
    """
    start_time = time.time()

    # Validate max nodes
    if len(request.gene_ids) > 2000:
        raise ValidationError(
            field="gene_ids",
            reason=f"Maximum 2000 genes allowed, got {len(request.gene_ids)}"
        )

    # Get gene symbols for Cytoscape labels
    genes = db.query(Gene).filter(Gene.id.in_(request.gene_ids)).all()
    gene_id_to_symbol = {g.id: g.approved_symbol for g in genes}

    if not gene_id_to_symbol:
        raise HTTPException(status_code=404, detail="No valid genes found")

    await logger.info(
        "Building network",
        gene_count=len(request.gene_ids),
        min_score=request.min_string_score
    )

    # Build network using service
    graph = await network_service.build_network_from_string_data(
        gene_ids=request.gene_ids,
        session=db,
        min_string_score=request.min_string_score
    )

    await logger.info(
        "Initial network built",
        nodes=graph.vcount(),
        edges=graph.ecount(),
        components=len(graph.connected_components())
    )

    # Apply filtering if requested
    if request.min_degree > 0 or request.remove_isolated or request.largest_component_only:
        await logger.info(
            "Applying network filters",
            min_degree=request.min_degree,
            remove_isolated=request.remove_isolated,
            largest_component_only=request.largest_component_only
        )
        graph = await network_service.filter_network(
            graph=graph,
            session=db,
            min_degree=request.min_degree,
            remove_isolated=request.remove_isolated,
            largest_component_only=request.largest_component_only
        )
        await logger.info(
            "Network filtering applied",
            final_nodes=graph.vcount(),
            final_edges=graph.ecount()
        )

    # Convert to Cytoscape.js format
    cytoscape_json = igraph_to_cytoscape(graph, gene_id_to_symbol)

    elapsed_ms = (time.time() - start_time) * 1000

    await logger.info(
        "Network build complete",
        nodes=graph.vcount(),
        edges=graph.ecount(),
        components=len(graph.connected_components()),
        elapsed_ms=round(elapsed_ms, 2)
    )

    return NetworkBuildResponse(
        nodes=graph.vcount(),
        edges=graph.ecount(),
        components=len(graph.connected_components()),
        cytoscape_json=cytoscape_json
    )


@router.post("/cluster", response_model=NetworkClusterResponse)
async def cluster_network(
    request: NetworkClusterRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Detect communities in PPI network using graph clustering.

    Supports Leiden (default), Louvain, and Walktrap algorithms.

    Performance: <2s for 500 nodes with Leiden
    """
    start_time = time.time()

    # Validate max nodes
    if len(request.gene_ids) > 2000:
        raise ValidationError(
            field="gene_ids",
            reason=f"Maximum 2000 genes allowed, got {len(request.gene_ids)}"
        )

    # Get gene symbols
    genes = db.query(Gene).filter(Gene.id.in_(request.gene_ids)).all()
    gene_id_to_symbol = {g.id: g.approved_symbol for g in genes}

    if not gene_id_to_symbol:
        raise HTTPException(status_code=404, detail="No valid genes found")

    await logger.info(
        "Clustering network",
        gene_count=len(request.gene_ids),
        algorithm=request.algorithm,
        remove_isolated=request.remove_isolated,
        min_degree=request.min_degree,
        min_cluster_size=request.min_cluster_size,
        largest_component_only=request.largest_component_only
    )

    # Build network
    graph = await network_service.build_network_from_string_data(
        gene_ids=request.gene_ids,
        session=db,
        min_string_score=request.min_string_score
    )

    await logger.info(
        "Initial network for clustering",
        nodes=graph.vcount(),
        edges=graph.ecount()
    )

    # Apply node filtering if requested
    if request.min_degree > 0 or request.remove_isolated or request.largest_component_only:
        await logger.info(
            "Applying node filters before clustering",
            min_degree=request.min_degree,
            remove_isolated=request.remove_isolated,
            largest_component_only=request.largest_component_only
        )
        graph = await network_service.filter_network(
            graph=graph,
            session=db,
            min_degree=request.min_degree,
            remove_isolated=request.remove_isolated,
            largest_component_only=request.largest_component_only
        )
        await logger.info(
            "Node filtering complete",
            filtered_nodes=graph.vcount(),
            filtered_edges=graph.ecount()
        )

    # Detect communities
    gene_to_cluster, modularity = await network_service.detect_communities(
        graph=graph,
        session=db,
        algorithm=request.algorithm
    )

    # Apply cluster size filtering if requested
    if request.min_cluster_size > 1:
        await logger.info(
            "Filtering clusters by size",
            original_clusters=len(set(gene_to_cluster.values())),
            min_cluster_size=request.min_cluster_size
        )
        gene_to_cluster = await network_service.filter_clusters_by_size(
            gene_to_cluster=gene_to_cluster,
            session=db,
            min_cluster_size=request.min_cluster_size
        )

        # CRITICAL: Filter graph to only include genes in filtered clusters
        genes_in_clusters = set(gene_to_cluster.keys())
        vertices_to_keep = [
            v.index for v in graph.vs
            if v["gene_id"] in genes_in_clusters
        ]

        if vertices_to_keep:
            graph = graph.subgraph(vertices_to_keep)
            await logger.info(
                "Filtered graph to clustered genes only",
                original_nodes=len(gene_id_to_symbol),
                filtered_nodes=graph.vcount(),
                removed_nodes=len(gene_id_to_symbol) - graph.vcount()
            )
        else:
            await logger.warning("All genes filtered out - returning empty graph")
            graph = ig.Graph()

    # Add cluster IDs to graph vertices
    for vertex in graph.vs:
        gene_id = vertex["gene_id"]
        vertex["cluster_id"] = gene_to_cluster.get(gene_id, -1)

    # Calculate cluster colors
    num_clusters = len(set(gene_to_cluster.values()))
    cluster_colors = generate_cluster_colors(num_clusters)

    # Convert to Cytoscape.js with cluster colors
    cytoscape_json = igraph_to_cytoscape(graph, gene_id_to_symbol, cluster_colors)

    elapsed_ms = (time.time() - start_time) * 1000

    await logger.info(
        "Clustering complete",
        num_clusters=num_clusters,
        modularity=round(modularity, 3),
        algorithm=request.algorithm,
        elapsed_ms=round(elapsed_ms, 2)
    )

    return NetworkClusterResponse(
        clusters=gene_to_cluster,
        num_clusters=num_clusters,
        modularity=round(modularity, 3),
        algorithm=request.algorithm,
        cytoscape_json=cytoscape_json
    )


@router.post("/subgraph", response_model=NetworkBuildResponse)
async def extract_subgraph(
    request: SubgraphRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Extract k-hop neighborhood subgraph around seed genes.

    Useful for focused visualization of genes and their immediate neighbors.
    """
    start_time = time.time()

    # Get gene symbols
    genes = db.query(Gene).filter(Gene.id.in_(request.gene_ids)).all()
    gene_id_to_symbol = {g.id: g.approved_symbol for g in genes}

    await logger.info(
        "Extracting subgraph",
        seed_count=len(request.seed_gene_ids),
        k_hops=request.k
    )

    # Build full network
    full_graph = await network_service.build_network_from_string_data(
        gene_ids=request.gene_ids,
        session=db,
        min_string_score=request.min_string_score
    )

    # Extract k-hop subgraph
    subgraph = await network_service.get_k_hop_subgraph(
        graph=full_graph,
        seed_gene_ids=request.seed_gene_ids,
        session=db,
        k=request.k
    )

    # Convert to Cytoscape.js
    cytoscape_json = igraph_to_cytoscape(subgraph, gene_id_to_symbol)

    elapsed_ms = (time.time() - start_time) * 1000

    await logger.info(
        "Subgraph extracted",
        nodes=subgraph.vcount(),
        edges=subgraph.ecount(),
        elapsed_ms=round(elapsed_ms, 2)
    )

    return NetworkBuildResponse(
        nodes=subgraph.vcount(),
        edges=subgraph.ecount(),
        components=len(subgraph.connected_components()),
        cytoscape_json=cytoscape_json
    )


@router.post("/enrich/hpo", response_model=HPOEnrichmentResponse)
async def enrich_hpo(
    request: HPOEnrichmentRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Perform HPO term enrichment analysis using Fisher's exact test.

    Tests for over-representation of HPO phenotypes in gene cluster
    compared to background. Uses Benjamini-Hochberg FDR correction.
    """
    start_time = time.time()

    await logger.info(
        "Starting HPO enrichment",
        cluster_size=len(request.cluster_genes),
        fdr_threshold=request.fdr_threshold
    )

    # Perform enrichment
    results = await enrichment_service.enrich_hpo_terms(
        cluster_genes=request.cluster_genes,
        session=db,
        background_genes=request.background_genes,
        fdr_threshold=request.fdr_threshold
    )

    elapsed_ms = (time.time() - start_time) * 1000

    await logger.info(
        "HPO enrichment complete",
        significant_terms=len(results),
        elapsed_ms=round(elapsed_ms, 2)
    )

    return HPOEnrichmentResponse(
        results=results,
        total_terms=len(results),
        cluster_size=len(request.cluster_genes),
        fdr_threshold=request.fdr_threshold
    )


@router.post("/enrich/go", response_model=GOEnrichmentResponse)
async def enrich_go(
    request: GOEnrichmentRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Perform GO/KEGG enrichment using GSEApy with Enrichr API.

    IMPORTANT: Enrichr API has rate limits (2s minimum interval).
    Requests may timeout if API is slow (default: 120s timeout).

    Gene sets:
    - GO_Biological_Process_2023
    - GO_Molecular_Function_2023
    - GO_Cellular_Component_2023
    - KEGG_2021_Human
    - Reactome_2022
    - WikiPathway_2023_Human
    """
    start_time = time.time()

    await logger.info(
        "Starting GO enrichment",
        cluster_size=len(request.cluster_genes),
        gene_set=request.gene_set,
        timeout_seconds=request.timeout_seconds
    )

    # Perform enrichment
    results = await enrichment_service.enrich_go_terms(
        cluster_genes=request.cluster_genes,
        session=db,
        gene_set=request.gene_set,
        fdr_threshold=request.fdr_threshold,
        timeout_seconds=request.timeout_seconds
    )

    elapsed_ms = (time.time() - start_time) * 1000

    await logger.info(
        "GO enrichment complete",
        significant_terms=len(results),
        elapsed_ms=round(elapsed_ms, 2)
    )

    return GOEnrichmentResponse(
        results=results,
        total_terms=len(results),
        cluster_size=len(request.cluster_genes),
        gene_set=request.gene_set,
        fdr_threshold=request.fdr_threshold
    )
