"""
Central gene normalization module using HGNC API

This module ensures all genes are properly normalized to HGNC standards
before entering the database. Uses efficient batch processing and comprehensive
fallback strategies based on proven patterns from custom-panel and kidney-genetics-v1.
"""

import asyncio
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.hgnc_client import HGNCClientCached, get_hgnc_client_cached
from app.crud import gene_crud, gene_staging

logger = logging.getLogger(__name__)

# Global HGNC client instance with optimized settings
_hgnc_client = None


def get_hgnc_client() -> HGNCClientCached:
    """Get or create cached HGNC client instance"""
    global _hgnc_client
    if _hgnc_client is None:
        _hgnc_client = get_hgnc_client_cached()
    return _hgnc_client


def clean_gene_text(gene_text: str) -> str:
    """
    Clean and preprocess gene text for HGNC lookup.

    Args:
        gene_text: Raw gene text from data source

    Returns:
        Cleaned gene symbol
    """
    if not gene_text:
        return ""

    # Remove extra whitespace and convert to uppercase
    cleaned = gene_text.strip().upper()

    # Remove common prefixes/suffixes that interfere with HGNC lookup
    cleaned = re.sub(r'^(GENE:|SYMBOL:|PROTEIN:)', '', cleaned)
    cleaned = re.sub(r'(GENE|PROTEIN|_HUMAN)$', '', cleaned)

    # Remove common separators and special characters
    cleaned = re.sub(r'[;,|/\\].*$', '', cleaned)  # Take only first part
    cleaned = re.sub(r'\s*\([^)]*\)', '', cleaned)  # Remove parenthetical content
    cleaned = re.sub(r'[^\w-]', '', cleaned)  # Keep only alphanumeric and hyphens

    return cleaned.strip()


def is_likely_gene_symbol(gene_text: str) -> bool:
    """
    Check if text is likely a valid gene symbol.

    Args:
        gene_text: Cleaned gene text

    Returns:
        True if likely a gene symbol
    """
    if not gene_text or len(gene_text) < 2:
        return False

    # Skip common non-gene terms
    excluded_terms = {
        'UNKNOWN', 'NONE', 'NULL', 'NA', 'GENE', 'PROTEIN', 'CHROMOSOME',
        'COMPLEX', 'FAMILY', 'GROUP', 'CLUSTER', 'REGION', 'LOCUS',
        'ELEMENT', 'SEQUENCE', 'FRAGMENT', 'PARTIAL', 'PUTATIVE'
    }

    if gene_text in excluded_terms:
        return False

    # Skip if too long (likely description rather than symbol)
    if len(gene_text) > 20:
        return False

    # Skip if contains only numbers
    if gene_text.isdigit():
        return False

    return True


