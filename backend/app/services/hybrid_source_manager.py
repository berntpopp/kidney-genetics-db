"""
Hybrid Source CRUD Manager
Handles source-specific operations for DiagnosticPanels and Literature
"""
import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger
from app.models.gene import GeneEvidence
from app.models.static_sources import StaticSource, StaticSourceAudit

logger = get_logger(__name__)


class HybridSourceManager(ABC):
    """Base class for hybrid source operations"""

    def __init__(self, db: Session):
        self.db = db
        self._executor = ThreadPoolExecutor(max_workers=4)

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Source name (DiagnosticPanels or Literature)"""
        pass

    @abstractmethod
    async def delete_by_identifier(
        self, identifier: str, user: str
    ) -> dict[str, Any]:
        """Delete all evidence for given identifier (provider or PMID)"""
        pass

    async def _create_audit_log(
        self, action: str, details: dict, user: str, upload_id: int | None = None
    ) -> None:
        """Create audit trail entry"""
        source = self.db.query(StaticSource).filter(
            StaticSource.source_name == self.source_name
        ).first()

        if not source:
            await logger.warning(
                "StaticSource not found for audit",
                source_name=self.source_name
            )
            return

        audit = StaticSourceAudit(
            source_id=source.id,
            upload_id=upload_id,
            action=action,
            details=details,
            performed_by=user,
            performed_at=datetime.utcnow()
        )
        self.db.add(audit)

    async def _invalidate_gene_caches(self, gene_ids: list[int]) -> None:
        """Invalidate caches for affected genes"""
        cache_service = get_cache_service(self.db)

        for gene_id in gene_ids:
            await cache_service.delete(f"{gene_id}:*", namespace="annotations")
            await cache_service.delete(f"{gene_id}:*", namespace="evidence")

        await logger.info(
            "Invalidated caches for affected genes",
            gene_count=len(gene_ids)
        )

    async def _recalculate_evidence_scores(self, gene_ids: list[int]) -> None:
        """Recalculate evidence scores using thread pool"""
        loop = asyncio.get_event_loop()

        # Run in thread pool to avoid blocking event loop
        await loop.run_in_executor(
            self._executor,
            self._recalculate_sync,
            gene_ids
        )

    def _recalculate_sync(self, gene_ids: list[int]) -> None:
        """Synchronous recalculation in thread pool"""
        # For now, trigger full recalculation
        # TODO: Optimize to only recalculate affected genes
        from app.pipeline.aggregate import update_all_curations
        update_all_curations(self.db)

        logger.sync_info(
            "Evidence recalculation complete",
            affected_genes=len(gene_ids)
        )


class DiagnosticPanelsManager(HybridSourceManager):
    """Manager for DiagnosticPanels source"""

    @property
    def source_name(self) -> str:
        return "DiagnosticPanels"

    async def delete_by_identifier(
        self, provider_name: str, user: str
    ) -> dict[str, Any]:
        """Delete all evidence from a specific provider"""

        await logger.info(
            "Starting provider deletion",
            provider=provider_name,
            user=user
        )

        # Get all affected genes WITH row-level locking
        stmt = (
            select(GeneEvidence)
            .where(
                GeneEvidence.source_name == self.source_name,
                GeneEvidence.evidence_data['providers'].astext.contains(provider_name)
            )
            .with_for_update()  # CRITICAL: Prevent race conditions
            .options(selectinload(GeneEvidence.gene))
        )

        affected_evidence = self.db.execute(stmt).scalars().all()
        affected_gene_ids = []
        genes_with_evidence_removed = 0
        genes_fully_removed = 0

        for evidence in affected_evidence:
            data = evidence.evidence_data or {}
            providers = set(data.get("providers", []))

            if provider_name not in providers:
                continue

            providers.discard(provider_name)
            affected_gene_ids.append(evidence.gene_id)

            if not providers:
                # No providers left - delete entire evidence record
                self.db.delete(evidence)
                genes_fully_removed += 1
                await logger.debug(
                    "Removed evidence record",
                    gene_id=evidence.gene_id,
                    symbol=evidence.gene.approved_symbol if evidence.gene else "unknown"
                )
            else:
                # Update without this provider
                data["providers"] = sorted(providers)
                data["provider_count"] = len(providers)
                evidence.evidence_data = data
                flag_modified(evidence, "evidence_data")
                genes_with_evidence_removed += 1

                await logger.debug(
                    "Updated evidence record",
                    gene_id=evidence.gene_id,
                    remaining_providers=len(providers)
                )

        # Create audit log
        await self._create_audit_log(
            action="delete_provider",
            details={
                "provider": provider_name,
                "genes_affected": len(set(affected_gene_ids)),
                "evidence_removed": genes_with_evidence_removed,
                "evidence_deleted": genes_fully_removed
            },
            user=user
        )

        # Commit changes
        self.db.commit()

        # Invalidate caches
        await self._invalidate_gene_caches(list(set(affected_gene_ids)))

        # Recalculate evidence scores in background
        await self._recalculate_evidence_scores(list(set(affected_gene_ids)))

        stats = {
            "status": "success",
            "provider": provider_name,
            "genes_affected": len(set(affected_gene_ids)),
            "evidence_updated": genes_with_evidence_removed,
            "evidence_deleted": genes_fully_removed
        }

        await logger.info("Provider deletion complete", stats=stats)
        return stats


class LiteratureManager(HybridSourceManager):
    """Manager for Literature source"""

    @property
    def source_name(self) -> str:
        return "Literature"

    async def delete_by_identifier(
        self, pmid: str, user: str
    ) -> dict[str, Any]:
        """Delete all evidence from a specific publication (PMID)"""

        await logger.info(
            "Starting publication deletion",
            pmid=pmid,
            user=user
        )

        # Get all affected genes WITH row-level locking
        stmt = (
            select(GeneEvidence)
            .where(
                GeneEvidence.source_name == self.source_name,
                GeneEvidence.evidence_data['publications'].astext.contains(pmid)
            )
            .with_for_update()  # CRITICAL: Prevent race conditions
            .options(selectinload(GeneEvidence.gene))
        )

        affected_evidence = self.db.execute(stmt).scalars().all()
        affected_gene_ids = []
        genes_with_evidence_removed = 0
        genes_fully_removed = 0

        for evidence in affected_evidence:
            data = evidence.evidence_data or {}
            publications = set(data.get("publications", []))

            if pmid not in publications:
                continue

            publications.discard(pmid)
            affected_gene_ids.append(evidence.gene_id)

            # Remove publication details
            pub_details = data.get("publication_details", {})
            pub_details.pop(pmid, None)

            if not publications:
                # No publications left - delete entire evidence record
                self.db.delete(evidence)
                genes_fully_removed += 1
                await logger.debug(
                    "Removed evidence record",
                    gene_id=evidence.gene_id,
                    symbol=evidence.gene.approved_symbol if evidence.gene else "unknown"
                )
            else:
                # Update without this publication
                data["publications"] = sorted(publications)
                data["publication_count"] = len(publications)
                data["publication_details"] = pub_details
                evidence.evidence_data = data
                flag_modified(evidence, "evidence_data")
                genes_with_evidence_removed += 1

                await logger.debug(
                    "Updated evidence record",
                    gene_id=evidence.gene_id,
                    remaining_publications=len(publications)
                )

        # Create audit log
        await self._create_audit_log(
            action="delete_publication",
            details={
                "pmid": pmid,
                "genes_affected": len(set(affected_gene_ids)),
                "evidence_removed": genes_with_evidence_removed,
                "evidence_deleted": genes_fully_removed
            },
            user=user
        )

        # Commit changes
        self.db.commit()

        # Invalidate caches
        await self._invalidate_gene_caches(list(set(affected_gene_ids)))

        # Recalculate evidence scores in background
        await self._recalculate_evidence_scores(list(set(affected_gene_ids)))

        stats = {
            "status": "success",
            "pmid": pmid,
            "genes_affected": len(set(affected_gene_ids)),
            "evidence_updated": genes_with_evidence_removed,
            "evidence_deleted": genes_fully_removed
        }

        await logger.info("Publication deletion complete", stats=stats)
        return stats


def get_source_manager(source_name: str, db: Session) -> HybridSourceManager:
    """Factory function to get appropriate manager"""
    if source_name == "DiagnosticPanels":
        return DiagnosticPanelsManager(db)
    elif source_name == "Literature":
        return LiteratureManager(db)
    else:
        raise ValueError(f"Unknown hybrid source: {source_name}")
