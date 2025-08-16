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
from app.pipeline.sources.pubtator_cache import PubTatorCache
from app.schemas.gene import GeneCreate

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PubTatorClient:
    """Client for PubTator API integration"""

    def __init__(self):
        """Initialize PubTator client"""
        self.base_url = settings.PUBTATOR_API_URL
        self.client = httpx.Client(timeout=60.0)
        # Use configuration from central settings
        self.kidney_query = settings.PUBTATOR_SEARCH_QUERY
        self.cache = PubTatorCache()

        # Configuration for processing
        self.max_pages_per_run = settings.PUBTATOR_MAX_PAGES
        self.use_cache = settings.PUBTATOR_USE_CACHE

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
                    "mindate": settings.PUBTATOR_MIN_DATE,
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("esearchresult", {}).get("idlist", [])
            return []
        except Exception as e:
            logger.error(f"Error searching PubMed for query '{query}': {e}")
            return []

    def get_annotations_by_search(self, query: str, max_pages: int | None = None, tracker=None) -> dict[str, Any]:
        """Get PubTator annotations by searching with caching support

        Args:
            query: Search query
            max_pages: Maximum number of pages to fetch (None = use configured limit)

        Returns:
            Dictionary mapping gene symbols to annotation data
        """
        # Check cache first
        if self.use_cache:
            cached_data = self.cache.get_cached_data(query)
            if cached_data:
                logger.info(f"Using cached data for query: {query[:50]}...")
                return cached_data

        gene_annotations = {}
        all_pmids = []

        # Get total pages first
        total_pages = 1
        try:
            response = self.client.get(
                "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/",
                params={"text": query, "page": 1},
            )
            if response.status_code == 200:
                data = response.json()
                total_pages = data.get("total_pages", 1)
                logger.info(f"PubTator search has {total_pages} total pages")
        except Exception as e:
            logger.error(f"Error getting total pages: {e}")

        # Determine how many pages to actually process
        if max_pages is None:
            max_pages = min(self.max_pages_per_run, total_pages)  # Use configured limit
        else:
            max_pages = min(max_pages, total_pages)

        logger.info(f"Will process {max_pages} pages (configured limit: {self.max_pages_per_run})")

        # Step 1: Search for PMIDs using PubTator3 search API (all pages)
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

                # Log progress every 10 pages
                if page % 10 == 0 or page == 1:
                    logger.info(f"Processing page {page}/{max_pages}: found {len(all_pmids)} PMIDs so far")
                    if tracker:
                        tracker.update(current_page=page, operation=f"Fetching page {page}/{max_pages}")

                # Rate limiting
                time.sleep(settings.PUBTATOR_RATE_LIMIT_DELAY)

            except Exception as e:
                logger.error(f"Error fetching PubTator3 search page {page}: {e}")
                break

        # Step 2: Get annotations for collected PMIDs (in batches)
        if all_pmids:
            batch_size = settings.PUBTATOR_BATCH_SIZE
            total_batches = (len(all_pmids) + batch_size - 1) // batch_size
            logger.info(f"Processing {len(all_pmids)} PMIDs in {total_batches} batches of {batch_size}")

            for batch_num, i in enumerate(range(0, len(all_pmids), batch_size), 1):
                batch_pmids = all_pmids[i : i + batch_size]
                pmids_str = ",".join(batch_pmids)

                if batch_num % 5 == 0 or batch_num == 1:
                    logger.info(f"Processing annotation batch {batch_num}/{total_batches}")
                    if tracker:
                        tracker.update(operation=f"Processing annotations batch {batch_num}/{total_batches}")

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
                    time.sleep(settings.PUBTATOR_RATE_LIMIT_DELAY * 1.5)  # Slightly longer for batch requests

                except Exception as e:
                    logger.error(f"Error fetching PubTator3 annotations for batch: {e}")

        # Convert sets to lists
        for gene_data in gene_annotations.values():
            gene_data["pmids"] = list(gene_data["pmids"])
            gene_data["ncbi_gene_ids"] = list(gene_data["ncbi_gene_ids"])

        # Cache the results if enabled
        if self.use_cache and gene_annotations:
            # Mark as complete if we processed all available pages
            is_complete = (max_pages >= total_pages) if 'total_pages' in locals() else False
            self.cache.save_cache(query, gene_annotations, complete=is_complete)
            logger.info(f"Cached {len(gene_annotations)} genes for future use")

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


