"""
PubTator data source integration

Fetches kidney disease-related gene mentions from biomedical literature
"""

import logging
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.gene import gene_crud
from app.models.gene import GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


class PubTatorClient:
    """Client for PubTator API integration"""

    def __init__(self):
        """Initialize PubTator client"""
        self.base_url = settings.PUBTATOR_API_URL
        self.client = httpx.Client(timeout=60.0)
        # Use comprehensive query like kidney-genetics-v1
        # This matches the approach in the R implementation which uses a single comprehensive query
        self.kidney_query = (
            "(kidney disease OR renal disease OR nephropathy OR glomerulonephritis OR "
            "nephrotic syndrome OR chronic kidney disease OR polycystic kidney OR "
            "renal failure OR nephritis OR proteinuria OR CAKUT OR "
            "congenital anomalies kidney urinary tract OR tubulopathy OR "
            "glomerulopathy OR ciliopathy kidney OR Alport syndrome OR "
            "focal segmental glomerulosclerosis OR FSGS OR "
            "IgA nephropathy OR membranous nephropathy OR "
            "tubulointerstitial kidney disease OR nephrolithiasis OR kidney stones)"
        )

    def search_publications(self, query: str, max_results: int = 100) -> list[str]:
        """Search PubMed for kidney-related publications

        Args:
            query: Search query
            max_results: Maximum number of PMIDs to return

        Returns:
            List of PMIDs
        """
        try:
            # Use PubMed E-utilities for search
            response = self.client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    "db": "pubmed",
                    "term": f"{query} AND genetics[MeSH]",
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                    "mindate": "2015",  # Focus on recent literature
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("esearchresult", {}).get("idlist", [])
            return []
        except Exception as e:
            logger.error(f"Error searching PubMed for query '{query}': {e}")
            return []

    def get_annotations_by_search(self, query: str, max_pages: int = 5) -> dict[str, Any]:
        """Get PubTator annotations by searching

        Args:
            query: Search query
            max_pages: Maximum number of pages to fetch

        Returns:
            Dictionary mapping gene symbols to annotation data
        """
        gene_annotations = {}
        all_pmids = []

        # Step 1: Search for PMIDs using PubTator3 search API
        for page in range(1, max_pages + 1):
            try:
                # Use PubTator3 search endpoint
                response = self.client.get(
                    "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/",
                    params={"text": query, "page": page},
                )

                if response.status_code != 200:
                    logger.warning(f"PubTator3 search returned status {response.status_code}")
                    break

                data = response.json()
                results = data.get("results", [])

                if not results:
                    break

                # Collect PMIDs from search results
                for result in results:
                    pmid = result.get("pmid")
                    if pmid:
                        all_pmids.append(str(pmid))

                logger.info(f"Found {len(results)} results on page {page} for query: {query}")

                # Rate limiting
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"Error fetching PubTator3 search page {page}: {e}")
                break

        # Step 2: Get annotations for collected PMIDs (in batches)
        if all_pmids:
            batch_size = 100
            for i in range(0, len(all_pmids), batch_size):
                batch_pmids = all_pmids[i : i + batch_size]
                pmids_str = ",".join(batch_pmids)

                try:
                    # Use PubTator3 export API to get annotations
                    response = self.client.get(
                        "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson",
                        params={"pmids": pmids_str, "concepts": "gene"},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get("PubTator3", [])

                        for article in articles:
                            pmid = article.get("pmid")
                            passages = article.get("passages", [])

                            for passage in passages:
                                annotations = passage.get("annotations", [])

                                for ann in annotations:
                                    if ann.get("infons", {}).get("type") == "Gene":
                                        gene_text = ann.get("text", "")
                                        gene_id = ann.get("infons", {}).get("identifier")

                                        if gene_text:
                                            symbol = self.normalize_gene_symbol(gene_text)
                                            if symbol:
                                                if symbol not in gene_annotations:
                                                    gene_annotations[symbol] = {
                                                        "pmids": set(),
                                                        "mentions": 0,
                                                        "ncbi_gene_ids": set(),
                                                    }

                                                gene_annotations[symbol]["pmids"].add(str(pmid))
                                                gene_annotations[symbol]["mentions"] += 1
                                                if gene_id:
                                                    gene_annotations[symbol]["ncbi_gene_ids"].add(gene_id)

                    # Rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error fetching PubTator3 annotations for batch: {e}")

        # Convert sets to lists
        for gene_data in gene_annotations.values():
            gene_data["pmids"] = list(gene_data["pmids"])
            gene_data["ncbi_gene_ids"] = list(gene_data["ncbi_gene_ids"])

        return gene_annotations

    def normalize_gene_symbol(self, gene_text: str) -> str | None:
        """Normalize gene text to standard symbol

        Args:
            gene_text: Gene text from PubTator

        Returns:
            Normalized gene symbol or None
        """
        # Simple normalization - in production, would use HGNC API
        if not gene_text:
            return None

        # Remove common suffixes/prefixes
        symbol = gene_text.upper()
        symbol = symbol.replace("HUMAN", "").strip()

        # Basic validation
        if len(symbol) > 1 and symbol[0].isalpha():
            return symbol

        return None

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_pubtator_data(db: Session) -> dict[str, Any]:
    # NOTE: PubTator API endpoints have changed. The search endpoint returns 404.
    # Need to investigate current PubTator3 API documentation for correct endpoints.
    # The R implementation uses older PubTator v2 endpoints that may be deprecated.
    """Update database with PubTator literature mining data

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    client = PubTatorClient()
    stats = {
        "source": "PubTator",
        "queries_processed": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Use single comprehensive query like kidney-genetics-v1
        logger.info("Searching PubTator with comprehensive kidney disease query")
        all_gene_data = client.get_annotations_by_search(client.kidney_query, max_pages=10)
        stats["queries_processed"] = 1

        logger.info(f"Found {len(all_gene_data)} unique genes from PubTator search")

        # Store in database (only genes with at least 3 publications, like kidney-genetics-v1)
        for symbol, data in all_gene_data.items():
            # Skip if mentioned in less than 3 papers (matching R implementation threshold)
            pmid_list = list(data["pmids"])
            if len(pmid_list) < 3:
                continue

            stats["genes_processed"] += 1

            # Get or create gene
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene:
                # Create new gene
                try:
                    gene_create = GeneCreate(
                        approved_symbol=symbol,
                        hgnc_id=None,  # Would need HGNC lookup
                        aliases=[],
                    )
                    gene = gene_crud.create(db, gene_create)
                    stats["genes_created"] += 1
                    logger.info(f"Created new gene from PubTator: {symbol}")
                except Exception as e:
                    logger.error(f"Error creating gene {symbol}: {e}")
                    stats["errors"] += 1
                    continue

            # Create or update evidence
            try:
                # Check if PubTator evidence already exists
                existing = (
                    db.query(GeneEvidence)
                    .filter(
                        GeneEvidence.gene_id == gene.id,  # type: ignore[arg-type]
                        GeneEvidence.source_name == "PubTator",
                    )
                    .first()
                )

                evidence_data = {
                    "pmids": pmid_list[:100],  # Limit to 100 PMIDs
                    "publication_count": len(pmid_list),
                    "total_mentions": data["mentions"],
                    "ncbi_gene_ids": list(data["ncbi_gene_ids"])[:10],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

                if existing:
                    # Update existing evidence
                    existing.evidence_data = evidence_data
                    existing.evidence_date = date.today()
                    db.add(existing)
                else:
                    # Create new evidence
                    evidence = GeneEvidence(
                        gene_id=gene.id,  # type: ignore[arg-type]
                        source_name="PubTator",
                        source_detail=f"{len(pmid_list)} publications",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved PubTator evidence for gene: {symbol}")

            except Exception as e:
                logger.error(f"Error saving PubTator evidence for gene {symbol}: {e}")
                db.rollback()
                stats["errors"] += 1

    finally:
        client.close()

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"PubTator update complete: {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats
