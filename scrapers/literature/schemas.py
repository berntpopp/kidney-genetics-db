"""Data structures for literature scraping matching diagnostic scraper schemas."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GeneEntry:
    """Gene entry with publication information."""

    symbol: str  # Display symbol (HGNC-approved if available, else reported)
    panels: List[str]  # In literature context, these are PMIDs
    occurrence_count: int = 1
    confidence: str = "medium"
    hgnc_id: Optional[str] = None
    approved_symbol: Optional[str] = None  # HGNC-approved symbol
    reported_symbol: Optional[str] = None  # Original symbol from publication

    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Publication:
    """Publication information."""

    pmid: str
    name: str
    authors: str
    publication_date: str
    file_type: str
    gene_count: int = 0
    extraction_method: Optional[str] = None

    def model_dump(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LiteratureData:
    """Literature data structure matching ProviderData schema."""

    provider_id: str = "literature"
    provider_name: str = "Literature Sources"
    provider_type: str = "literature"
    main_url: str = "kidney_genetics_publications"
    total_panels: int = 0  # Total publications
    total_unique_genes: int = 0
    genes: List[GeneEntry] = field(default_factory=list)
    publications: Optional[List[Publication]] = None
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
        if self.publications:
            data["publications"] = [
                p.model_dump() if hasattr(p, "model_dump") else asdict(p) for p in self.publications
            ]
        return data
