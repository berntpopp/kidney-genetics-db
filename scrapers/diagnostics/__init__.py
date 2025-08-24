"""
Diagnostic panel scraping module.
"""

from .base_scraper import BaseDiagnosticScraper as BaseDiagnosticScraper
from .schemas import DiagnosticPanelBatch as DiagnosticPanelBatch
from .schemas import GeneEntry as GeneEntry
from .schemas import ProviderData as ProviderData
from .schemas import SubPanel as SubPanel
from .utils import clean_gene_symbol as clean_gene_symbol
from .utils import resolve_hgnc_symbol as resolve_hgnc_symbol

__version__ = "1.0.0"

__all__ = [
    "BaseDiagnosticScraper",
    "DiagnosticPanelBatch",
    "GeneEntry",
    "ProviderData",
    "SubPanel",
    "clean_gene_symbol",
    "resolve_hgnc_symbol",
]
