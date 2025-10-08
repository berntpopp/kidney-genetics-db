"""
Pydantic schemas for network analysis and enrichment
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class NetworkBuildRequest(BaseModel):
    """Request to build a PPI network"""

    gene_ids: list[int] = Field(
        ...,
        description="List of gene IDs to include in network",
        min_length=1,
        max_length=2000
    )
    min_string_score: int = Field(
        default=400,
        ge=0,
        le=1000,
        description="Minimum STRING confidence score (0-1000)"
    )

    @field_validator('gene_ids')
    @classmethod
    def validate_gene_ids(cls, v: list[int]) -> list[int]:
        """Validate gene IDs are positive integers"""
        if not all(gid > 0 for gid in v):
            raise ValueError("All gene IDs must be positive integers")
        return v


class NetworkClusterRequest(BaseModel):
    """Request to cluster a network"""

    gene_ids: list[int] = Field(
        ...,
        description="List of gene IDs in network",
        min_length=1,
        max_length=2000
    )
    min_string_score: int = Field(
        default=400,
        ge=0,
        le=1000,
        description="Minimum STRING confidence score (0-1000)"
    )
    algorithm: str = Field(
        default="leiden",
        description="Clustering algorithm: leiden, louvain, or walktrap"
    )

    @field_validator('algorithm')
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate clustering algorithm"""
        valid_algorithms = ['leiden', 'louvain', 'walktrap']
        if v not in valid_algorithms:
            raise ValueError(
                f"Algorithm must be one of {valid_algorithms}, got '{v}'"
            )
        return v


class SubgraphRequest(BaseModel):
    """Request to extract k-hop subgraph"""

    seed_gene_ids: list[int] = Field(
        ...,
        description="Seed gene IDs to center subgraph around",
        min_length=1,
        max_length=50
    )
    gene_ids: list[int] = Field(
        ...,
        description="Full network gene IDs",
        min_length=1,
        max_length=2000
    )
    min_string_score: int = Field(
        default=400,
        ge=0,
        le=1000,
        description="Minimum STRING confidence score"
    )
    k: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Number of hops (1-5)"
    )


class HPOEnrichmentRequest(BaseModel):
    """Request for HPO term enrichment"""

    cluster_genes: list[int] = Field(
        ...,
        description="Gene IDs in cluster to test",
        min_length=1,
        max_length=500
    )
    background_genes: list[int] | None = Field(
        default=None,
        description="Background gene set (default: all genes)"
    )
    fdr_threshold: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="FDR significance threshold"
    )


class GOEnrichmentRequest(BaseModel):
    """Request for GO/KEGG enrichment via GSEApy"""

    cluster_genes: list[int] = Field(
        ...,
        description="Gene IDs in cluster",
        min_length=1,
        max_length=500
    )
    gene_set: str = Field(
        default="GO_Biological_Process_2023",
        description="GSEApy gene set name"
    )
    fdr_threshold: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        description="FDR significance threshold"
    )
    timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=300,
        description="API timeout (30-300 seconds)"
    )

    @field_validator('gene_set')
    @classmethod
    def validate_gene_set(cls, v: str) -> str:
        """Validate gene set name"""
        valid_sets = [
            'GO_Biological_Process_2023',
            'GO_Molecular_Function_2023',
            'GO_Cellular_Component_2023',
            'KEGG_2021_Human',
            'Reactome_2022',
            'WikiPathway_2023_Human'
        ]
        if v not in valid_sets:
            raise ValueError(
                f"gene_set must be one of {valid_sets}, got '{v}'"
            )
        return v


class NetworkBuildResponse(BaseModel):
    """Response from network build"""

    nodes: int = Field(..., description="Number of nodes")
    edges: int = Field(..., description="Number of edges")
    components: int = Field(..., description="Number of connected components")
    cytoscape_json: dict[str, Any] = Field(..., description="Cytoscape.js format")


class NetworkClusterResponse(BaseModel):
    """Response from network clustering"""

    clusters: dict[int, int] = Field(..., description="Gene ID -> cluster ID mapping")
    num_clusters: int = Field(..., description="Number of clusters detected")
    modularity: float = Field(..., description="Modularity score")
    algorithm: str = Field(..., description="Algorithm used")
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


class GOEnrichmentResponse(BaseModel):
    """Response from GO/KEGG enrichment"""

    results: list[EnrichmentResult]
    total_terms: int = Field(..., description="Total significant terms")
    cluster_size: int = Field(..., description="Cluster gene count")
    gene_set: str = Field(..., description="Gene set used")
    fdr_threshold: float
