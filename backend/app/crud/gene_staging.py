"""
CRUD operations for gene normalization staging
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models.gene_staging import GeneNormalizationLog, GeneNormalizationStaging


class GeneNormalizationStagingCRUD:
    """CRUD operations for gene normalization staging"""

    def create_staging_record(
        self,
        db: Session,
        original_text: str,
        source_name: str,
        normalization_log: dict[str, Any],
        original_data: dict[str, Any] | None = None,
    ) -> GeneNormalizationStaging:
        """Create a new staging record for manual review"""

        # Calculate priority score based on various factors
        priority_score = self._calculate_priority_score(
            original_text, source_name, normalization_log
        )

        # Check if this might be a high-value gene requiring expert review
        requires_expert = self._requires_expert_review(original_text, source_name)

        staging_record = GeneNormalizationStaging(
            original_text=original_text,
            source_name=source_name,
            original_data=original_data or {},
            normalization_log=normalization_log,
            status="pending_review",
            priority_score=priority_score,
            requires_expert_review=requires_expert,
        )

        db.add(staging_record)
        db.commit()
        db.refresh(staging_record)

        return staging_record

    def get_pending_reviews(
        self, db: Session, limit: int = 50, source_filter: str | None = None
    ) -> list[GeneNormalizationStaging]:
        """Get genes pending manual review, ordered by priority"""

        query = db.query(GeneNormalizationStaging).filter(
            GeneNormalizationStaging.status == "pending_review"
        )

        if source_filter:
            query = query.filter(GeneNormalizationStaging.source_name == source_filter)

        result: list[GeneNormalizationStaging] = (
            query.order_by(
                desc(GeneNormalizationStaging.priority_score), GeneNormalizationStaging.created_at
            )
            .limit(limit)
            .all()
        )
        return result

    def approve_staging_record(
        self,
        db: Session,
        staging_id: int,
        approved_symbol: str,
        hgnc_id: str,
        aliases: list[str] | None = None,
        reviewer: str = "system",
        notes: str | None = None,
    ) -> GeneNormalizationStaging:
        """Approve a staging record with manual corrections"""

        staging_record: GeneNormalizationStaging | None = (
            db.query(GeneNormalizationStaging)
            .filter(GeneNormalizationStaging.id == staging_id)
            .first()
        )

        if not staging_record:
            raise ValueError(f"Staging record {staging_id} not found")

        staging_record.status = "approved"
        staging_record.reviewed_by = reviewer
        staging_record.reviewed_at = datetime.now(timezone.utc)
        staging_record.review_notes = notes
        staging_record.manual_approved_symbol = approved_symbol
        staging_record.manual_hgnc_id = hgnc_id
        staging_record.manual_aliases = aliases or []
        staging_record.resolution_method = "manual_correction"

        db.add(staging_record)
        db.commit()
        db.refresh(staging_record)

        return staging_record

    def reject_staging_record(
        self, db: Session, staging_id: int, reviewer: str = "system", notes: str | None = None
    ) -> GeneNormalizationStaging:
        """Reject a staging record (not a valid gene)"""

        staging_record: GeneNormalizationStaging | None = (
            db.query(GeneNormalizationStaging)
            .filter(GeneNormalizationStaging.id == staging_id)
            .first()
        )

        if not staging_record:
            raise ValueError(f"Staging record {staging_id} not found")

        staging_record.status = "rejected"
        staging_record.reviewed_by = reviewer
        staging_record.reviewed_at = datetime.now(timezone.utc)
        staging_record.review_notes = notes
        staging_record.resolution_method = "rejected_invalid"

        db.add(staging_record)
        db.commit()
        db.refresh(staging_record)

        return staging_record

    def get_staging_stats(self, db: Session) -> dict[str, Any]:
        """Get statistics about staging records"""

        total_pending = (
            db.query(GeneNormalizationStaging)
            .filter(GeneNormalizationStaging.status == "pending_review")
            .count()
        )

        total_approved = (
            db.query(GeneNormalizationStaging)
            .filter(GeneNormalizationStaging.status == "approved")
            .count()
        )

        total_rejected = (
            db.query(GeneNormalizationStaging)
            .filter(GeneNormalizationStaging.status == "rejected")
            .count()
        )

        # By source breakdown
        source_stats = {}
        sources = db.query(GeneNormalizationStaging.source_name).distinct().all()
        for (source,) in sources:
            source_pending = (
                db.query(GeneNormalizationStaging)
                .filter(
                    and_(
                        GeneNormalizationStaging.source_name == source,
                        GeneNormalizationStaging.status == "pending_review",
                    )
                )
                .count()
            )
            source_stats[source] = source_pending

        return {
            "total_pending": total_pending,
            "total_approved": total_approved,
            "total_rejected": total_rejected,
            "by_source": source_stats,
        }

    def _calculate_priority_score(
        self, original_text: str, source_name: str, normalization_log: dict[str, Any]
    ) -> int:
        """Calculate priority score for manual review (higher = more important)"""
        score = 0

        # Base score by source reliability
        source_scores = {
            "PanelApp": 100,  # High priority - clinical panels
            "ClinGen": 95,  # High priority - expert curated
            "HPO": 85,  # High priority - phenotype associations
            "GenCC": 80,  # High priority - harmonized data
            "DiagnosticPanels": 75,  # High priority - commercial panels
            "PubTator": 20,  # Lower priority - literature mining
        }
        score += source_scores.get(source_name, 10)

        # Boost score for genes that almost matched
        steps = normalization_log.get("steps", [])
        for step in steps:
            if "HGNC API" in step and "failed" in step:
                score += 20  # Was close to matching
            if "Fuzzy matching" in step and "failed" in step:
                score += 10  # Had some similarity

        # Boost score for clean-looking gene symbols
        if original_text and len(original_text.strip()) > 1:
            clean_text = original_text.strip().upper()
            if clean_text.isalpha() and len(clean_text) >= 2:
                score += 15  # Looks like a real gene symbol

        # Boost score for common gene patterns
        common_patterns = ["PKD", "COL", "HNF", "SLC", "ATP", "UMOD"]
        for pattern in common_patterns:
            if pattern in original_text.upper():
                score += 25

        return min(score, 200)  # Cap at 200

    def _requires_expert_review(self, original_text: str, source_name: str) -> bool:
        """Determine if gene requires expert review"""

        # Clinical sources always need expert review
        if source_name in ["PanelApp", "ClinGen"]:
            return True

        # Known important kidney genes
        important_genes = [
            "PKD1",
            "PKD2",
            "COL4A1",
            "COL4A3",
            "COL4A4",
            "COL4A5",
            "NPHS1",
            "NPHS2",
            "UMOD",
            "HNF1B",
            "ATP6V1B1",
        ]

        for gene in important_genes:
            if gene.lower() in original_text.lower():
                return True

        return False


class GeneNormalizationLogCRUD:
    """CRUD operations for gene normalization logs"""

    def create_log_entry(
        self,
        db: Session,
        original_text: str,
        source_name: str,
        success: bool,
        normalization_log: dict[str, Any],
        approved_symbol: str | None = None,
        hgnc_id: str | None = None,
        final_gene_id: int | None = None,
        staging_id: int | None = None,
        api_calls_made: int = 0,
        processing_time_ms: int | None = None,
    ) -> GeneNormalizationLog:
        """Create a comprehensive log entry for normalization attempt"""

        log_entry = GeneNormalizationLog(
            original_text=original_text,
            source_name=source_name,
            success=success,
            approved_symbol=approved_symbol,
            hgnc_id=hgnc_id,
            normalization_log=normalization_log,
            final_gene_id=final_gene_id,
            staging_id=staging_id,
            api_calls_made=api_calls_made,
            processing_time_ms=processing_time_ms,
        )

        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        return log_entry

    def get_normalization_stats(self, db: Session) -> dict[str, Any]:
        """Get normalization success statistics"""

        total_attempts = db.query(GeneNormalizationLog).count()
        successful_attempts = (
            db.query(GeneNormalizationLog).filter(GeneNormalizationLog.success).count()
        )

        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0

        # By source stats
        source_stats = {}
        sources = db.query(GeneNormalizationLog.source_name).distinct().all()
        for (source,) in sources:
            source_total = (
                db.query(GeneNormalizationLog)
                .filter(GeneNormalizationLog.source_name == source)
                .count()
            )
            source_success = (
                db.query(GeneNormalizationLog)
                .filter(
                    and_(GeneNormalizationLog.source_name == source, GeneNormalizationLog.success)
                )
                .count()
            )

            source_rate = (source_success / source_total * 100) if source_total > 0 else 0
            source_stats[source] = {
                "total": source_total,
                "successful": source_success,
                "success_rate": round(source_rate, 1),
            }

        return {
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "success_rate": round(success_rate, 1),
            "by_source": source_stats,
        }


# Create singleton instances
staging_crud = GeneNormalizationStagingCRUD()
log_crud = GeneNormalizationLogCRUD()
