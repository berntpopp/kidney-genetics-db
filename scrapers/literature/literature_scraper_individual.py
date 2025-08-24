"""Literature scraper that outputs individual files per publication."""

import importlib
import json
from datetime import datetime
from typing import Any, Dict

from base_literature_scraper import BaseLiteratureScraper
from schemas import GeneEntry, LiteratureData, Publication


class IndividualLiteratureScraper(BaseLiteratureScraper):
    """Literature scraper that processes publications individually."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the literature scraper."""
        super().__init__(config)
        self.processor_mapping = self._load_processor_mapping()

    def _load_processor_mapping(self) -> Dict[str, Any]:
        """Load processor classes for each PMID."""
        mapping = {}

        # Map PMIDs to their processor modules
        pmid_processors = {
            "35325889": "pmid_35325889.PMID35325889Processor",
            "36035137": "pmid_36035137.PMID36035137Processor",
            "33664247": "pmid_33664247.PMID33664247Processor",
            "34264297": "pmid_34264297.PMID34264297Processor",
            "30476936": "remaining_processors.PMID30476936Processor",
            "31509055": "remaining_processors.PMID31509055Processor",
            "31822006": "remaining_processors.PMID31822006Processor",
            "29801666": "remaining_processors.PMID29801666Processor",
            "31027891": "remaining_processors.PMID31027891Processor",
            "26862157": "remaining_processors.PMID26862157Processor",
            "33532864": "remaining_processors.PMID33532864Processor",
            "35005812": "remaining_processors.PMID35005812Processor",
        }

        for pmid, processor_path in pmid_processors.items():
            try:
                module_name, class_name = processor_path.rsplit(".", 1)
                module = importlib.import_module(f"processors.{module_name}")
                processor_class = getattr(module, class_name)
                mapping[pmid] = processor_class
                self.logger.debug(f"Loaded processor for PMID {pmid}")
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Processor not found for PMID {pmid}: {e}")

        return mapping

    def process_publication(self, pub_metadata: Dict[str, Any]) -> LiteratureData:
        """Process a single publication and return its data.

        Args:
            pub_metadata: Publication metadata from Excel

        Returns:
            LiteratureData for this publication
        """
        pmid = str(pub_metadata.get("PMID", ""))
        file_type = pub_metadata.get("Type", "")

        if not pmid:
            raise ValueError("No PMID in publication metadata")

        # Check if we have a processor for this PMID
        if pmid not in self.processor_mapping:
            raise ValueError(f"No processor available for PMID {pmid}")

        # Get file path
        file_path = self.data_dir / "downloads" / f"PMID_{pmid}.{file_type.lower()}"

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Process the publication
        processor_class = self.processor_mapping[pmid]
        processor = processor_class()
        genes = processor.process(file_path)

        if not genes:
            self.logger.warning(f"No genes extracted from PMID {pmid}")
            genes = []

        # Create GeneEntry objects for this publication
        gene_entries = []
        for gene_symbol in genes:
            entry = GeneEntry(
                symbol=gene_symbol,
                panels=[f"PMID_{pmid}"],  # Single publication
                occurrence_count=1,
                confidence="medium",  # Default confidence for single publication
            )
            gene_entries.append(entry)

        # Normalize genes via HGNC
        if gene_entries:
            self.logger.info(f"Normalizing {len(gene_entries)} genes for PMID {pmid}")
            gene_entries = self.normalize_genes(gene_entries)

        # Create publication record
        publication = Publication(
            pmid=pmid,
            name=pub_metadata.get("Name", "")[:200],
            authors=pub_metadata.get("Authors", "")[:200],
            publication_date=str(pub_metadata.get("Publication Date", "")),
            file_type=file_type,
            gene_count=len(gene_entries),
            extraction_method=f"{processor_class.__name__}",
        )

        # Create result for this publication
        result = LiteratureData(
            provider_id=f"literature_pmid_{pmid}",
            provider_name=f"Literature PMID {pmid}",
            provider_type="literature",
            main_url=pub_metadata.get("Link", ""),
            total_panels=1,  # Single publication
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            publications=[publication],
            metadata={
                "pmid": pmid,
                "title": pub_metadata.get("Name", ""),
                "source_file": str(file_path),
                "extraction_timestamp": datetime.now().isoformat(),
            },
        )

        return result

    def save_individual_output(self, data: LiteratureData, pmid: str):
        """Save output for individual publication.

        Args:
            data: LiteratureData for the publication
            pmid: PMID identifier
        """
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        output_file = date_dir / f"literature_pmid_{pmid}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, indent=2, default=str)

        self.logger.info(f"Saved output to {output_file}")

    def run(self) -> Dict[str, LiteratureData]:
        """Process all publications individually.

        Returns:
            Dictionary mapping PMIDs to their LiteratureData
        """
        self.logger.info("Starting individual literature scraping")

        results = {}
        successful = 0
        failed = 0

        # Process each publication individually
        for pub_metadata in self.publications_metadata:
            pmid = str(pub_metadata.get("PMID", ""))

            if not pmid:
                continue

            try:
                # Process publication
                result = self.process_publication(pub_metadata)

                # Save individual output
                self.save_individual_output(result, pmid)

                # Store in results
                results[pmid] = result
                successful += 1

                self.logger.info(
                    f"Successfully processed PMID {pmid}: "
                    f"{result.total_unique_genes} genes",
                )

            except Exception as e:
                self.logger.error(f"Failed to process PMID {pmid}: {e}")
                failed += 1

        # Create summary file
        self._create_summary(results, successful, failed)

        self.logger.info(
            f"Literature scraping complete: "
            f"{successful} successful, {failed} failed",
        )

        return results

    def _create_summary(
        self, results: Dict[str, LiteratureData], successful: int, failed: int
    ):
        """Create a summary file for all processed publications.

        Args:
            results: Dictionary of PMID to LiteratureData
            successful: Count of successful processing
            failed: Count of failed processing
        """
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # Collect summary statistics
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_publications_attempted": successful + failed,
            "successful": successful,
            "failed": failed,
            "publications": [],
        }

        # Add publication details
        for pmid, data in results.items():
            pub_summary = {
                "pmid": pmid,
                "title": data.metadata.get("title", ""),
                "gene_count": data.total_unique_genes,
                "genes_with_hgnc": sum(1 for g in data.genes if g.hgnc_id),
                "output_file": f"literature_pmid_{pmid}.json",
            }
            summary["publications"].append(pub_summary)

        # Calculate total unique genes across all publications
        all_genes = set()
        for data in results.values():
            for gene in data.genes:
                all_genes.add(gene.symbol)

        summary["total_unique_genes_all_publications"] = len(all_genes)

        # Save summary
        summary_file = date_dir / "literature_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        self.logger.info(f"Saved summary to {summary_file}")
