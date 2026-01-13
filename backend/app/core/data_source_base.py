"""
Abstract base class for all data source clients.

This module provides a unified architecture for data source implementations,
enforcing consistent patterns for fetching, processing, and storing data.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker
from app.crud.gene import gene_crud
from app.models.gene import Gene, GeneEvidence
from app.schemas.gene import GeneCreate

logger = get_logger(__name__)


class DataSourceClient(ABC):
    """
    Abstract base class for all data source clients.

    Implements the Template Method pattern to ensure consistent data processing
    workflows across all data sources while allowing specific implementations
    to customize the data fetching and processing logic.
    """

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
    ):
        """Initialize the data source client with shared services."""
        # BUGFIX: Removed the faulty 'or' logic. The dependencies are now
        # correctly created and passed in by the UnifiedDataSource or TaskMixin.
        # This constructor should simply assign them.
        self.cache_service = cache_service
        self.http_client = http_client
        self.db_session = db_session

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        pass

    @property
    @abstractmethod
    def namespace(self) -> str:
        """Return the cache namespace for this data source."""
        pass

    @abstractmethod
    async def fetch_raw_data(
        self, tracker: "ProgressTracker | None" = None, mode: str = "smart"
    ) -> Any:
        """
        Fetch raw data from the external source.

        Args:
            tracker: Progress tracker for real-time updates
            mode: Update mode - "smart" (incremental) or "full" (complete refresh)

        Returns:
            Raw data in whatever format the source provides
        """
        pass

    @abstractmethod
    async def process_data(self, raw_data: Any) -> dict[str, Any]:
        """
        Process raw data into structured gene information.

        Args:
            raw_data: Raw data from fetch_raw_data()

        Returns:
            Dictionary mapping gene symbols to their aggregated data
        """
        pass

    @abstractmethod
    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """
        Check if a data record is kidney-related.

        Args:
            record: Individual data record from the source

        Returns:
            True if the record is kidney-related
        """
        pass

    async def _clear_existing_entries(self, db: Session) -> int:
        """Clear existing entries for this source (for full mode).

        Returns:
            Number of deleted entries
        """
        deleted: int = (
            db.query(GeneEvidence).filter(GeneEvidence.source_name == self.source_name).delete()
        )
        db.commit()
        logger.sync_info(f"Cleared {deleted} existing {self.source_name} entries")
        return deleted

    async def update_data(
        self, db: Session, tracker: ProgressTracker, mode: str = "smart"
    ) -> dict[str, Any]:
        """
        Template method for the complete data update process.

        This method implements the common workflow:
        1. Initialize statistics
        2. Clear existing data if full mode
        3. Fetch raw data from source
        4. Process data into gene information
        5. Store processed data in database
        6. Return comprehensive statistics

        Args:
            db: Database session
            tracker: Progress tracker for real-time updates
            mode: Update mode - "smart" (incremental) or "full" (complete refresh)

        Returns:
            Dictionary with comprehensive update statistics
        """
        stats = self._initialize_stats()

        try:
            tracker.start(f"Starting {self.source_name} update (mode: {mode})")
            logger.sync_info("Starting data update", source_name=self.source_name, mode=mode)

            # Clear existing entries if full mode
            if mode == "full":
                tracker.update(operation="Clearing existing entries")
                deleted = await self._clear_existing_entries(db)
                stats["entries_deleted"] = deleted
                logger.sync_info(f"Full mode: deleted {deleted} existing entries")

            # Step 1: Fetch raw data
            tracker.update(operation="Fetching data from source")
            logger.sync_info("Fetching data from source", source_name=self.source_name)

            # Check if fetch_raw_data accepts mode parameter
            import inspect

            sig = inspect.signature(self.fetch_raw_data)
            if "mode" in sig.parameters:
                raw_data = await self.fetch_raw_data(tracker=tracker, mode=mode)
            else:
                raw_data = await self.fetch_raw_data(tracker=tracker)
            stats["data_fetched"] = True

            # Step 2: Process data
            tracker.update(operation="Processing and filtering data")
            logger.sync_info("Processing data", source_name=self.source_name)
            processed_data = await self.process_data(raw_data)
            stats["genes_found"] = len(processed_data)

            if not processed_data:
                logger.sync_warning("No genes found in data", source_name=self.source_name)
                tracker.complete(f"{self.source_name} update completed: 0 genes found")
                return stats

            # Step 3: Store in database
            tracker.update(operation="Storing genes in database")
            logger.sync_info(
                "Storing genes in database",
                source_name=self.source_name,
                gene_count=len(processed_data),
            )
            await self._store_genes_in_database(db, processed_data, stats, tracker)

            # Step 4: Finalize
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            stats["duration"] = (
                datetime.fromisoformat(stats["completed_at"])
                - datetime.fromisoformat(stats["started_at"])
            ).total_seconds()

            # Get the actual total counts from the database
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT gene_id) as total_genes,
                        COUNT(*) as total_evidence
                    FROM gene_evidence
                    WHERE source_name = :source_name
                """),
                {"source_name": self.source_name},
            ).fetchone()

            total_genes = result[0] if result else 0
            total_evidence = result[1] if result else 0

            logger.sync_info(
                "Data update completed",
                source_name=self.source_name,
                total_genes=total_genes,
                total_evidence=total_evidence,
                genes_created=stats["genes_created"],
                evidence_created=stats["evidence_created"],
            )

            tracker.complete(
                f"{self.source_name}: {total_genes} genes, {total_evidence} evidence "
                f"(+{stats['genes_created']} new genes, +{stats['evidence_created']} new evidence)"
            )

            return stats

        except Exception as e:
            logger.sync_error("Data update failed", source_name=self.source_name, error=str(e))
            tracker.error(str(e))
            stats["error"] = str(e)
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            raise

    def _initialize_stats(self) -> dict[str, Any]:
        """Initialize statistics dictionary with common fields."""
        return {
            "source": self.source_name,
            "data_fetched": False,
            "genes_found": 0,
            "genes_processed": 0,
            "genes_created": 0,
            "genes_updated": 0,
            "evidence_created": 0,
            "evidence_updated": 0,
            "errors": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "duration": None,
        }

    async def _store_genes_in_database(
        self,
        db: Session,
        gene_data: dict[str, Any],
        stats: dict[str, Any],
        tracker: ProgressTracker,
    ) -> None:
        """
        Store processed gene data in the database.

        This method handles the common pattern of:
        1. Getting or creating genes
        2. Creating/updating evidence records
        3. Tracking statistics and progress

        Args:
            db: Database session
            gene_data: Processed gene data from process_data()
            stats: Statistics dictionary to update
            tracker: Progress tracker for updates
        """
        from app.core.gene_normalizer import normalize_genes_batch_async

        # Get list of gene symbols for batch normalization
        gene_symbols = list(gene_data.keys())

        # Normalize gene symbols in batches
        batch_size = 50
        total_batches = (len(gene_symbols) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(gene_symbols))
            batch_symbols = gene_symbols[start_idx:end_idx]

            tracker.update(operation=f"Processing gene batch {batch_num + 1}/{total_batches}")

            # Normalize gene symbols
            normalization_results = await normalize_genes_batch_async(
                db, batch_symbols, self.source_name
            )

            # Process each gene in the batch
            for symbol in batch_symbols:
                try:
                    stats["genes_processed"] += 1
                    data = gene_data[symbol]

                    # Get normalized gene info
                    norm_result = normalization_results.get(symbol, {})
                    if norm_result.get("status") != "normalized":
                        logger.sync_debug("Skipping unnormalized gene", symbol=symbol)
                        continue

                    # Get or create gene
                    gene = await self._get_or_create_gene(db, norm_result, symbol, stats)

                    if gene:
                        # Create or update evidence
                        await self._create_or_update_evidence(db, gene, data, stats)

                except Exception as e:
                    logger.sync_error("Error processing gene", symbol=symbol, error=str(e))
                    stats["errors"] += 1

            # Commit batch
            db.commit()

    async def _get_or_create_gene(
        self, db: Session, norm_result: dict[str, Any], original_symbol: str, stats: dict[str, Any]
    ) -> Gene | None:
        """Get existing gene or create new one from normalization result."""
        approved_symbol = norm_result.get("approved_symbol")
        hgnc_id = norm_result.get("hgnc_id")

        if not approved_symbol:
            return None

        # Try to get existing gene by symbol first
        gene = gene_crud.get_by_symbol(db, approved_symbol)

        # If not found by symbol, try by HGNC ID (in case of symbol changes)
        if not gene and hgnc_id:
            gene = db.query(Gene).filter(Gene.hgnc_id == hgnc_id).first()

        if not gene:
            try:
                gene_create = GeneCreate(
                    approved_symbol=approved_symbol,
                    hgnc_id=hgnc_id,
                    aliases=[original_symbol] if original_symbol != approved_symbol else [],
                )
                gene = gene_crud.create(db, gene_create)
                stats["genes_created"] += 1
                logger.sync_debug(
                    "Created new gene", approved_symbol=approved_symbol, hgnc_id=hgnc_id
                )
            except Exception as e:
                # Handle race condition: another task may have created the gene
                if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                    logger.sync_debug(
                        "Gene constraint violation, retrying fetch",
                        approved_symbol=approved_symbol,
                        hgnc_id=hgnc_id,
                    )

                    # Try to get the gene that was created by another task
                    # Check both symbol and HGNC ID constraints
                    gene = gene_crud.get_by_symbol(db, approved_symbol)
                    if not gene and hgnc_id:
                        gene = db.query(Gene).filter(Gene.hgnc_id == hgnc_id).first()

                    if gene:
                        stats["genes_updated"] += 1
                        logger.sync_debug(
                            "Found gene after race condition",
                            approved_symbol=gene.approved_symbol,
                            hgnc_id=gene.hgnc_id,
                        )
                    else:
                        logger.sync_error(
                            "Race condition: gene still not found after creation attempt",
                            approved_symbol=approved_symbol,
                            hgnc_id=hgnc_id,
                        )
                        return None
                else:
                    logger.sync_error(
                        "Error creating gene",
                        approved_symbol=approved_symbol,
                        hgnc_id=hgnc_id,
                        error=str(e),
                    )
                    return None
        else:
            stats["genes_updated"] += 1

        return gene

    async def _create_or_update_evidence(
        self, db: Session, gene: Gene, evidence_data: dict[str, Any], stats: dict[str, Any]
    ) -> None:
        """Create or update evidence record for a gene.

        Ensures ONE evidence record per source per gene.
        Updates existing evidence with new data when found.
        """
        try:
            # Generate source detail for the evidence
            source_detail = self._get_source_detail(evidence_data)

            # Check if evidence already exists (ONE per source per gene)
            existing = (
                db.query(GeneEvidence)
                .filter(
                    GeneEvidence.gene_id == gene.id,
                    GeneEvidence.source_name == self.source_name,
                )
                .first()
            )

            # Clean evidence data for JSON storage
            clean_evidence = self._clean_data_for_json(evidence_data)

            if existing:
                # Update existing evidence with new data
                existing.source_detail = source_detail  # Update detail
                existing.evidence_data = clean_evidence
                existing.evidence_date = datetime.now(timezone.utc).date()
                db.add(existing)
                stats["evidence_updated"] += 1
                logger.sync_debug(
                    "Updated evidence for gene",
                    gene_symbol=gene.approved_symbol,
                    source_name=self.source_name,
                )
            else:
                # Create new evidence with proper constraint handling
                try:
                    evidence = GeneEvidence(
                        gene_id=gene.id,
                        source_name=self.source_name,
                        source_detail=source_detail,
                        evidence_data=clean_evidence,
                        evidence_date=datetime.now(timezone.utc).date(),
                    )
                    db.add(evidence)
                    db.flush()  # Force constraint check before commit
                    stats["evidence_created"] += 1
                    logger.sync_debug(
                        "Created evidence for gene",
                        gene_symbol=gene.approved_symbol,
                        source_name=self.source_name,
                    )
                except Exception as constraint_error:
                    # Handle race condition: another process may have created the evidence
                    if (
                        "unique constraint" in str(constraint_error).lower()
                        or "duplicate key" in str(constraint_error).lower()
                    ):
                        db.rollback()  # Rollback failed transaction
                        logger.sync_debug(
                            "Race condition detected for gene, retrying...",
                            gene_symbol=gene.approved_symbol,
                        )

                        # Try to get the evidence that was created by another process
                        existing = (
                            db.query(GeneEvidence)
                            .filter(
                                GeneEvidence.gene_id == gene.id,
                                GeneEvidence.source_name == self.source_name,
                            )
                            .first()
                        )

                        if existing:
                            # Update with our data
                            existing.source_detail = source_detail
                            existing.evidence_data = clean_evidence
                            existing.evidence_date = datetime.now(timezone.utc).date()
                            db.add(existing)
                            stats["evidence_updated"] += 1
                            logger.sync_debug(
                                "Updated evidence after race condition",
                                gene_symbol=gene.approved_symbol,
                            )
                        else:
                            # Should not happen, but log if it does
                            logger.sync_error(
                                "Evidence not found after race condition",
                                gene_symbol=gene.approved_symbol,
                            )
                            stats["errors"] += 1
                    else:
                        # Other constraint errors should be raised
                        logger.sync_error(
                            "Constraint error for gene",
                            gene_symbol=gene.approved_symbol,
                            error=str(constraint_error),
                        )
                        stats["errors"] += 1
                        raise

        except Exception as e:
            logger.sync_error(
                "Error creating/updating evidence for gene",
                gene_symbol=gene.approved_symbol,
                error=str(e),
            )
            stats["errors"] += 1

    def _clean_data_for_json(self, data: Any) -> Any:
        """Clean data by replacing NaN/None values for JSON serialization."""
        if isinstance(data, dict):
            return {k: self._clean_data_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data_for_json(item) for item in data]
        elif isinstance(data, set):
            return list(data)  # Convert sets to lists
        elif str(data).lower() in ("nan", "none", "null") or data is None:
            return ""
        else:
            return data

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate a source detail string from evidence data.

        Subclasses can override this to provide source-specific details.
        """
        return f"Data from {self.source_name}"


def get_data_source_client(source_name: str, **kwargs: Any) -> DataSourceClient:
    """
    Factory function to get appropriate data source client.

    Args:
        source_name: Name of the data source
        **kwargs: Additional arguments for client initialization

    Returns:
        Appropriate DataSourceClient instance

    Raises:
        ValueError: If source_name is not recognized
    """
    source_map = {
        # REFACTORED: Updated to use unified sources
        "GenCC": "app.pipeline.sources.unified.gencc.GenCCUnifiedSource",
        "PubTator": "app.pipeline.sources.unified.pubtator.PubTatorUnifiedSource",
        "PanelApp": "app.pipeline.sources.unified.panelapp.PanelAppUnifiedSource",
        "ClinGen": "app.pipeline.sources.unified.clingen.ClinGenUnifiedSource",
        "HPO": "app.pipeline.sources.unified.hpo.HPOUnifiedSource",
    }

    if source_name not in source_map:
        raise ValueError(f"Unknown data source: {source_name}")

    # Dynamic import and instantiation
    module_path, class_name = source_map[source_name].rsplit(".", 1)

    try:
        import importlib
        from typing import cast

        module = importlib.import_module(module_path)
        client_class = getattr(module, class_name)
        return cast(DataSourceClient, client_class(**kwargs))
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Could not import {source_name} client: {e}") from e
