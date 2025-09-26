"""
Unified filtering utilities for all data sources.
Provides consistent filtering logic and statistics tracking.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Integer, cast, delete, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import Gene, GeneEvidence

logger = get_logger(__name__)


class FilteringStats:
    """Track filtering statistics consistently across all sources."""

    def __init__(self, source_name: str, entity_name: str, threshold: int):
        self.source_name = source_name
        self.entity_name = entity_name
        self.threshold = threshold
        self.total_before = 0
        self.total_after = 0
        self.filtered_count = 0
        self.filtered_genes = []
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None

    @property
    def filter_rate(self) -> float:
        if self.total_before == 0:
            return 0.0
        return (self.filtered_count / self.total_before) * 100

    @property
    def duration_seconds(self) -> float:
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def complete(self):
        """Mark filtering as complete."""
        self.end_time = datetime.now(timezone.utc)

    def log_summary(self):
        """Log standardized summary across all sources."""
        logger.sync_info(
            f"{self.source_name} filtering complete",
            total_before=self.total_before,
            total_after=self.total_after,
            filtered_count=self.filtered_count,
            filter_rate=f"{self.filter_rate:.1f}%",
            threshold=f"min_{self.entity_name}={self.threshold}",
            duration_seconds=f"{self.duration_seconds:.2f}",
            sample_filtered=self.filtered_genes[:5] if self.filtered_genes else [],
        )

        # Warn if aggressive
        if self.filter_rate > 50:
            logger.sync_warning(
                f"{self.source_name} filtered >50% of genes - review threshold",
                filter_rate=f"{self.filter_rate:.1f}%",
                threshold=self.threshold,
                entity=self.entity_name,
            )

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "source_name": self.source_name,
            "entity_name": self.entity_name,
            "threshold": self.threshold,
            "total_before": self.total_before,
            "total_after": self.total_after,
            "filtered_count": self.filtered_count,
            "filter_rate": f"{self.filter_rate:.1f}%",
            "duration_seconds": self.duration_seconds,
            "timestamp": self.end_time.isoformat() if self.end_time else None,
            "filtered_sample": self.filtered_genes[:10],
        }


def apply_database_filter(
    db: Session,
    source_name: str,
    count_field: str,
    min_threshold: int,
    entity_name: str,
    enabled: bool = True,
) -> FilteringStats:
    """
    Apply filtering directly in database for complete datasets.
    Used by PubTator after all chunks processed.

    IMPORTANT: Caller must handle transaction commit/rollback.
    """
    stats = FilteringStats(source_name, entity_name, min_threshold)

    if not enabled or min_threshold <= 1:
        logger.sync_info(
            f"{source_name} filtering disabled", min_threshold=min_threshold, enabled=enabled
        )
        return stats

    try:
        # Count before filtering
        count_stmt = (
            select(func.count())
            .select_from(GeneEvidence)
            .where(GeneEvidence.source_name == source_name)
        )
        stats.total_before = db.execute(count_stmt).scalar() or 0

        if stats.total_before == 0:
            stats.complete()
            return stats

        # Get sample of records to be deleted for logging (before deletion)
        sample_stmt = (
            select(Gene.approved_symbol, GeneEvidence.evidence_data[count_field])
            .select_from(GeneEvidence)
            .join(Gene, GeneEvidence.gene_id == Gene.id)
            .where(
                GeneEvidence.source_name == source_name,
                cast(GeneEvidence.evidence_data[count_field], Integer) < min_threshold,
            )
            .limit(10)
        )
        samples = db.execute(sample_stmt).all()

        for symbol, count in samples:
            stats.filtered_genes.append(
                {"symbol": symbol, count_field: count, "threshold": min_threshold}
            )

        # More efficient: Delete directly with returning clause
        delete_stmt = (
            delete(GeneEvidence)
            .where(
                GeneEvidence.source_name == source_name,
                cast(GeneEvidence.evidence_data[count_field], Integer) < min_threshold,
            )
            .returning(GeneEvidence.id)
        )

        # Execute and get deleted count
        result = db.execute(delete_stmt)
        deleted_ids = result.fetchall()
        stats.filtered_count = len(deleted_ids)

        if stats.filtered_count > 0:
            logger.sync_info(
                f"Deleted {stats.filtered_count} genes below threshold",
                source_name=source_name,
                threshold=min_threshold,
                sample=stats.filtered_genes[:3],
            )

        # Count after filtering
        stats.total_after = db.execute(count_stmt).scalar() or 0

    except Exception as e:
        logger.sync_error(
            f"Database filtering failed for {source_name}", error=str(e), threshold=min_threshold
        )
        raise

    stats.complete()
    stats.log_summary()

    return stats


def apply_memory_filter(
    data_dict: dict[str, Any],
    count_field: str,
    min_threshold: int,
    entity_name: str,
    source_name: str,
    enabled: bool = True,
) -> tuple[dict[str, Any], FilteringStats]:
    """
    Apply filtering in memory for merged data.
    Used by DiagnosticPanels and Literature.
    """
    stats = FilteringStats(source_name, entity_name, min_threshold)
    stats.total_before = len(data_dict)

    if not enabled or min_threshold <= 1:
        logger.sync_info(
            f"{source_name} filtering disabled",
            gene_count=len(data_dict),
            min_threshold=min_threshold,
            enabled=enabled,
        )
        stats.total_after = stats.total_before
        stats.complete()
        return data_dict, stats

    filtered_data = {}

    for gene_symbol, gene_data in data_dict.items():
        count = gene_data.get(count_field, 0)

        if count < min_threshold:
            stats.filtered_count += 1
            stats.filtered_genes.append(
                {"symbol": gene_symbol, count_field: count, "threshold": min_threshold}
            )
            continue

        filtered_data[gene_symbol] = gene_data

    stats.total_after = len(filtered_data)
    stats.complete()
    stats.log_summary()

    return filtered_data, stats


def validate_threshold_config(threshold: Any, entity_name: str, source_name: str) -> int:
    """
    Validate threshold configuration with consistent error handling.
    """
    try:
        value = int(threshold)
        if value < 1:
            logger.sync_warning(
                f"Invalid threshold for {source_name}, using minimum",
                configured=value,
                entity=entity_name,
                using=1,
            )
            return 1
        return value
    except (TypeError, ValueError):
        logger.sync_error(
            f"Invalid threshold type for {source_name}, disabling filter",
            configured=threshold,
            entity=entity_name,
            using=1,
        )
        return 1
