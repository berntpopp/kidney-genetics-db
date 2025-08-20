"""Simple data structures without Pydantic dependency."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

@dataclass
class GeneEntry:
    """Gene entry with panel information."""

    symbol: str  # Display symbol (HGNC-approved if available, else reported)
    panels: List[str]
    occurrence_count: int = 1
    confidence: str = "medium"
    hgnc_id: Optional[str] = None
    approved_symbol: Optional[str] = None  # HGNC-approved symbol
    reported_symbol: Optional[str] = None  # Original symbol from provider

    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

@dataclass
class SubPanel:
    """Sub-panel information."""

    name: str
    url: Optional[str] = None
    gene_count: int = 0

    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

@dataclass
class ProviderData:
    """Provider data structure."""

    provider_id: str
    provider_name: str
    provider_type: str
    main_url: str
    total_panels: int
    total_unique_genes: int
    genes: List[GeneEntry]
    sub_panels: Optional[List[SubPanel]] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def model_dump(self) -> dict:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        # Convert gene entries
        data["genes"] = [
            g.model_dump() if hasattr(g, "model_dump") else asdict(g) for g in self.genes
        ]
        if self.sub_panels:
            data["sub_panels"] = [
                p.model_dump() if hasattr(p, "model_dump") else asdict(p)
                for p in self.sub_panels
            ]
        return data

@dataclass
class DiagnosticPanelBatch:
    """Batch of diagnostic panel results from multiple providers."""

    providers: List[ProviderData]
    batch_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_providers: int = field(init=False)
    total_genes: int = field(init=False)
    successful_providers: int = field(init=False)
    failed_providers: int = field(init=False)

    def __post_init__(self):
        """Calculate summary statistics."""
        self.total_providers = len(self.providers)
        self.successful_providers = sum(1 for p in self.providers if not p.errors)
        self.failed_providers = self.total_providers - self.successful_providers

        # Calculate unique genes across all providers
        all_genes = set()
        for provider in self.providers:
            for gene in provider.genes:
                all_genes.add(gene.symbol)
        self.total_genes = len(all_genes)

    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
