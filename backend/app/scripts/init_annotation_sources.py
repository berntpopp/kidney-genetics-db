#!/usr/bin/env python3
"""
Initialize all annotation sources in the database.
This script ensures all annotation sources are properly registered and configured.
"""

import asyncio
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.gene_annotation import AnnotationSource

logger = get_logger(__name__)

# Define all annotation sources with their configurations
ANNOTATION_SOURCES = [
    {
        "source_name": "hgnc",
        "display_name": "HGNC",
        "description": "HUGO Gene Nomenclature Committee - Gene symbols and identifiers",
        "base_url": "https://www.genenames.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 10,  # Highest priority - provides base identifiers
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 100,
            "requests_per_second": 10.0
        }
    },
    {
        "source_name": "gnomad",
        "display_name": "gnomAD",
        "description": "Genome Aggregation Database - Population allele frequencies and constraint scores",
        "base_url": "https://gnomad.broadinstitute.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 9,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 50,
            "requests_per_second": 5.0
        }
    },
    {
        "source_name": "gtex",
        "display_name": "GTEx",
        "description": "Genotype-Tissue Expression - Gene expression across tissues",
        "base_url": "https://gtexportal.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 8,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 100,
            "requests_per_second": 10.0
        }
    },
    {
        "source_name": "clinvar",
        "display_name": "ClinVar",
        "description": "Clinical Variants - Pathogenicity and clinical significance",
        "base_url": "https://www.ncbi.nlm.nih.gov/clinvar/",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 7,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 20,
            "requests_per_second": 3.0
        }
    },
    {
        "source_name": "hpo",
        "display_name": "HPO",
        "description": "Human Phenotype Ontology - Phenotype associations",
        "base_url": "https://hpo.jax.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 6,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 50,
            "requests_per_second": 5.0
        }
    },
    {
        "source_name": "mpo_mgi",
        "display_name": "MPO/MGI",
        "description": "Mouse Phenotype Ontology / Mouse Genome Informatics - Mouse orthologs and phenotypes",
        "base_url": "http://www.informatics.jax.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 5,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 50,
            "requests_per_second": 5.0
        }
    },
    {
        "source_name": "string_ppi",
        "display_name": "STRING PPI",
        "description": "STRING Protein-Protein Interactions - Protein interaction networks",
        "base_url": "https://string-db.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 4,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 100,
            "requests_per_second": 10.0
        }
    },
    {
        "source_name": "descartes",
        "display_name": "Descartes",
        "description": "Descartes Human Cell Atlas - Single-cell expression data",
        "base_url": "https://descartes.brotmanbaty.org",
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": 3,
        "config": {
            "cache_ttl_days": 90,
            "batch_size": 100,
            "requests_per_second": 5.0
        }
    }
]


async def init_annotation_sources():
    """Initialize all annotation sources in the database."""

    # Get database session
    db = next(get_db())

    try:
        await logger.info("Starting annotation source initialization")

        created_count = 0
        updated_count = 0

        for source_config in ANNOTATION_SOURCES:
            # Check if source already exists
            existing = db.query(AnnotationSource).filter_by(
                source_name=source_config["source_name"]
            ).first()

            if existing:
                # Update existing source
                for key, value in source_config.items():
                    if key != "source_name":  # Don't update the primary identifier
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
                await logger.info(f"Updated annotation source: {source_config['source_name']}")
            else:
                # Create new source
                new_source = AnnotationSource(**source_config)
                new_source.created_at = datetime.now(timezone.utc)
                new_source.updated_at = datetime.now(timezone.utc)
                db.add(new_source)
                created_count += 1
                await logger.info(f"Created annotation source: {source_config['source_name']}")

        # Commit all changes
        db.commit()

        await logger.info(
            "Annotation source initialization complete",
            created=created_count,
            updated=updated_count,
            total=len(ANNOTATION_SOURCES)
        )

        # Display current status
        all_sources = db.query(AnnotationSource).order_by(AnnotationSource.priority.desc()).all()
        await logger.info("Current annotation sources status:")
        for source in all_sources:
            await logger.info(
                f"  - {source.source_name}: active={source.is_active}, priority={source.priority}, "
                f"last_update={source.last_update}"
            )

        return {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(all_sources)
        }

    except Exception as e:
        await logger.error(f"Failed to initialize annotation sources: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


async def clear_corrupted_cache():
    """Clear any corrupted cache entries to prevent deserialization errors."""

    db = next(get_db())

    try:
        await logger.info("Clearing cache to prevent corruption issues")

        # Clear all cache entries to ensure clean slate
        from app.models.cache import CacheEntry

        cache_count = db.query(CacheEntry).count()
        if cache_count > 0:
            db.query(CacheEntry).delete()
            db.commit()
            await logger.info(f"Cleared {cache_count} cache entries")
        else:
            await logger.info("Cache already empty")

    except Exception as e:
        await logger.error(f"Failed to clear cache: {str(e)}")
        db.rollback()
    finally:
        db.close()


async def main():
    """Main entry point for the script."""

    # Clear cache first to prevent issues
    await clear_corrupted_cache()

    # Initialize annotation sources
    result = await init_annotation_sources()

    if result["success"]:
        print(f"\n✅ Successfully initialized {result['total']} annotation sources")
        print(f"   Created: {result['created']}")
        print(f"   Updated: {result['updated']}")
        print("\n🚀 You can now run the annotation pipeline to fetch data from all sources")
    else:
        print("\n❌ Failed to initialize annotation sources")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
