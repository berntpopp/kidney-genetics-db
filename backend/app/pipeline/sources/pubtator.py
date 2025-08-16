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
        self.kidney_queries = [
            "kidney disease",
            "renal disease",
            "nephropathy",
            "glomerulonephritis",
            "nephrotic syndrome",
            "chronic kidney disease",
            "polycystic kidney",
            "renal failure",
            "nephritis",
            "proteinuria",
        ]

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

        for page in range(1, max_pages + 1):
            try:
                # Use search endpoint like the R implementation
                response = self.client.get(
                    f"{self.base_url}/publications/search",
                    params={"q": query, "page": page},
                )

                if response.status_code != 200:
                    break

                data = response.json()
                results = data.get("results", [])

                if not results:
                    break

                # Process each publication
                for result in results:
                    pmid = result.get("pmid")
                    passages = result.get("passages", [])

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
                time.sleep(0.3)

            except Exception as e:
                logger.error(f"Error fetching PubTator search page {page}: {e}")
                break

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
        # Aggregate gene mentions from all queries
        all_gene_data = {}  # symbol -> aggregated data

        for query in client.kidney_queries:
            logger.info(f"Searching PubTator for: {query}")
            gene_annotations = client.get_annotations_by_search(query, max_pages=3)
            stats["queries_processed"] += 1

            # Merge with existing data
            for symbol, data in gene_annotations.items():
                if symbol not in all_gene_data:
                    all_gene_data[symbol] = {
                        "pmids": set(),
                        "mentions": 0,
                        "ncbi_gene_ids": set(),
                    }

                all_gene_data[symbol]["pmids"].update(data["pmids"])
                all_gene_data[symbol]["mentions"] += data["mentions"]
                all_gene_data[symbol]["ncbi_gene_ids"].update(data.get("ncbi_gene_ids", []))

            logger.debug(f"Found {len(gene_annotations)} genes for query: {query}")

        logger.info(f"Found {len(all_gene_data)} unique genes across all queries")

        # Store in database (only genes with multiple mentions)
        for symbol, data in all_gene_data.items():
            # Skip if only mentioned in one paper
            pmid_list = list(data["pmids"])
            if len(pmid_list) < 2:
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
