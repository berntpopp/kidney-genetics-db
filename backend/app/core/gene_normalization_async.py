"""
Async version of gene normalization for use in async contexts.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.gene_normalization import clean_gene_text
from app.core.hgnc_client_cached import get_hgnc_client_cached
from app.crud.gene import gene_crud

logger = logging.getLogger(__name__)


async def normalize_genes_batch_async(
    db: Session,
    gene_texts: list[str],
    source_name: str,
    original_data_list: list[dict[str, Any]] | None = None
) -> dict[str, dict[str, Any]]:
    """
    Async version of normalize_genes_batch.
    
    Normalize multiple genes efficiently using batch processing.
    
    Args:
        db: Database session
        gene_texts: List of gene symbols/names to normalize
        source_name: Name of the data source
        original_data_list: Optional list of original data for each gene
    
    Returns:
        Dictionary mapping original text to normalized gene info
    """
    if not gene_texts:
        return {}
    
    logger.info(f"[{source_name}] Normalizing {len(gene_texts)} gene texts")
    
    # Clean and prepare gene texts
    cleaned_genes = []
    gene_mapping = {}
    
    for i, gene_text in enumerate(gene_texts):
        if not gene_text:
            continue
        
        cleaned = clean_gene_text(gene_text)
        if cleaned:
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
        existing_gene = gene_crud.get_by_symbol(db, cleaned)
        if existing_gene and existing_gene.hgnc_id:
            existing_genes[cleaned] = {
                "approved_symbol": existing_gene.approved_symbol,
                "hgnc_id": existing_gene.hgnc_id
            }
    
    logger.info(f"Found {len(existing_genes)} genes already in database")
    
    # Look up remaining genes via HGNC
    genes_to_lookup = [g for g in cleaned_genes if g not in existing_genes]
    hgnc_results = {}
    
    if genes_to_lookup:
        hgnc_client = get_hgnc_client_cached()
        # Already in async context, so await directly
        hgnc_results = await hgnc_client.standardize_symbols_parallel(genes_to_lookup)
    
    # Compile final results
    results = {}
    
    for cleaned in cleaned_genes:
        mapping = gene_mapping[cleaned]
        original_text = mapping["original"]
        
        # Check if we have existing gene info
        if cleaned in existing_genes:
            gene_info = existing_genes[cleaned]
            results[original_text] = {
                "approved_symbol": gene_info["approved_symbol"],
                "hgnc_id": gene_info["hgnc_id"],
                "source": "database",
                "original_data": mapping["original_data"]
            }
        # Check if HGNC found it
        elif cleaned in hgnc_results:
            hgnc_info = hgnc_results[cleaned]
            if hgnc_info and hgnc_info.get("approved_symbol"):
                results[original_text] = {
                    "approved_symbol": hgnc_info["approved_symbol"],
                    "hgnc_id": hgnc_info.get("hgnc_id", ""),
                    "source": "hgnc",
                    "original_data": mapping["original_data"]
                }
            else:
                # Gene not found in HGNC
                results[original_text] = {
                    "approved_symbol": cleaned,
                    "hgnc_id": None,
                    "source": "not_found",
                    "original_data": mapping["original_data"]
                }
        else:
            # Shouldn't happen, but handle it
            results[original_text] = {
                "approved_symbol": cleaned,
                "hgnc_id": None,
                "source": "not_found",
                "original_data": mapping["original_data"]
            }
    
    # Log summary
    sources = {}
    for info in results.values():
        source = info.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1
    
    logger.info(
        f"[{source_name}] Normalization complete: "
        f"{sources.get('database', 0)} from database, "
        f"{sources.get('hgnc', 0)} from HGNC, "
        f"{sources.get('not_found', 0)} not found"
    )
    
    return results