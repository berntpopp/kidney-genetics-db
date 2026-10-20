"""
Pydantic schemas for network analysis and enrichment
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.datasource_config import get_config

# Load network analysis configuration
_config = get_config()
_na_config = _config.network_analysis
_enrichment_config = _config.enrichment
_filtering_config = _na_config.get("filtering", {})
_network_config = _na_config.get("network", {})


class NetworkBuildRequest(BaseModel):
    """Request to build a PPI network"""

    gene_ids: list[int] = Field(
        ...,
        description="List of gene IDs to include in network",
        min_length=1,
        max_length=_network_config.get("max_nodes", 2000),
    )
    min_string_score: int = Field(
        default=_network_config.get("min_string_score", 400),
        ge=0,
        le=1000,
        description="Minimum STRING confidence score (0-1000)",
    )
    min_degree: int = Field(
        default=_filtering_config.get("default_min_degree", 0),
        ge=0,
        le=_filtering_config.get("max_min_degree", 10),
        description="Minimum node degree (0=include all, 1=remove isolated, 2+=require multiple interactions)",
    )
    remove_isolated: bool = Field(
        default=_filtering_config.get("default_remove_isolated", False),
        description="Remove nodes with no interactions (degree=0)",
    )
    largest_component_only: bool = Field(
        default=_filtering_config.get("default_largest_component_only", False),
        description="Keep only largest connected component",
    )

    @field_validator("gene_ids")
    @classmethod
    def validate_and_normalize_gene_ids(cls, v: list[int]) -> list[int]:
        """Validate gene IDs and normalize to sorted order for cache consistency"""
        if not all(gid > 0 for gid in v):
            raise ValueError("All gene IDs must be positive integers")
        return sorted(v)  # Ensures deterministic cache keys


class NetworkClusterRequest(BaseModel):
    """Request to cluster a network"""

    gene_ids: list[int] = Field(
        ...,
        description="List of gene IDs in network",
        min_length=1,
        max_length=_network_config.get("max_nodes", 2000),
    )
    min_string_score: int = Field(
        default=_network_config.get("min_string_score", 400),
        ge=0,
        le=1000,
        description="Minimum STRING confidence score (0-1000)",
    )
    algorithm: str = Field(
        default=_na_config.get("clustering", {}).get("default_algorithm", "leiden"),
        description="Clustering algorithm: leiden, louvain, or walktrap",
    )
    seed: int = Field(
        default=0,
        ge=0,
        le=2**31 - 1,
        description="RNG seed for leiden/louvain; the fixed default makes default runs reproducible",
    )
    min_degree: int = Field(
        default=_filtering_config.get("default_min_degree", 0),
        ge=0,
        le=_filtering_config.get("max_min_degree", 10),
        description="Minimum node degree filter",
    )
    remove_isolated: bool = Field(
        default=_filtering_config.get("default_remove_isolated", False),
        description="Remove isolated nodes (degree=0)",
    )
    min_cluster_size: int = Field(
        default=_filtering_config.get("default_min_cluster_size", 1),
        ge=1,
        le=_filtering_config.get("max_min_cluster_size", 50),
        description="Minimum cluster size (1=keep all, 3+=filter small clusters)",
    )
    largest_component_only: bool = Field(
        default=_filtering_config.get("default_largest_component_only", False),
        description="Keep only largest connected component",
    )

    @field_validator("gene_ids")
    @classmethod
    def validate_and_normalize_gene_ids(cls, v: list[int]) -> list[int]:
        """Validate gene IDs and normalize to sorted order for cache consistency"""
        if not all(gid > 0 for gid in v):
            raise ValueError("All gene IDs must be positive integers")
        return sorted(v)  # Ensures deterministic cache keys

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate clustering algorithm"""
        valid_algorithms = ["leiden", "louvain", "walktrap"]
        if v not in valid_algorithms:
            raise ValueError(f"Algorithm must be one of {valid_algorithms}, got '{v}'")
        return v