def normalize_gene_for_database(
    db: Session,
    gene_text: str,
    source_name: str,
    original_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Normalize a single gene for database insertion.

    Args:
        db: Database session
        gene_text: Raw gene text from data source
        source_name: Name of data source (PubTator, ClinGen, etc.)
        original_data: Original data context for staging

    Returns:
        Dictionary with normalization results:
        {
            "status": "normalized" | "requires_manual_review" | "error",
            "approved_symbol": str | None,
            "hgnc_id": str | None,
            "staging_id": int | None,  # If requires manual review
            "error": str | None
        }
    """
    try:
        # Clean the input
        cleaned_text = clean_gene_text(gene_text)

        if not is_likely_gene_symbol(cleaned_text):
            logger.debug(f"Skipping non-gene text: '{gene_text}' -> '{cleaned_text}'")
            return _create_staging_record(
                db, gene_text, source_name, original_data,
                reason="Not a valid gene symbol format"
            )

        # Check if gene already exists in database
        existing_gene = gene_crud.get_gene_by_symbol(db, cleaned_text)
        if existing_gene and existing_gene.hgnc_id:
            logger.debug(f"Gene '{cleaned_text}' already exists with HGNC ID: {existing_gene.hgnc_id}")
            return {
                "status": "normalized",
                "approved_symbol": existing_gene.approved_symbol,
                "hgnc_id": existing_gene.hgnc_id,
                "staging_id": None,
                "error": None
            }

        # Use HGNC client for normalization
        hgnc_client = get_hgnc_client()
        standardization_result = asyncio.run(hgnc_client.standardize_symbols_batch([cleaned_text]))

        if cleaned_text in standardization_result:
            result = standardization_result[cleaned_text]
            approved_symbol = result.get("approved_symbol")
            hgnc_id = result.get("hgnc_id")

            if approved_symbol and hgnc_id:
                logger.debug(f"Successfully normalized '{gene_text}' -> '{approved_symbol}' ({hgnc_id})")
                return {
                    "status": "normalized",
                    "approved_symbol": approved_symbol,
                    "hgnc_id": hgnc_id,
                    "staging_id": None,
                    "error": None
                }

        # Normalization failed - create staging record
        logger.info(f"Gene '{gene_text}' requires manual review - HGNC lookup failed")
        return _create_staging_record(
            db, gene_text, source_name, original_data,
            reason="HGNC lookup failed - no HGNC ID found"
        )

    except Exception as e:
        logger.error(f"Error normalizing gene '{gene_text}': {e}")
        return {
            "status": "error",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": None,
            "error": str(e)
        }


def normalize_genes_batch(
    db: Session,
    gene_texts: list[str],
    source_name: str,
    original_data_list: list[dict[str, Any]] | None = None
) -> dict[str, dict[str, Any]]:
    """
    Normalize multiple genes efficiently using batch processing.

    Args:
        db: Database session
        gene_texts: List of raw gene texts
        source_name: Name of data source
        original_data_list: List of original data contexts (same length as gene_texts)

    Returns:
        Dictionary mapping original gene_text to normalization results
    """
    if not gene_texts:
        return {}

    logger.info(f"Batch normalizing {len(gene_texts)} genes from {source_name}")

    # Clean and filter gene texts
    cleaned_genes = []
    gene_mapping = {}  # Maps cleaned -> original

    for i, gene_text in enumerate(gene_texts):
        cleaned = clean_gene_text(gene_text)
        if is_likely_gene_symbol(cleaned):
            cleaned_genes.append(cleaned)
            gene_mapping[cleaned] = {
                "original": gene_text,
                "index": i,
                "original_data": original_data_list[i] if original_data_list else None
            }

    logger.info(f"After cleaning: {len(cleaned_genes)} valid gene symbols to normalize")

    if not cleaned_genes:
        return {}

    # Check existing genes in database first
    existing_genes = {}
    for cleaned in cleaned_genes:
        existing_gene = gene_crud.get_gene_by_symbol(db, cleaned)
        if existing_gene and existing_gene.hgnc_id:
            existing_genes[cleaned] = {
                "approved_symbol": existing_gene.approved_symbol,
                "hgnc_id": existing_gene.hgnc_id
            }

    # Get genes that need HGNC lookup
    genes_to_lookup = [g for g in cleaned_genes if g not in existing_genes]
    logger.info(f"Found {len(existing_genes)} existing genes, {len(genes_to_lookup)} need HGNC lookup")

    # Batch HGNC lookup for remaining genes
    hgnc_results = {}
    if genes_to_lookup:
        hgnc_client = get_hgnc_client()
        hgnc_results = asyncio.run(hgnc_client.standardize_symbols_parallel(genes_to_lookup))

    # Compile final results
    results = {}

    for cleaned in cleaned_genes:
        mapping = gene_mapping[cleaned]
        original_text = mapping["original"]
        original_data = mapping["original_data"]

        if cleaned in existing_genes:
            # Use existing gene data
            gene_data = existing_genes[cleaned]
            results[original_text] = {
                "status": "normalized",
                "approved_symbol": gene_data["approved_symbol"],
                "hgnc_id": gene_data["hgnc_id"],
                "staging_id": None,
                "error": None
            }
        elif cleaned in hgnc_results:
            # Use HGNC lookup result
            hgnc_result = hgnc_results[cleaned]
            approved_symbol = hgnc_result.get("approved_symbol")
            hgnc_id = hgnc_result.get("hgnc_id")

            if approved_symbol and hgnc_id:
                results[original_text] = {
                    "status": "normalized",
                    "approved_symbol": approved_symbol,
                    "hgnc_id": hgnc_id,
                    "staging_id": None,
                    "error": None
                }
            else:
                # Failed normalization - create staging record
                results[original_text] = _create_staging_record(
                    db, original_text, source_name, original_data,
                    reason="HGNC batch lookup failed - no HGNC ID found"
                )
        else:
            # Shouldn't happen, but handle gracefully
            results[original_text] = _create_staging_record(
                db, original_text, source_name, original_data,
                reason="Unexpected error in batch processing"
            )

    # Log summary
    normalized_count = sum(1 for r in results.values() if r["status"] == "normalized")
    staging_count = sum(1 for r in results.values() if r["status"] == "requires_manual_review")
    error_count = sum(1 for r in results.values() if r["status"] == "error")

    logger.info(
        f"Batch normalization complete: {normalized_count} normalized, "
        f"{staging_count} staged for review, {error_count} errors"
    )

    return results


def _create_staging_record(
    db: Session,
    gene_text: str,
    source_name: str,
    original_data: dict[str, Any] | None,
    reason: str
) -> dict[str, Any]:
    """Create a staging record for manual review"""
    try:
        staging_record = gene_staging.create_staging_record(
            db=db,
            original_text=gene_text,
            source_name=source_name,
            original_data=original_data or {},
            normalization_log={"failure_reason": reason, "attempts": 1}
        )

        logger.debug(f"Created staging record {staging_record.id} for gene '{gene_text}'")

        return {
            "status": "requires_manual_review",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": staging_record.id,
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to create staging record for '{gene_text}': {e}")
        return {
            "status": "error",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": None,
            "error": f"Staging creation failed: {e}"
        }


def get_normalization_stats(db: Session) -> dict[str, Any]:
    """Get statistics about gene normalization"""
    try:
        # Gene statistics
        total_genes = gene_crud.count(db)
        genes_with_hgnc = gene_crud.count(db)  # TODO: Implement proper HGNC count

        # Staging statistics
        staging_stats = gene_staging.get_staging_stats(db)

        return {
            "total_genes": total_genes,
            "genes_with_hgnc_id": genes_with_hgnc,
            "genes_without_hgnc_id": total_genes - genes_with_hgnc,
            "normalization_coverage": (genes_with_hgnc / total_genes * 100) if total_genes > 0 else 0,
            "staging_records": {
                "pending": staging_stats.get("pending", 0),
                "approved": staging_stats.get("approved", 0),
                "rejected": staging_stats.get("rejected", 0),
                "total": staging_stats.get("total", 0)
            },
            "hgnc_cache_info": asyncio.run(get_hgnc_client().get_cache_stats())
        }
    except Exception as e:
        logger.error(f"Error getting normalization stats: {e}")
        return {"error": str(e)}


def clear_normalization_cache():
    """Clear HGNC client cache"""
    asyncio.run(get_hgnc_client().clear_cache())
    logger.info("HGNC normalization cache cleared")
