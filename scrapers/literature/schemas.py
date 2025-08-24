"""Data structures for literature gene extraction."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LiteratureGene:
    """Gene extracted from a publication."""
    
    symbol: str  # HGNC-approved symbol (or reported if not found)
    reported_as: str  # Original symbol as it appeared in the publication
    hgnc_id: Optional[str] = None
    normalization_status: str = "normalized"  # "normalized", "not_found", "unchanged"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass 
class LiteraturePublication:
    """A single literature publication with extracted genes."""
    
    id: str  # Same as PMID for consistency
    pmid: str
    title: str
    authors: List[str]  # List of author names
    journal: str
    publication_date: str  # ISO format date
    url: Optional[str] = None
    doi: Optional[str] = None
    
    # Gene data
    genes: List[LiteratureGene] = field(default_factory=list)
    gene_count: int = 0
    
    # Extraction metadata
    source_file: str = ""
    file_type: str = ""  # pdf, docx, xlsx, etc.
    extraction_method: str = ""  # Which processor was used
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    extraction_errors: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        # Ensure genes are properly serialized
        data["genes"] = [g.to_dict() if hasattr(g, "to_dict") else asdict(g) for g in self.genes]
        # Convert datetime fields to strings
        if isinstance(data.get("extraction_timestamp"), datetime):
            data["extraction_timestamp"] = data["extraction_timestamp"].isoformat()
        if isinstance(data.get("publication_date"), datetime):
            data["publication_date"] = data["publication_date"].isoformat()
        return data
    
    @property
    def unique_genes(self) -> int:
        """Count of unique gene symbols."""
        return len(set(g.symbol for g in self.genes))


@dataclass
class LiteratureSummary:
    """Summary of all processed literature."""
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_publications: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    total_unique_genes: int = 0
    
    publications: List[Dict[str, Any]] = field(default_factory=list)  # Summary info for each pub
    extraction_errors: Optional[List[Dict[str, str]]] = None  # PMIDs that failed with reasons
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


# For backward compatibility during transition
@dataclass
class GeneEntry:
    """Legacy gene entry - to be removed after refactoring."""
    symbol: str
    panels: List[str]
    occurrence_count: int = 1
    hgnc_id: Optional[str] = None
    approved_symbol: Optional[str] = None
    reported_symbol: Optional[str] = None
    
    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class Publication:
    """Legacy publication - to be removed after refactoring."""
    pmid: str
    name: str
    authors: str
    publication_date: str
    file_type: str
    gene_count: int = 0
    extraction_method: Optional[str] = None
    
    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class LiteratureData:
    """Legacy data structure - to be removed after refactoring."""
    provider_id: str = "literature"
    provider_name: str = "Literature Sources"
    provider_type: str = "literature"
    main_url: str = "kidney_genetics_publications"
    total_panels: int = 0
    total_unique_genes: int = 0
    genes: List[GeneEntry] = field(default_factory=list)
    publications: Optional[List[Publication]] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def model_dump(self) -> dict:
        data = asdict(self)
        data["genes"] = [
            g.model_dump() if hasattr(g, "model_dump") else asdict(g) for g in self.genes
        ]
        if self.publications:
            data["publications"] = [
                p.model_dump() if hasattr(p, "model_dump") else asdict(p) for p in self.publications
            ]
        return data