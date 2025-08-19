"""Shared utilities for diagnostic panel scrapers."""

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=10000)
def resolve_hgnc_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Resolve a gene symbol to HGNC data.

    Args:
        symbol: Gene symbol to resolve

    Returns:
        Dict with hgnc_id and approved_symbol, or None if not found
    """
    try:
        # For now, we'll return the symbol as-is
        # In production, this would query HGNC API or database
        return {"hgnc_id": None, "approved_symbol": symbol.upper()}
    except Exception as e:
        logger.error(f"Error resolving HGNC symbol {symbol}: {e}")
        return None


def clean_gene_symbol(symbol: str) -> str:
    """Clean a gene symbol by removing special characters and annotations.

    Args:
        symbol: Raw gene symbol from source

    Returns:
        Cleaned gene symbol
    """
    # Remove common annotations
    symbol = re.sub(r"\[.*?\]", "", symbol)  # Remove bracketed content
    symbol = re.sub(r"\(.*?\)", "", symbol)  # Remove parenthetical content
    symbol = symbol.replace("*", "").replace("#", "").replace(".", "")
    symbol = symbol.strip()

    # Remove common suffixes/prefixes
    if symbol.endswith("-AS1"):
        symbol = symbol[:-4]

    # Validate basic gene symbol format
    if not re.match(r"^[A-Z][A-Z0-9]{1,}[A-Z0-9]*$", symbol):
        return ""

    return symbol


def calculate_confidence(gene_count: int, source_type: str) -> str:
    """Calculate confidence score for gene data.

    Args:
        gene_count: Number of genes found
        source_type: Type of source (e.g., 'commercial', 'academic')

    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    if gene_count > 100 and source_type in ["commercial", "academic"]:
        return "high"
    elif gene_count > 50:
        return "medium"
    else:
        return "low"


def normalize_panel_name(name: str) -> str:
    """Normalize panel name for consistency.

    Args:
        name: Raw panel name

    Returns:
        Normalized panel name
    """
    # Remove extra whitespace
    name = " ".join(name.split())

    # Standardize common terms
    replacements = {
        "NGS": "Next Generation Sequencing",
        "WES": "Whole Exome Sequencing",
        "WGS": "Whole Genome Sequencing",
        "&": "and",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name.strip()


def validate_gene_list(genes: list) -> tuple[list, list]:
    """Validate a list of gene symbols.

    Args:
        genes: List of gene symbols to validate

    Returns:
        Tuple of (valid_genes, invalid_genes)
    """
    valid_genes = []
    invalid_genes = []

    for gene in genes:
        if gene and 2 <= len(gene) <= 15:
            if re.match(r"^[A-Z][A-Z0-9]{1,}[A-Z0-9]*$", gene):
                valid_genes.append(gene)
            else:
                invalid_genes.append(gene)
        else:
            invalid_genes.append(gene)

    return valid_genes, invalid_genes