class SubgraphRequest(BaseModel):
    """Request to extract k-hop subgraph"""

    seed_gene_ids: list[int] = Field(
        ...,
        description="Seed gene IDs to center subgraph around",
        min_length=1,
        max_length=_na_config.get("subgraph", {}).get("max_seed_genes", 50),
    )
    gene_ids: list[int] = Field(
        ...,
        description="Full network gene IDs",
        min_length=1,
        max_length=_network_config.get("max_nodes", 2000),
    )
    min_string_score: int = Field(
        default=_network_config.get("min_string_score", 400),
        ge=0,
        le=1000,
        description="Minimum STRING confidence score",
    )
    k: int = Field(
        default=_na_config.get("subgraph", {}).get("default_k_hops", 2),
        ge=1,
        le=_na_config.get("subgraph", {}).get("max_k_hops", 5),
        description="Number of hops (1-5)",
    )

    @field_validator("seed_gene_ids", "gene_ids")
    @classmethod
    def validate_and_normalize_gene_ids(cls, v: list[int]) -> list[int]:
        """Validate gene IDs and normalize to sorted order for cache consistency"""
        if not all(gid > 0 for gid in v):
            raise ValueError("All gene IDs must be positive integers")
        return sorted(v)  # Ensures deterministic cache keys


class HPOEnrichmentRequest(BaseModel):
    """Request for HPO term enrichment"""

    cluster_genes: list[int] = Field(
        ...,
        description="Gene IDs in cluster to test",
        min_length=1,
        max_length=_enrichment_config.get("hpo", {}).get("max_cluster_size", 2000),
    )
    background_genes: list[int] | None = Field(
        default=None,
        description=(
            "Background gene IDs; the tested universe is these genes that have kidney "
            "HPO annotations (default: all genes with kidney HPO annotations)"
        ),
        max_length=_enrichment_config.get("hpo", {}).get("max_background_size", 50000),
    )
    fdr_threshold: float = Field(
        default=_enrichment_config.get("hpo", {}).get("default_fdr_threshold", 0.05),
        gt=0.0,
        le=1.0,
        description="FDR significance threshold",
    )


class HPOBatchEnrichmentRequest(BaseModel):
    """Request for HPO enrichment of several communities with pooled FDR (#332)"""

    communities: list[list[int]] = Field(
        ...,
        description=(
            "Gene IDs per community; BH-FDR is pooled over all community x term pairs "
            "with at least one overlapping community gene (the single-community family). "
            f"At most {_enrichment_config.get('hpo', {}).get('max_communities', 200)} communities."
        ),
        min_length=1,
        max_length=_enrichment_config.get("hpo", {}).get("max_communities", 200),
    )
    fdr_threshold: float = Field(
        default=_enrichment_config.get("hpo", {}).get("default_fdr_threshold", 0.05),
        gt=0.0,
        le=1.0,
        description="FDR significance threshold (applied to pooled q-values)",
    )

    @field_validator("communities")
    @classmethod
    def validate_communities(cls, v: list[list[int]]) -> list[list[int]]:
        """Bound each community like a single HPO request and the total like a network"""
        max_cluster = _enrichment_config.get("hpo", {}).get("max_cluster_size", 2000)
        max_total = _network_config.get("max_nodes", 2000)
        if any(not 1 <= len(c) <= max_cluster for c in v):
            raise ValueError(f"Each community must have 1-{max_cluster} gene IDs")
        if sum(len(c) for c in v) > max_total:
            raise ValueError(f"At most {max_total} gene IDs across all communities")
        if not all(gid > 0 for c in v for gid in c):
            raise ValueError("All gene IDs must be positive integers")
        return [sorted(c) for c in v]  # Ensures deterministic cache keys


class GOEnrichmentRequest(BaseModel):
    """Request for GO/KEGG enrichment via GSEApy"""

    cluster_genes: list[int] = Field(
        ...,
        description="Gene IDs in cluster",
        min_length=1,
        max_length=_enrichment_config.get("go", {}).get("max_cluster_size", 2000),
    )
    gene_set: str = Field(
        default=_enrichment_config.get("go", {}).get(
            "default_gene_set", "GO_Biological_Process_2023"
        ),
        description="GSEApy gene set name",
    )
    fdr_threshold: float = Field(
        default=_enrichment_config.get("go", {}).get("default_fdr_threshold", 0.05),
        gt=0.0,
        le=1.0,
        description="FDR significance threshold",
    )
    timeout_seconds: int = Field(
        default=_enrichment_config.get("go", {}).get("timeout_seconds", 120),
        ge=_enrichment_config.get("go", {}).get("min_timeout_seconds", 30),
        le=_enrichment_config.get("go", {}).get("max_timeout_seconds", 300),
        description="API timeout (30-300 seconds)",
    )

    @field_validator("gene_set")
    @classmethod
    def validate_gene_set(cls, v: str) -> str:
        """Validate gene set name"""
        valid_sets = [
            "GO_Biological_Process_2023",
            "GO_Molecular_Function_2023",
            "GO_Cellular_Component_2023",
            "KEGG_2021_Human",
            "Reactome_2022",
            "WikiPathway_2023_Human",
        ]
        if v not in valid_sets:
            raise ValueError(f"gene_set must be one of {valid_sets}, got '{v}'")
        return v


