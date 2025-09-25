#!/usr/bin/env python
"""Backfill molecular consequences for existing ClinVar annotations."""

import asyncio

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.config import settings
from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

logger = get_logger(__name__)


async def backfill_molecular_consequences():
    """Re-fetch ClinVar data to get molecular consequences."""
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db:
        # Initialize services
        cache_service = get_cache_service(db)
        clinvar_source = ClinVarAnnotationSource(db)

        # Clear ClinVar cache to ensure fresh data
        await cache_service.clear_namespace("clinvar")
        logger.sync_info("Cleared ClinVar cache")

        # Find genes that have ClinVar data but no consequences
        genes_to_update = db.execute(text("""
            SELECT DISTINCT g.*
            FROM genes g
            JOIN gene_annotations ga ON ga.gene_id = g.id
            WHERE ga.source = 'clinvar'
            AND ga.annotations->>'total_variants' IS NOT NULL
            AND ga.annotations->>'total_variants' != '0'
            AND NOT ga.annotations ? 'molecular_consequences'
            ORDER BY g.approved_symbol
            LIMIT 100  -- Process in batches
        """)).fetchall()

        logger.sync_info(f"Found {len(genes_to_update)} genes to update")

        # Process with rate limiting
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests

        async def process_gene(gene_row):
            async with semaphore:
                try:
                    # Create Gene object from row
                    gene = Gene(
                        id=gene_row.id,
                        approved_symbol=gene_row.approved_symbol,
                        hgnc_id=gene_row.hgnc_id
                    )

                    # Fetch updated annotation
                    annotation = await clinvar_source.fetch_annotation(gene)

                    if annotation and "molecular_consequences" in annotation:
                        logger.sync_info(
                            f"Updated {gene.approved_symbol}",
                            truncating=annotation["consequence_categories"].get("truncating", 0),
                            total=annotation["total_variants"]
                        )

                    # Rate limit
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.sync_error(
                        f"Failed to update {gene_row.approved_symbol}",
                        error=str(e)
                    )

        # Process all genes
        tasks = [process_gene(gene) for gene in genes_to_update]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        updated_count = db.execute(text("""
            SELECT COUNT(*)
            FROM gene_annotations ga
            WHERE ga.source = 'clinvar'
            AND ga.annotations ? 'molecular_consequences'
        """)).scalar()

        logger.sync_info(f"Backfill complete. {updated_count} genes now have molecular consequences")


if __name__ == "__main__":
    asyncio.run(backfill_molecular_consequences())
