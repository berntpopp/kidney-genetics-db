#!/usr/bin/env python3
"""
Main orchestration script to run all diagnostic panel scrapers.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add the diagnostics directory to the path
sys.path.append(str(Path(__file__).parent))

from providers import (
    BlueprintGeneticsScraper,
    CegatScraper,
    CentogeneScraper,
    InvitaeScraper,
    MayoClinicScraper,
    MGZMuenchenScraper,
    MVZMedicoverScraper,
    NateraScraper,
    PreventionGeneticsScraper,
)
from schemas import DiagnosticPanelBatch

# Configure logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / f'scraping_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Orchestrates running all diagnostic panel scrapers."""

    def __init__(self, config_path: str = None):
        """
        Initialize the orchestrator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.output_dir = Path(self.config.get('output_dir', 'output'))
        self.scrapers = self._initialize_scrapers()

    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    return json.load(f)

        # Default configuration
        return {
            'output_dir': 'output',
            'rate_limit': 2,
            'enable_browser': True,
            'scrapers': {
                'blueprint_genetics': {'enabled': True},
                'mayo_clinic': {'enabled': True},
                'centogene': {'enabled': True},
                'cegat': {'enabled': True},
                'invitae': {'enabled': True},
                'mgz_muenchen': {'enabled': True},
                'mvz_medicover': {'enabled': True},
                'natera': {'enabled': True},
                'prevention_genetics': {'enabled': True}
            }
        }

    def _initialize_scrapers(self) -> List:
        """
        Initialize all enabled scrapers.
        
        Returns:
            List of scraper instances
        """
        scrapers = []
        scraper_config = self.config.get('scrapers', {})

        scraper_classes = [
            ('blueprint_genetics', BlueprintGeneticsScraper),
            ('mayo_clinic', MayoClinicScraper),
            ('centogene', CentogeneScraper),
            ('cegat', CegatScraper),
            ('invitae', InvitaeScraper),
            ('mgz_muenchen', MGZMuenchenScraper),
            ('mvz_medicover', MVZMedicoverScraper),
            ('natera', NateraScraper),
            ('prevention_genetics', PreventionGeneticsScraper)
        ]

        for scraper_id, scraper_class in scraper_classes:
            if scraper_config.get(scraper_id, {}).get('enabled', True):
                scrapers.append(scraper_class(self.config))
                logger.info(f"Initialized {scraper_id} scraper")
            else:
                logger.info(f"Skipping disabled scraper: {scraper_id}")

        return scrapers

    def run_all(self) -> DiagnosticPanelBatch:
        """
        Run all enabled scrapers.
        
        Returns:
            DiagnosticPanelBatch with all results
        """
        logger.info(f"Starting scraping run with {len(self.scrapers)} scrapers")

        providers = []
        total_genes = 0
        all_errors = []

        for i, scraper in enumerate(self.scrapers, 1):
            try:
                logger.info(f"[{i}/{len(self.scrapers)}] Running {scraper.provider_id} scraper...")

                # Run the scraper
                result = scraper.run()
                providers.append(result)
                total_genes += result.total_unique_genes

                if result.errors:
                    all_errors.extend([f"{scraper.provider_id}: {e}" for e in result.errors])

                logger.info(f"Completed {scraper.provider_id}: {result.total_unique_genes} genes")

            except Exception as e:
                logger.error(f"Failed to run {scraper.provider_id}: {e}")
                all_errors.append(f"{scraper.provider_id}: {str(e)}")

        # Create batch result
        batch = DiagnosticPanelBatch(providers=providers)

        # Save batch result
        self._save_batch(batch)

        return batch

    def _save_batch(self, batch: DiagnosticPanelBatch):
        """
        Save batch results to file.
        
        Args:
            batch: Batch results to save
        """
        batch_dir = self.output_dir / 'batches'
        batch_dir.mkdir(parents=True, exist_ok=True)

        batch_file = batch_dir / f"batch_{batch.batch_id}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch.model_dump(), f, indent=2, default=str)

        logger.info(f"Saved batch results to {batch_file}")

    def generate_summary(self, batch: DiagnosticPanelBatch) -> str:
        """
        Generate a summary report of the scraping run.
        
        Args:
            batch: Batch results
            
        Returns:
            Summary report string
        """
        report = []
        report.append("=" * 80)
        report.append("DIAGNOSTIC PANEL SCRAPING SUMMARY")
        report.append("=" * 80)
        report.append(f"Batch ID: {batch.batch_id}")
        report.append(f"Run Time: {batch.created_at}")
        report.append(f"Total Providers: {batch.total_providers}")
        report.append(f"Total Unique Genes: {batch.total_genes}")
        report.append("")

        report.append("PROVIDER DETAILS:")
        report.append("-" * 80)

        for provider in batch.providers:
            report.append(f"\n{provider.provider_name} ({provider.provider_id}):")
            report.append(f"  - Type: {provider.provider_type}")
            report.append(f"  - URL: {provider.main_url}")
            report.append(f"  - Total Genes: {provider.total_unique_genes}")

            if provider.provider_type == "multi_panel" and provider.sub_panels:
                report.append(f"  - Sub-panels: {len(provider.sub_panels)}")
                # Show top 5 panels by gene count
                sorted_panels = sorted(provider.sub_panels,
                                     key=lambda x: x.gene_count,
                                     reverse=True)[:5]
                report.append("  - Top panels by gene count:")
                for panel in sorted_panels:
                    report.append(f"    • {panel.name}: {panel.gene_count} genes")

            if provider.errors:
                report.append(f"  - Errors: {len(provider.errors)}")

        if batch.errors:
            report.append("\nERRORS:")
            report.append("-" * 80)
            for error in batch.errors:
                report.append(f"  - {error}")

        report.append("\n" + "=" * 80)

        summary = "\n".join(report)

        # Save summary to file
        summary_file = self.output_dir / 'batches' / f"summary_{batch.batch_id}.txt"
        with open(summary_file, 'w') as f:
            f.write(summary)

        return summary


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run diagnostic panel scrapers')
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (YAML or JSON)'
    )
    parser.add_argument(
        '--provider',
        type=str,
        help='Run only a specific provider (e.g., blueprint_genetics)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be run without executing'
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = ScraperOrchestrator(args.config)

    if args.dry_run:
        logger.info("DRY RUN - Would run the following scrapers:")
        for scraper in orchestrator.scrapers:
            logger.info(f"  - {scraper.provider_id}")
        return

    if args.provider:
        # Run single provider
        scraper_map = {s.provider_id: s for s in orchestrator.scrapers}
        if args.provider in scraper_map:
            logger.info(f"Running single provider: {args.provider}")
            result = scraper_map[args.provider].run()
            logger.info(f"Completed: {result.total_unique_genes} genes")
        else:
            logger.error(f"Provider not found: {args.provider}")
            logger.info(f"Available providers: {', '.join(scraper_map.keys())}")
            sys.exit(1)
    else:
        # Run all providers
        batch = orchestrator.run_all()

        # Generate and print summary
        summary = orchestrator.generate_summary(batch)
        print(summary)

        logger.info(f"Scraping complete! Results saved in {orchestrator.output_dir}")


if __name__ == "__main__":
    main()