class NetworkBuildResponse(BaseModel):
    """Response from network build"""

    nodes: int = Field(..., description="Number of nodes")
    edges: int = Field(..., description="Number of edges")
    components: int = Field(..., description="Number of connected components")
    cytoscape_json: dict[str, Any] = Field(..., description="Cytoscape.js format")


class NetworkClusterResponse(BaseModel):
    """Response from network clustering"""

    nodes: int = Field(..., description="Number of nodes in clustered network")
    edges: int = Field(..., description="Number of edges in clustered network")
    components: int = Field(..., description="Number of connected components")
    clusters: dict[int, int] = Field(..., description="Gene ID -> cluster ID mapping")
    num_clusters: int = Field(..., description="Number of clusters detected")
    modularity: float = Field(..., description="Modularity score")
    algorithm: str = Field(..., description="Algorithm used")
    parameters: dict[str, Any] = Field(
        ...,
        description="Clustering parameters used, e.g. objective, resolution, iterations, seed",
    )
    cytoscape_json: dict[str, Any] = Field(..., description="Cytoscape.js with cluster colors")


class EnrichmentResult(BaseModel):
    """Single enrichment result"""

    term_id: str
    term_name: str
    p_value: float
    fdr: float
    gene_count: int
    cluster_size: int
    background_count: int | None = None
    genes: list[str]
    enrichment_score: float
    odds_ratio: float


class HPOEnrichmentResponse(BaseModel):
    """Response from HPO enrichment"""

    results: list[EnrichmentResult]
    total_terms: int = Field(..., description="Total significant terms")
    cluster_size: int = Field(..., description="Cluster gene count")
    fdr_threshold: float
    excluded_genes: list[int] = Field(
        default_factory=list,
        description=(
            "Submitted gene IDs not tested: outside the universe of kidney HPO-annotated genes "
            "(intersected with background_genes when given) or unknown"
        ),
    )


class GOEnrichmentResponse(BaseModel):
    """Response from GO/KEGG enrichment"""

    results: list[EnrichmentResult]
    total_terms: int = Field(..., description="Total significant terms")
    cluster_size: int = Field(..., description="Cluster gene count")
    gene_set: str = Field(..., description="Gene set used")
    fdr_threshold: float


class HPOClassificationRequest(BaseModel):
    """Request to fetch HPO classifications for genes"""

    gene_ids: list[int] = Field(
        ...,
        description="List of gene IDs to fetch HPO classifications for",
        min_length=1,
        max_length=1000,
    )

    @field_validator("gene_ids")
    @classmethod
    def validate_gene_ids(cls, v: list[int]) -> list[int]:
        """Validate gene IDs are positive integers"""
        if not all(gid > 0 for gid in v):
            raise ValueError("All gene IDs must be positive integers")
        return v


class HPOClassificationData(BaseModel):
    """HPO classification data for a single gene"""

    gene_id: int = Field(..., description="Gene ID")
    gene_symbol: str = Field(..., description="Gene symbol")
    clinical_group: str | None = Field(None, description="Clinical classification group")
    onset_group: str | None = Field(None, description="Age of onset group")
    is_syndromic: bool | None = Field(
        None, description="Syndromic assessment; null when the gene has not been assessed"
    )


class HPOClassificationResponse(BaseModel):
    """Response with HPO classifications for genes"""

    data: list[HPOClassificationData] = Field(..., description="HPO classification data")
    metadata: dict[str, Any] = Field(..., description="Response metadata")


class HPOBatchEnrichmentResponse(BaseModel):
    """Response from batch HPO enrichment with pooled FDR"""

    results: list[list[EnrichmentResult]] = Field(
        ..., description="Significant terms per community, in submitted order"
    )
    total_tests: int = Field(
        ...,
        description=(
            "Community x term pairs with at least one overlapping community gene, "
            "i.e. the tests in the pooled BH correction (zero-overlap pairs are not tested)"
        ),
    )
    fdr_threshold: float
    excluded_genes: list[list[int]] = Field(
        default_factory=list,
        description=(
            "Per community, submitted gene IDs not tested: without kidney HPO annotation or unknown"
        ),
    )