def update_pubtator_data(db: Session, tracker=None) -> dict[str, Any]:
    """Update database with PubTator literature mining data

    Args:
        db: Database session
        tracker: Optional progress tracker (created if not provided)

    Returns:
        Statistics about the update
    """
    from app.core.progress_tracker import ProgressTracker

    # Initialize progress tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "PubTator")

    client = PubTatorClient()
    stats = {
        "source": "PubTator",
        "queries_processed": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "evidence_updated": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Start tracking
        tracker.start("Initializing PubTator search")

        # Use single comprehensive query like kidney-genetics-v1
        # Get configured number of pages from settings
        max_pages = settings.PUBTATOR_MAX_PAGES
        logger.info(f"Searching PubTator with comprehensive kidney disease query for {max_pages} pages")
        tracker.update(operation="Fetching PubTator data", total_pages=max_pages, current_page=0)

        all_gene_data = client.get_annotations_by_search(client.kidney_query, max_pages=max_pages, tracker=tracker)
        stats["queries_processed"] = 1

        if not all_gene_data:
            logger.warning("No gene data found from PubTator search")
            tracker.complete("No data found")
            return stats

        logger.info(f"Found {len(all_gene_data)} unique genes from PubTator search")

        # Filter genes by minimum publication threshold
        filtered_genes = {symbol: data for symbol, data in all_gene_data.items()
                         if len(data.get("pmids", [])) >= settings.PUBTATOR_MIN_PUBLICATIONS}
        logger.info(f"Filtered to {len(filtered_genes)} genes with >= {settings.PUBTATOR_MIN_PUBLICATIONS} publications")

        # Batch normalize all genes first for efficiency
        logger.info(f"Starting batch normalization of {len(filtered_genes)} genes")
        tracker.update(
            total_items=len(filtered_genes),
            current_item=0,
            operation=f"Batch normalizing {len(filtered_genes)} genes via HGNC"
        )

        # Use batch normalization for efficiency
        from app.core.gene_normalization import normalize_genes_batch

        # Prepare data for batch normalization
        gene_symbols = list(filtered_genes.keys())
        original_data_list = [
            {
                "pmids": list(data["pmids"])[:10],  # Sample of PMIDs
                "publication_count": len(data["pmids"]),
                "total_mentions": data["mentions"]
            }
            for data in filtered_genes.values()
        ]

        # Batch normalize genes in smaller batches to avoid API issues
        batch_size = 20  # Smaller batch size for reliability
        normalization_results = {}

        for i in range(0, len(gene_symbols), batch_size):
            batch_symbols = gene_symbols[i:i+batch_size]
            batch_data = original_data_list[i:i+batch_size]

            logger.info(f"Normalizing batch {i//batch_size + 1}/{(len(gene_symbols) + batch_size - 1)//batch_size} ({len(batch_symbols)} genes)")

            try:
                batch_results = normalize_genes_batch(
                    db=db,
                    gene_texts=batch_symbols,
                    source_name="PubTator",
                    original_data_list=batch_data
                )
                normalization_results.update(batch_results)
            except Exception as e:
                logger.error(f"Error normalizing batch: {e}")
                # Continue with next batch even if one fails
                continue

        logger.info(f"Batch normalization complete. Processing {len(normalization_results)} results")
        tracker.update(operation=f"Storing {len(normalization_results)} genes in database")

        # Process normalization results and store in database
        processed_count = 0
        for symbol, data in filtered_genes.items():
            processed_count += 1
            pmid_list = list(data["pmids"])

            # Update progress every 10 genes
            if processed_count % 10 == 0 or processed_count == 1:
                logger.info(f"Storing gene {processed_count}/{len(filtered_genes)}: {symbol}")
                tracker.update(
                    current_item=processed_count,
                    operation=f"Storing gene {symbol} ({processed_count}/{len(filtered_genes)})"
                )

            stats["genes_processed"] += 1

            # Get normalization result for this gene
            normalization_result = normalization_results.get(symbol, {})

            if not normalization_result:
                logger.warning(f"No normalization result for gene '{symbol}'")
                stats["errors"] += 1
                continue

            if normalization_result.get("status") == "normalized":
                # Gene successfully normalized - get or create
                # Check by both symbol and HGNC ID to avoid duplicates
                gene = gene_crud.get_by_symbol(db, normalization_result["approved_symbol"])
                if not gene and normalization_result.get("hgnc_id"):
                    gene = gene_crud.get_by_hgnc_id(db, normalization_result["hgnc_id"])

                if not gene:
                    # Create new gene with proper HGNC data
                    try:
                        gene_create = GeneCreate(
                            approved_symbol=normalization_result["approved_symbol"],
                            hgnc_id=normalization_result["hgnc_id"],
                            aliases=normalization_result.get("aliases", []),
                        )
                        gene = gene_crud.create(db, gene_create)
                        stats["genes_created"] += 1
                        tracker.update(items_added=1)
                        logger.debug(f"Created normalized gene: {normalization_result['approved_symbol']} ({normalization_result['hgnc_id']})")
                    except Exception as e:
                        logger.error(f"Error creating normalized gene {normalization_result['approved_symbol']}: {e}")
                        stats["errors"] += 1
                        tracker.update(items_failed=1)
                        continue

            elif normalization_result.get("status") == "requires_manual_review":
                # Gene sent to staging for manual review - skip for now
                logger.info(f"Gene '{symbol}' sent to staging (ID: {normalization_result.get('staging_id')}) for manual review")
                continue

            else:
                # Normalization error - skip gene
                logger.error(f"Failed to normalize gene '{symbol}': {normalization_result.get('error', 'Unknown error')}")
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
                    stats["evidence_updated"] += 1
                    tracker.update(items_updated=1)
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
                    tracker.update(items_added=1)

                db.commit()

            except Exception as e:
                logger.error(f"Error saving PubTator evidence for gene {symbol}: {e}")
                db.rollback()
                stats["errors"] += 1
                tracker.update(items_failed=1)

        # Complete tracking
        tracker.complete(f"Processed {stats['genes_processed']} genes successfully")

    except Exception as e:
        logger.error(f"PubTator update failed: {e}")
        tracker.error(str(e))
        stats["errors"] += 1

    finally:
        client.close()

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"PubTator update complete: {stats['genes_processed']} genes processed, "
        f"{stats['genes_created']} new genes created, "
        f"{stats['evidence_created']} new evidence records, "
        f"{stats['evidence_updated']} updated evidence records, "
        f"Duration: {stats.get('duration', 0):.1f}s"
    )

    return stats


# Alias for backward compatibility with tests
def run_pubtator_pipeline(db: Session, max_pages: int = None, tracker=None) -> dict[str, Any]:
    """Alias for update_pubtator_data for test compatibility"""
    return update_pubtator_data(db, tracker)
