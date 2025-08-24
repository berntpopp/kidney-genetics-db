#!/usr/bin/env python3
"""Main script to run the literature scraper.

This script processes scientific publications to extract gene symbols for the
kidney genetics database. It supports both individual file output and
aggregated output modes.
"""

import argparse
import logging
import sys
from pathlib import Path

from literature_scraper_individual import IndividualLiteratureScraper


def setup_logging(level: str = "INFO"):
    """Setup basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Main entry point for the literature scraper."""
    parser = argparse.ArgumentParser(
        description="Extract gene symbols from kidney genetics publications"
    )
    parser.add_argument(
        "--config", type=str, help="Path to configuration file (default: config/config.yaml)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument("--pmid", type=str, help="Process only a specific PMID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually running",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration if provided
        config = None
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {config_path}")
                sys.exit(1)

            import yaml

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

        # Initialize scraper
        logger.info("Initializing literature scraper...")
        scraper = IndividualLiteratureScraper(config)

        # Dry run mode - just show what would be processed
        if args.dry_run:
            logger.info("DRY RUN MODE - No files will be processed")
            logger.info(f"Would process {len(scraper.publications_metadata)} publications:")
            for pub in scraper.publications_metadata:
                pmid = pub.get("PMID")
                title = pub.get("Name", "")[:80]
                file_type = pub.get("Type", "")
                logger.info(f"  - PMID {pmid} ({file_type}): {title}...")
            return

        # Process specific PMID if requested
        if args.pmid:
            logger.info(f"Processing only PMID {args.pmid}")

            # Find the publication
            pub_metadata = None
            for pub in scraper.publications_metadata:
                if str(pub.get("PMID")) == args.pmid:
                    pub_metadata = pub
                    break

            if not pub_metadata:
                logger.error(f"PMID {args.pmid} not found in metadata")
                sys.exit(1)

            # Process single publication
            try:
                result = scraper.process_publication(pub_metadata)
                scraper.save_individual_output(result, args.pmid)
                logger.info(
                    f"Successfully processed PMID {args.pmid}: {result.total_unique_genes} genes"
                )
            except Exception as e:
                logger.error(f"Failed to process PMID {args.pmid}: {e}")
                sys.exit(1)
        else:
            # Process all publications
            logger.info("Processing all publications...")
            results = scraper.run()

            # Print summary
            logger.info("\n" + "=" * 60)
            logger.info("PROCESSING COMPLETE")
            logger.info("=" * 60)

            total_genes = sum(r.total_unique_genes for r in results.values())
            all_unique_genes = set()
            for result in results.values():
                for gene in result.genes:
                    all_unique_genes.add(gene.symbol)

            logger.info(f"Publications processed: {len(results)}")
            logger.info(f"Total genes extracted: {total_genes}")
            logger.info(f"Unique genes across all publications: {len(all_unique_genes)}")

            # Show HGNC normalization stats
            stats = scraper.hgnc_normalizer.get_stats()
            logger.info("\nHGNC Normalization Stats:")
            logger.info(f"  API calls: {stats['api_calls']}")
            logger.info(f"  Cache hits: {stats['cache_hits']}")
            logger.info(f"  Cache misses: {stats['cache_misses']}")

            # List output files
            logger.info(f"\nOutput files saved to: {scraper.output_dir}")

    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
