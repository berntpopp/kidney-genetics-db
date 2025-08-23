"""
Statistics API schemas
"""

from typing import Any

from pydantic import BaseModel


class SourceSet(BaseModel):
    """Individual data source for UpSet plot"""

    name: str
    size: int


class SourceIntersection(BaseModel):
    """Intersection between multiple data sources"""

    sets: list[str]
    size: int
    genes: list[str]


class OverlapStatistics(BaseModel):
    """Summary statistics for source overlaps"""

    highest_overlap_count: int
    genes_in_all_sources: int
    single_source_combinations: int
    total_combinations: int


class SourceOverlapResponse(BaseModel):
    """Response schema for source overlap analysis"""

    sets: list[SourceSet]
    intersections: list[SourceIntersection]
    total_unique_genes: int
    overlap_statistics: OverlapStatistics


class DistributionPoint(BaseModel):
    """Single point in a distribution chart"""

    source_count: int
    gene_count: int


class DistributionMetadata(BaseModel):
    """Metadata for distribution analysis"""

    # Use flexible dict to accommodate different source types
    metadata: dict[str, Any] = {}


class SourceDistribution(BaseModel):
    """Distribution data for a single source"""

    distribution: list[DistributionPoint]
    metadata: dict[str, Any]


class SourceDistributionResponse(BaseModel):
    """Response schema for source distribution analysis"""

    # Dynamic keys based on available sources
    __root__: dict[str, SourceDistribution]


class EvidenceQualityPoint(BaseModel):
    """Single point in evidence quality distribution"""

    score_range: str
    gene_count: int
    label: str


class SourceCoveragePoint(BaseModel):
    """Single point in source coverage distribution"""

    source_count: int
    gene_count: int
    percentage: float


class CompositionSummary(BaseModel):
    """Summary statistics for evidence composition"""

    total_genes: int
    total_evidence_records: int
    active_sources: int
    avg_sources_per_gene: float


class EvidenceCompositionResponse(BaseModel):
    """Response schema for evidence composition analysis"""

    evidence_quality_distribution: list[EvidenceQualityPoint]
    source_contribution_weights: dict[str, float]
    source_coverage_distribution: list[SourceCoveragePoint]
    summary_statistics: CompositionSummary


class TopGeneOverlap(BaseModel):
    """Top gene by source overlap"""

    gene_id: int
    approved_symbol: str
    source_count: int
    evidence_count: int
    percentage_score: float
    hgnc_id: str
    sources: list[str]


class TopGenesOverlapResponse(BaseModel):
    """Response schema for top genes by overlap"""

    genes: list[TopGeneOverlap]
    limit: int
    total_genes_analyzed: int


class StatisticsMetadata(BaseModel):
    """Common metadata for statistics responses"""

    generated_at: str
    data_version: str | None = None
    query_duration_ms: float | None = None
