"""
Materialized view management with safe concurrent refresh.
Implements advisory locks to prevent concurrent refresh conflicts.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.core.view_monitoring import track_materialized_view_refresh

logger = get_logger(__name__)


class RefreshStrategy(Enum):
    """Refresh strategy for materialized views."""

    STANDARD = "STANDARD"  # Blocks queries during refresh
    CONCURRENT = "CONCURRENT"  # Allows queries during refresh


@dataclass
class MaterializedViewConfig:
    """Configuration for a materialized view."""

    name: str
    definition: str
    indexes: list[str]
    dependencies: set[str]
    refresh_strategy: RefreshStrategy = RefreshStrategy.CONCURRENT
    refresh_interval_hours: int = 24
    last_refresh: datetime | None = None


class MaterializedViewManager:
    """
    Manages materialized views with safe concurrent refresh.

    Uses PostgreSQL advisory locks to prevent concurrent refresh attempts
    that could cause deadlocks or errors.
    """

    # Materialized view definitions
    MATERIALIZED_VIEWS: dict[str, MaterializedViewConfig] = {
        "source_overlap_statistics": MaterializedViewConfig(
            name="source_overlap_statistics",
            definition="""
            SELECT
                s1.source_name AS source1,
                s2.source_name AS source2,
                COUNT(DISTINCT CASE
                    WHEN s1.gene_id = s2.gene_id
                    THEN s1.gene_id
                END)::integer AS overlap_count,
                COUNT(DISTINCT s1.gene_id)::integer AS source1_total,
                COUNT(DISTINCT s2.gene_id)::integer AS source2_total,
                ROUND(
                    COUNT(DISTINCT CASE
                        WHEN s1.gene_id = s2.gene_id
                        THEN s1.gene_id
                    END)::numeric /
                    NULLIF(COUNT(DISTINCT s1.gene_id), 0) * 100,
                    2
                )::float8 AS overlap_percentage
            FROM gene_evidence s1
            CROSS JOIN gene_evidence s2
            WHERE s1.source_name < s2.source_name  -- Avoid duplicates
            GROUP BY s1.source_name, s2.source_name
            """,
            indexes=[
                "CREATE INDEX idx_source_overlap_sources ON source_overlap_statistics(source1, source2)",
            ],
            dependencies=set(),
            refresh_strategy=RefreshStrategy.CONCURRENT,
            refresh_interval_hours=24,
        ),
        "gene_distribution_analysis": MaterializedViewConfig(
            name="gene_distribution_analysis",
            definition="""
            WITH score_bins AS (
                SELECT
                    CASE
                        WHEN percentage_score < 10 THEN '0-10%'
                        WHEN percentage_score < 20 THEN '10-20%'
                        WHEN percentage_score < 30 THEN '20-30%'
                        WHEN percentage_score < 40 THEN '30-40%'
                        WHEN percentage_score < 50 THEN '40-50%'
                        WHEN percentage_score < 60 THEN '50-60%'
                        WHEN percentage_score < 70 THEN '60-70%'
                        WHEN percentage_score < 80 THEN '70-80%'
                        WHEN percentage_score < 90 THEN '80-90%'
                        ELSE '90-100%'
                    END AS score_bin,
                    classification,
                    COUNT(*)::integer AS gene_count
                FROM gene_scores
                GROUP BY score_bin, classification
            ),
            source_distribution AS (
                SELECT
                    source_count,
                    classification,
                    COUNT(*)::integer AS gene_count
                FROM gene_scores
                GROUP BY source_count, classification
            )
            SELECT
                'score_distribution'::text AS analysis_type,
                score_bin AS category,
                classification,
                gene_count
            FROM score_bins
            UNION ALL
            SELECT
                'source_distribution'::text AS analysis_type,
                source_count::text AS category,
                classification,
                gene_count
            FROM source_distribution
            """,
            indexes=[
                "CREATE INDEX idx_gene_dist_type ON gene_distribution_analysis(analysis_type)",
                "CREATE INDEX idx_gene_dist_category ON gene_distribution_analysis(category)",
            ],
            dependencies={"gene_scores"},
            refresh_strategy=RefreshStrategy.CONCURRENT,
            refresh_interval_hours=12,
        ),
        "upset_plot_data": MaterializedViewConfig(
            name="upset_plot_data",
            definition="""
            WITH gene_sources AS (
                SELECT
                    gene_id,
                    array_agg(DISTINCT source_name ORDER BY source_name) AS source_combination
                FROM gene_evidence
                GROUP BY gene_id
            ),
            combinations AS (
                SELECT
                    source_combination,
                    COUNT(*)::integer AS gene_count,
                    array_length(source_combination, 1)::integer AS source_count
                FROM gene_sources
                GROUP BY source_combination
                HAVING COUNT(*) > 1  -- Filter out singleton combinations
            )
            SELECT
                source_combination::text[] AS sources,
                gene_count,
                source_count,
                ROUND(
                    gene_count::numeric /
                    (SELECT COUNT(DISTINCT gene_id) FROM gene_evidence) * 100,
                    2
                )::float8 AS percentage
            FROM combinations
            ORDER BY gene_count DESC
            LIMIT 100  -- Top 100 combinations for visualization
            """,
            indexes=[
                "CREATE INDEX idx_upset_sources ON upset_plot_data USING GIN(sources)",
                "CREATE INDEX idx_upset_count ON upset_plot_data(gene_count DESC)",
            ],
            dependencies=set(),
            refresh_strategy=RefreshStrategy.CONCURRENT,
            refresh_interval_hours=24,
        ),
    }

    def __init__(self, db: Session):
        """
        Initialize the materialized view manager.

        Args:
            db: Database session
        """
        self.db = db
        self._executor = get_thread_pool_executor()

    def _get_lock_id(self, view_name: str) -> int:
        """
        Generate a unique lock ID for a view name.

        Uses MD5 hash to create a consistent integer ID for advisory locks.

        Args:
            view_name: Name of the materialized view

        Returns:
            Integer lock ID
        """
        # Create hash and take first 8 bytes as signed int
        # MD5 used for consistent lock ID generation, not security
        hash_bytes = hashlib.md5(
            f"matview_{view_name}".encode(), usedforsecurity=False
        ).digest()[:8]
        return int.from_bytes(hash_bytes, byteorder="big", signed=True) % (2**31)

    def _acquire_advisory_lock(self, lock_id: int, timeout_seconds: int = 5) -> bool:
        """
        Acquire an advisory lock with timeout.

        Args:
            lock_id: Lock ID to acquire
            timeout_seconds: Maximum wait time

        Returns:
            True if lock acquired, False if timeout
        """
        try:
            # Try to acquire lock with timeout
            result = self.db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
            ).scalar()

            if result:
                logger.sync_info(f"Acquired advisory lock {lock_id}")
                return True

            # Wait and retry with exponential backoff
            wait_time: float = 0.1
            total_wait: float = 0.0

            while total_wait < timeout_seconds:
                time.sleep(wait_time)
                result = self.db.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
                ).scalar()

                if result:
                    logger.sync_info(f"Acquired advisory lock {lock_id} after {total_wait:.1f}s")
                    return True

                total_wait += wait_time
                wait_time = min(wait_time * 2.0, 1.0)  # Cap at 1 second

            logger.sync_warning(f"Failed to acquire lock {lock_id} after {timeout_seconds}s")
            return False

        except Exception as e:
            logger.sync_error(f"Error acquiring advisory lock: {e}")
            return False

    def _release_advisory_lock(self, lock_id: int) -> None:
        """
        Release an advisory lock.

        Args:
            lock_id: Lock ID to release
        """
        try:
            self.db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
            logger.sync_info(f"Released advisory lock {lock_id}")
        except Exception as e:
            logger.sync_error(f"Error releasing advisory lock: {e}")

    def create_materialized_view(self, config: MaterializedViewConfig) -> None:
        """
        Create a materialized view if it doesn't exist.

        Args:
            config: Materialized view configuration
        """
        lock_id = self._get_lock_id(config.name)

        if not self._acquire_advisory_lock(lock_id):
            raise RuntimeError(f"Could not acquire lock for creating {config.name}")

        try:
            # Check if view exists
            exists = self.db.execute(
                text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_matviews
                    WHERE matviewname = :name
                )
                """),
                {"name": config.name},
            ).scalar()

            if not exists:
                logger.sync_info(f"Creating materialized view: {config.name}")

                # Create the materialized view
                self.db.execute(
                    text(f"""
                    CREATE MATERIALIZED VIEW {config.name} AS
                    {config.definition}
                    WITH DATA
                """)
                )

                # Create indexes
                for index_sql in config.indexes:
                    self.db.execute(text(index_sql))

                self.db.commit()
                logger.sync_info(f"Created materialized view: {config.name}")
            else:
                logger.sync_info(f"Materialized view already exists: {config.name}")

        finally:
            self._release_advisory_lock(lock_id)

    @track_materialized_view_refresh("dynamic")
    def refresh_materialized_view(self, view_name: str, concurrent: bool | None = None) -> bool:
        """
        Refresh a materialized view with advisory locking.

        Args:
            view_name: Name of the view to refresh
            concurrent: Override refresh strategy (None uses config default)

        Returns:
            True if refresh successful, False otherwise
        """
        config = self.MATERIALIZED_VIEWS.get(view_name)
        if not config:
            logger.sync_error(f"Unknown materialized view: {view_name}")
            return False

        lock_id = self._get_lock_id(view_name)

        if not self._acquire_advisory_lock(lock_id, timeout_seconds=10):
            logger.sync_warning(f"Skipping refresh for {view_name} - could not acquire lock")
            return False

        try:
            # Determine refresh strategy
            use_concurrent = concurrent
            if use_concurrent is None:
                use_concurrent = config.refresh_strategy == RefreshStrategy.CONCURRENT

            refresh_clause = "CONCURRENTLY" if use_concurrent else ""

            logger.sync_info(f"Refreshing materialized view: {view_name} ({refresh_clause})")

            start_time = datetime.now()
            self.db.execute(text(f"REFRESH MATERIALIZED VIEW {refresh_clause} {view_name}"))
            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()

            logger.sync_info(
                f"Refreshed materialized view: {view_name}",
                duration_seconds=duration,
                strategy=refresh_clause or "STANDARD",
            )

            # Update last refresh time
            config.last_refresh = datetime.now()

            return True

        except Exception as e:
            logger.sync_error(f"Error refreshing materialized view {view_name}: {e}")
            self.db.rollback()
            return False

        finally:
            self._release_advisory_lock(lock_id)

    async def refresh_all_views(self, force: bool = False) -> dict[str, bool]:
        """
        Refresh all materialized views that need updating.

        Args:
            force: Force refresh regardless of interval

        Returns:
            Dictionary of view names to refresh success status
        """
        results = {}
        loop = asyncio.get_event_loop()

        for view_name, config in self.MATERIALIZED_VIEWS.items():
            should_refresh = force

            if not force and config.last_refresh:
                # Check if refresh interval has passed
                time_since_refresh = datetime.now() - config.last_refresh
                should_refresh = time_since_refresh > timedelta(hours=config.refresh_interval_hours)
            elif not force and not config.last_refresh:
                # Never refreshed, should refresh
                should_refresh = True

            if should_refresh:
                # Run refresh in thread pool to avoid blocking
                result = await loop.run_in_executor(
                    self._executor,
                    self.refresh_materialized_view,
                    view_name,
                    None,  # Use default strategy
                )
                results[view_name] = result
            else:
                logger.sync_info(
                    f"Skipping refresh for {view_name} - within interval",
                    last_refresh=config.last_refresh.isoformat() if config.last_refresh else None,
                )
                results[view_name] = True  # Consider as success

        return results

    def drop_materialized_view(self, view_name: str) -> None:
        """
        Drop a materialized view.

        Args:
            view_name: Name of the view to drop
        """
        lock_id = self._get_lock_id(view_name)

        if not self._acquire_advisory_lock(lock_id):
            raise RuntimeError(f"Could not acquire lock for dropping {view_name}")

        try:
            logger.sync_info(f"Dropping materialized view: {view_name}")
            self.db.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE"))
            self.db.commit()
            logger.sync_info(f"Dropped materialized view: {view_name}")

        finally:
            self._release_advisory_lock(lock_id)

    def get_view_stats(self) -> list[dict[str, Any]]:
        """
        Get statistics for all materialized views.

        Returns:
            List of view statistics
        """
        stats = []

        for view_name, config in self.MATERIALIZED_VIEWS.items():
            # Get view size and row count
            size_result = self.db.execute(
                text("""
                SELECT
                    pg_size_pretty(pg_total_relation_size(:view_name)) AS size,
                    (SELECT COUNT(*) FROM information_schema.tables
                     WHERE table_name = :view_name) AS exists
                """),
                {"view_name": view_name},
            ).first()

            if size_result and size_result.exists:
                row_count = self.db.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()

                stats.append(
                    {
                        "name": view_name,
                        "size": size_result.size,
                        "row_count": row_count,
                        "refresh_strategy": config.refresh_strategy.value,
                        "refresh_interval_hours": config.refresh_interval_hours,
                        "last_refresh": config.last_refresh.isoformat()
                        if config.last_refresh
                        else None,
                        "dependencies": list(config.dependencies),
                    }
                )

        return stats

    def initialize_all_views(self) -> None:
        """Create all materialized views if they don't exist."""
        logger.sync_info("Initializing all materialized views")

        # Sort by dependencies (views with no dependencies first)
        sorted_views = sorted(self.MATERIALIZED_VIEWS.items(), key=lambda x: len(x[1].dependencies))

        for view_name, config in sorted_views:
            try:
                self.create_materialized_view(config)
            except Exception as e:
                logger.sync_error(f"Failed to create materialized view {view_name}: {e}")

        logger.sync_info("Materialized view initialization complete")


# Convenience functions for dependency injection
_manager_instance: MaterializedViewManager | None = None


def get_materialized_view_manager(db: Session) -> MaterializedViewManager:
    """
    Get or create a materialized view manager instance.

    Args:
        db: Database session

    Returns:
        MaterializedViewManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MaterializedViewManager(db)
    return _manager_instance
