"""Individual literature scraper for extracting genes from specific publications."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from base_literature_scraper import BaseLiteratureScraper
from schemas import LiteratureGene, LiteraturePublication, LiteratureSummary


class IndividualLiteratureScraper(BaseLiteratureScraper):
    """Scraper for extracting genes from individual literature publications."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the scraper."""
        super().__init__(config)
        self.processor_mapping = self._load_processor_mapping()

    def _load_processor_mapping(self) -> Dict[str, Any]:
        """Load processor mapping for each PMID.
        Returns:
            Dict mapping PMID to processor class
        """
        # Import processors
        from processors import (
            pmid_33664247,
            pmid_34264297,
            pmid_35325889,
            pmid_36035137,
            remaining_processors,
        )

        # Map PMIDs to their processors
        mapping = {
            "35325889": pmid_35325889.PMID35325889Processor,
            "36035137": pmid_36035137.PMID36035137Processor,
            "33664247": pmid_33664247.PMID33664247Processor,
            "34264297": pmid_34264297.PMID34264297Processor,
            "30476936": remaining_processors.PMID30476936Processor,
            "31509055": remaining_processors.PMID31509055Processor,
            "31822006": remaining_processors.PMID31822006Processor,
            "29801666": remaining_processors.PMID29801666Processor,
            "31027891": remaining_processors.PMID31027891Processor,
            "26862157": remaining_processors.PMID26862157Processor,
            "33532864": remaining_processors.PMID33532864Processor,
            "35005812": remaining_processors.PMID35005812Processor,
        }

        return mapping

    def process_publication(self, pub_metadata: Dict[str, Any]) -> Optional[LiteraturePublication]:
        """Process a single publication and return its data.
        
        Args:
            pub_metadata: Publication metadata from Excel
            
        Returns:
            LiteraturePublication object or None if processing fails
        """
        pmid = str(pub_metadata.get("PMID", ""))
        if not pmid:
            self.logger.error("No PMID in publication metadata")
            return None

        # Check if we have a processor for this PMID
        if pmid not in self.processor_mapping:
            self.logger.error(f"No processor available for PMID {pmid}")
            return None

        try:
            # Get file path
            file_type = pub_metadata.get("Type", "").lower()
            file_path = self.data_dir / "downloads" / f"PMID_{pmid}.{file_type}"
            
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return None

            # Process the publication
            processor_class = self.processor_mapping[pmid]
            processor = processor_class()
            raw_genes = processor.process(file_path)

            if not raw_genes:
                self.logger.warning(f"No genes extracted from PMID {pmid}")
                raw_genes = []

            # Normalize genes and create LiteratureGene objects
            self.logger.info(f"Normalizing {len(raw_genes)} genes for PMID {pmid}")
            literature_genes = []
            
            for gene_symbol in raw_genes:
                # Normalize through HGNC
                hgnc_data = self.hgnc_normalizer.normalize_symbol(gene_symbol)
                
                # Create LiteratureGene object
                if hgnc_data and hgnc_data.get("found"):
                    gene = LiteratureGene(
                        symbol=hgnc_data["approved_symbol"],
                        reported_as=gene_symbol,
                        hgnc_id=hgnc_data.get("hgnc_id"),
                        normalization_status="normalized"
                    )
                else:
                    # Keep original symbol if not found in HGNC
                    gene = LiteratureGene(
                        symbol=gene_symbol,
                        reported_as=gene_symbol,
                        hgnc_id=None,
                        normalization_status="not_found"
                    )
                
                literature_genes.append(gene)

            # Parse authors (split by semicolon or comma if multiple)
            authors_str = pub_metadata.get("Authors", "")
            if ';' in authors_str:
                authors = [a.strip() for a in authors_str.split(';')]
            elif ',' in authors_str and authors_str.count(',') > 1:
                # Multiple commas suggest multiple authors
                authors = [a.strip() for a in authors_str.split(',')]
            else:
                authors = [authors_str] if authors_str else []

            # Extract journal from metadata (could be in Link or Name field)
            journal = self._extract_journal(pub_metadata)
            
            # Convert publication date to string if it's a datetime
            import datetime as dt
            pub_date = pub_metadata.get("Publication Date", "")
            if isinstance(pub_date, (dt.datetime, dt.date)):
                pub_date = pub_date.isoformat()
            else:
                pub_date = str(pub_date) if pub_date else ""
            
            # Create publication object
            publication = LiteraturePublication(
                id=pmid,  # ID is same as PMID
                pmid=pmid,
                title=pub_metadata.get("Name", ""),
                authors=authors,
                journal=journal,
                publication_date=pub_date,
                url=pub_metadata.get("Link", ""),
                doi=self._extract_doi(pub_metadata),
                genes=literature_genes,
                gene_count=len(literature_genes),
                source_file=str(file_path),
                file_type=file_type,
                extraction_method=processor_class.__name__
            )

            return publication

        except Exception as e:
            self.logger.error(f"Error processing PMID {pmid}: {e}")
            return None

    def _extract_journal(self, metadata: Dict[str, Any]) -> str:
        """Extract journal name from metadata."""
        # Try to parse from Link or other fields
        link = metadata.get("Link", "")
        name = metadata.get("Name", "")
        
        # Common journal patterns in URLs
        journal_mapping = {
            "kidney-international.org": "Kidney International",
            "onlinelibrary.wiley.com": "Human Mutation",
            "karger.com": "American Journal of Nephrology",
            "tandfonline.com": "Renal Failure",
            "nature.com": "NPJ Genomic Medicine",
            "frontiersin.org": "Frontiers in Genetics",
            "jmg.bmj.com": "Journal of Medical Genetics",
            "nejm.org": "New England Journal of Medicine",
        }
        
        for domain, journal in journal_mapping.items():
            if domain in link.lower():
                return journal
        
        # Check if journal name is in the title
        if "Kidney International" in name:
            return "Kidney International"
        elif "Human Mutation" in name:
            return "Human Mutation"
        
        return "Unknown Journal"

    def _extract_doi(self, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract DOI from metadata if available."""
        # Check Link field for DOI
        link = metadata.get("Link", "")
        if "doi.org/" in link:
            return link.split("doi.org/")[-1]
        elif "doi/" in link:
            return link.split("doi/")[-1].split("?")[0]
        return None

    def scrape_all(self) -> LiteratureSummary:
        """Process all publications and return summary.
        
        Returns:
            LiteratureSummary with all processed publications
        """
        self.logger.info("Starting individual literature scraping")
        
        summary = LiteratureSummary()
        summary.total_publications = len(self.publications_metadata)
        
        all_publications = []
        all_unique_genes = set()
        failed_pmids = []

        for pub_metadata in self.publications_metadata:
            pmid = str(pub_metadata.get("PMID", ""))
            
            try:
                publication = self.process_publication(pub_metadata)
                
                if publication:
                    # Save individual publication file
                    output_file = self.output_dir / f"literature_pmid_{pmid}.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(publication.to_dict(), f, indent=2, ensure_ascii=False)
                    
                    self.logger.info(f"Saved output to {output_file}")
                    self.logger.info(f"Successfully processed PMID {pmid}: {publication.gene_count} genes")
                    
                    all_publications.append(publication)
                    
                    # Track unique genes
                    for gene in publication.genes:
                        all_unique_genes.add(gene.symbol)
                    
                    # Add to summary
                    summary.publications.append({
                        "pmid": pmid,
                        "title": publication.title,
                        "gene_count": publication.gene_count,
                        "unique_genes": publication.unique_genes,
                        "output_file": f"literature_pmid_{pmid}.json"
                    })
                    summary.successful_extractions += 1
                else:
                    failed_pmids.append({"pmid": pmid, "error": "Processing failed"})
                    summary.failed_extractions += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to process PMID {pmid}: {e}")
                failed_pmids.append({"pmid": pmid, "error": str(e)})
                summary.failed_extractions += 1

        # Update summary
        summary.total_unique_genes = len(all_unique_genes)
        if failed_pmids:
            summary.extraction_errors = failed_pmids

        # Save summary
        summary_file = self.output_dir / "literature_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved summary to {summary_file}")
        self.logger.info(
            f"Literature scraping complete: {summary.successful_extractions} successful, "
            f"{summary.failed_extractions} failed"
        )

        return summary