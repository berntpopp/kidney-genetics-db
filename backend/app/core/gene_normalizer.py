"""
Unified async-first gene normalization service.

This module provides the single source of truth for gene normalization,
replacing the duplicated sync/async implementations with a clean async-first design.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.hgnc_client import get_hgnc_client_cached
from app.core.logging import get_logger
from app.crud import gene_crud, gene_staging

logger = get_logger(__name__)


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

    import re

    # Remove extra whitespace and convert to uppercase
    cleaned = gene_text.strip().upper()

    # Remove common prefixes/suffixes that interfere with HGNC lookup
    cleaned = re.sub(r"^(GENE:|SYMBOL:|PROTEIN:)", "", cleaned)
    cleaned = re.sub(r"(GENE|PROTEIN|_HUMAN)$", "", cleaned)

    # Remove common separators and special characters
    cleaned = re.sub(r"[;,|/\\].*$", "", cleaned)  # Take only first part
    cleaned = re.sub(r"\s*\([^)]*\)", "", cleaned)  # Remove parenthetical content
    cleaned = re.sub(r"[^\w-]", "", cleaned)  # Keep only alphanumeric and hyphens

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
        "UNKNOWN",
        "NONE",
        "NULL",
        "NA",
        "GENE",
        "PROTEIN",
        "CHROMOSOME",
        "COMPLEX",
        "FAMILY",
        "GROUP",
        "CLUSTER",
        "REGION",
        "LOCUS",
        "ELEMENT",
        "SEQUENCE",
        "FRAGMENT",
        "PARTIAL",
        "PUTATIVE",
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


class GeneNormalizer:
    """Unified async-first gene normalization service."""

    def __init__(self, db_session: Session | None = None):
        self.hgnc_client = get_hgnc_client_cached(db_session=db_session)

    async def normalize_batch_async(
        self,
        db: Session,
        gene_texts: list[str],
        source_name: str,
        original_data_list: list[dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Async batch normalization of gene symbols."""
        if not gene_texts:
            return {}

        logger.sync_info("Normalizing gene texts", source_name=source_name, count=len(gene_texts))

        # Clean and prepare
        cleaned_genes = []
        gene_mapping = {}

        for i, gene_text in enumerate(gene_texts):
            if not gene_text:
                continue

            cleaned = clean_gene_text(gene_text)
            if cleaned and is_likely_gene_symbol(cleaned):
                cleaned_genes.append(cleaned)
                gene_mapping[cleaned] = {
                    "original": gene_text,
                    "index": i,
                    "original_data": original_data_list[i] if original_data_list else None,
                }

        if not cleaned_genes:
            return {}

        # Check existing genes in database
        existing_genes = self._get_existing_genes(db, cleaned_genes)

        # HGNC lookup for remaining genes
        genes_to_lookup = [g for g in cleaned_genes if g not in existing_genes]
        hgnc_results = {}

        if genes_to_lookup:
            hgnc_results = await self.hgnc_client.standardize_symbols_parallel(genes_to_lookup)

        # Compile results
        return self._compile_results(gene_mapping, existing_genes, hgnc_results, db, source_name)

    def _get_existing_genes(self, db: Session, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get existing genes from database."""
        existing_genes = {}
        for symbol in symbols:
            existing_gene = gene_crud.get_gene_by_symbol(db, symbol)
            if existing_gene and existing_gene.hgnc_id:
                existing_genes[symbol] = {
                    "approved_symbol": existing_gene.approved_symbol,
                    "hgnc_id": existing_gene.hgnc_id,
                    "gene_id": existing_gene.id,  # Include gene_id for efficiency
                }
        return existing_genes

    def _compile_results(
        self,
        gene_mapping: dict[str, dict[str, Any]],
        existing_genes: dict[str, dict[str, Any]],
        hgnc_results: dict[str, dict[str, Any]],
        db: Session,
        source_name: str,
    ) -> dict[str, dict[str, Any]]:
        """Compile final normalization results."""
        results = {}

        for cleaned in gene_mapping:
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
                    "gene_id": gene_data.get("gene_id"),  # Include gene_id
                    "staging_id": None,
                    "error": None,
                    "source": "database",
                    "original_data": original_data,
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
                        "error": None,
                        "source": "hgnc",
                        "original_data": original_data,
                    }
                else:
                    # Failed normalization - create staging record
                    results[original_text] = self._create_staging_record(
                        db,
                        original_text,
                        source_name,
                        original_data,
                        reason="HGNC lookup failed - no HGNC ID found",
                    )
            else:
                # Shouldn't happen, but handle gracefully
                results[original_text] = self._create_staging_record(
                    db,
                    original_text,
                    source_name,
                    original_data,
                    reason="Unexpected error in batch processing",
                )

        # Log summary
        status_counts = {}
        for info in results.values():
            status = info.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.sync_info(
            "Normalization complete",
            source_name=source_name,
            normalized=status_counts.get("normalized", 0),
            staged_for_review=status_counts.get("requires_manual_review", 0),
            errors=status_counts.get("error", 0),
        )

        return results

    def _create_staging_record(
        self,
        db: Session,
        gene_text: str,
        source_name: str,
        original_data: dict[str, Any] | None,
        reason: str,
    ) -> dict[str, Any]:
        """Create a staging record for manual review."""
        try:
            staging_record = gene_staging.create_staging_record(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                original_data=original_data or {},
                normalization_log={"failure_reason": reason, "attempts": 1},
            )

            logger.sync_debug(
                "Created staging record for gene", staging_id=staging_record.id, gene_text=gene_text
            )

            return {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": staging_record.id,
                "error": None,
                "source": "not_found",
                "original_data": original_data,
            }

        except Exception as e:
            logger.sync_error("Failed to create staging record", gene_text=gene_text, error=str(e))
            return {
                "status": "error",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": None,
                "error": f"Staging creation failed: {e}",
                "source": "error",
                "original_data": original_data,
            }


# Global instance
_normalizer = None


def get_gene_normalizer(db_session: Session | None = None) -> GeneNormalizer:
    """Get or create gene normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = GeneNormalizer(db_session)
    return _normalizer


# Convenience function - async only
async def normalize_genes_batch_async(
    db: Session,
    gene_texts: list[str],
    source_name: str,
    original_data_list: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Async batch gene normalization - the only correct implementation."""
    normalizer = get_gene_normalizer(db)
    return await normalizer.normalize_batch_async(db, gene_texts, source_name, original_data_list)


async def get_normalization_stats(db: Session) -> dict[str, Any]:
    """Get statistics about gene normalization."""
    try:
        # Gene statistics
        total_genes = gene_crud.count(db)
        genes_with_hgnc = gene_crud.count(db)  # TODO: Implement proper HGNC count

        # Staging statistics
        staging_stats = gene_staging.get_staging_stats(db)

        # HGNC cache info
        normalizer = get_gene_normalizer(db)
        hgnc_cache_info = await normalizer.hgnc_client.get_cache_stats()

        return {
            "total_genes": total_genes,
            "genes_with_hgnc_id": genes_with_hgnc,
            "genes_without_hgnc_id": total_genes - genes_with_hgnc,
            "normalization_coverage": (
                (genes_with_hgnc / total_genes * 100) if total_genes > 0 else 0
            ),
            "staging_records": {
                "pending": staging_stats.get("pending", 0),
                "approved": staging_stats.get("approved", 0),
                "rejected": staging_stats.get("rejected", 0),
                "total": staging_stats.get("total", 0),
            },
            "hgnc_cache_info": hgnc_cache_info,
        }
    except Exception as e:
        logger.sync_error("Error getting normalization stats", error=str(e))
        return {"error": str(e)}


async def clear_normalization_cache():
    """Clear HGNC client cache."""
    normalizer = get_gene_normalizer()
    await normalizer.hgnc_client.clear_cache()
    logger.sync_info("HGNC normalization cache cleared")
