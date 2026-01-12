"""
Global percentile calculation service for annotation scores.

This service provides non-blocking, cached percentile calculations
for annotation sources like STRING PPI. Designed with safety features
to prevent regressions and ensure graceful degradation.
"""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger


class PercentileService:
    """
    Service for calculating and managing global percentiles.

    Features:
    - Non-blocking calculation via ThreadPoolExecutor
    - Multi-level caching for performance
    - Graceful degradation on failures
    - Frequency limiting to prevent storms
    - Comprehensive error handling
    """

    def __init__(self, session: Session):
        """Initialize the percentile service."""
        self.session = session
        self.logger = get_logger(__name__)

        # Use separate thread pool to avoid blocking main executor
        self._percentile_executor = ThreadPoolExecutor(
            max_workers=1,  # Only 1 to prevent resource exhaustion
            thread_name_prefix="percentile",
        )

        self.cache_service = get_cache_service(session)

        # Frequency limiting
        self._last_calculation: dict[str, float] = {}
        self._min_interval = 300  # 5 minutes between calculations

        # Check if disabled via environment
        self.disabled = os.getenv("DISABLE_PERCENTILE_CALCULATION", "false").lower() == "true"
        if self.disabled:
            self.logger.sync_warning("Percentile calculation is DISABLED via environment variable")

    async def calculate_global_percentiles(
        self, source: str, score_field: str, force: bool = False
    ) -> dict[int, float]:
        """
        Calculate global percentiles for a source using PostgreSQL.

        Args:
            source: Source name (e.g., 'string_ppi')
            score_field: Field containing the score (for logging)
            force: Force recalculation even if recently calculated

        Returns:
            Dictionary mapping gene_id to percentile (0.0-1.0)
            Empty dict if calculation fails or is disabled
        """
        if self.disabled:
            self.logger.sync_debug("Percentile calculation disabled")
            return {}

        # Check frequency limit
        if not force:
            last_calc = self._last_calculation.get(source, 0)
            if time.time() - last_calc < self._min_interval:
                await self.logger.info(
                    f"Skipping percentile calculation for {source} - too frequent",
                    time_since_last=time.time() - last_calc,
                )
                return await self.get_cached_percentiles_only(source) or {}

        # Try with timeout (5 second max)
        try:
            return await asyncio.wait_for(
                self._calculate_with_fallback(source, score_field), timeout=5.0
            )
        except asyncio.TimeoutError:
            await self.logger.error(f"Percentile calculation timed out for {source}")
            return await self.get_cached_percentiles_only(source) or {}

    async def _calculate_with_fallback(self, source: str, score_field: str) -> dict[int, float]:
        """Calculate with multiple fallback levels."""
        start_time = time.time()

        # Check cache first
        cache_key = f"percentiles:{source}:global"
        cached = await self.cache_service.get(key=cache_key, namespace="statistics", default=None)

        if cached and isinstance(cached, dict):
            await self.logger.info(f"Using cached percentiles for {source}", gene_count=len(cached))
            return cast(dict[int, float], cached)

        # Calculate from database view
        try:
            loop = asyncio.get_event_loop()
            percentiles = await loop.run_in_executor(
                self._percentile_executor, self._calculate_sync, source, score_field
            )

            if percentiles:
                # Cache for 1 hour
                await self.cache_service.set(
                    key=cache_key, value=percentiles, namespace="statistics", ttl=3600
                )

                # Update last calculation time
                self._last_calculation[source] = time.time()

                # Log metrics
                await self.logger.info(
                    "Percentile calculation completed",
                    source=source,
                    duration_ms=(time.time() - start_time) * 1000,
                    gene_count=len(percentiles),
                )

                # Alert if suspicious
                if percentiles and len(set(percentiles.values())) == 1:
                    await self.logger.error(
                        f"ALERT: All percentiles identical for {source} - calculation may be broken"
                    )

                return percentiles

        except Exception as e:
            await self.logger.error(
                f"Failed to calculate percentiles for {source}",
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

        return {}

    def _calculate_sync(self, source: str, score_field: str) -> dict[int, float]:
        """
        Synchronous percentile calculation for thread pool execution.

        Args:
            source: Source name
            score_field: Field name (for logging)

        Returns:
            Dictionary mapping gene_id to percentile
        """
        try:
            # Use the view to get percentiles
            result = self.session.execute(
                text(f"""
                    SELECT gene_id, percentile_rank
                    FROM {source}_percentiles
                    WHERE ppi_score IS NOT NULL
                    AND ppi_score > 0
                """)
            )

            rows = result.fetchall()

            if not rows:
                self.logger.sync_warning(
                    f"No data in {source}_percentiles view. "
                    "Percentiles will be None until calculated."
                )
                return {}

            # Handle single gene case
            if len(rows) == 1:
                # Single value gets 0.5 (median) by convention
                row = rows[0]
                return {row[0]: 0.5}

            # Build percentile map
            percentiles = {}
            for row in rows:
                gene_id = row[0]
                percentile = row[1]
                percentiles[gene_id] = round(percentile, 3)

            self.logger.sync_info(
                f"Calculated {len(percentiles)} percentiles from view", source=source
            )

            return percentiles

        except Exception as e:
            # View doesn't exist or query failed
            self.logger.sync_debug(
                "Could not calculate percentiles from view", source=source, error=str(e)
            )
            return {}

    async def get_cached_percentiles_only(self, source: str) -> dict[int, float] | None:
        """
        Get percentiles from cache only, no calculation.

        Args:
            source: Source name

        Returns:
            Cached percentiles or None
        """
        try:
            cache_key = f"percentiles:{source}:global"
            cached = await self.cache_service.get(
                key=cache_key, namespace="statistics", default=None
            )

            # Validate structure
            if cached and isinstance(cached, dict):
                return cast(dict[int, float], cached)

        except Exception as e:
            self.logger.sync_debug(f"Cache error getting percentiles: {e}")

        return None

    async def get_percentile_for_gene(
        self, source: str, gene_id: int, raw_score: float | None = None
    ) -> float | None:
        """
        Get percentile for a specific gene.

        Args:
            source: Source name
            gene_id: Gene ID
            raw_score: Optional raw score (for logging)

        Returns:
            Percentile (0.0-1.0) or None if not available
        """
        # Try cache-only first for speed
        percentiles = await self.get_cached_percentiles_only(source)

        if percentiles and gene_id in percentiles:
            return percentiles[gene_id]

        # Don't trigger full calculation for single gene
        await self.logger.debug(
            f"Gene {gene_id} not in cached percentiles for {source}", raw_score=raw_score
        )

        return None

    async def validate_percentiles(self, source: str) -> dict[str, Any]:
        """
        Validate that percentile distribution is reasonable.

        Args:
            source: Source name

        Returns:
            Validation results with status and checks
        """
        percentiles = await self.get_cached_percentiles_only(source)

        if not percentiles:
            return {"status": "error", "message": "No percentiles found"}

        values = list(percentiles.values())

        if not values:
            return {"status": "error", "message": "Empty percentiles"}

        # Basic sanity checks
        sorted_values = sorted(values)
        median_idx = len(sorted_values) // 2

        checks = {
            "has_data": len(values) > 0,
            "has_variance": len(set(values)) > 1,  # Not all same
            "median_reasonable": 0.4 < sorted_values[median_idx] < 0.6,
            "min_near_zero": min(values) < 0.1,
            "max_near_one": max(values) > 0.9,
            "no_all_ones": not all(v == 1.0 for v in values),
            "no_all_zeros": not all(v == 0.0 for v in values),
        }

        all_passed = all(checks.values())

        if not all_passed:
            await self.logger.error(
                f"Percentile validation failed for {source}",
                checks=checks,
                sample_values=sorted_values[:5] + sorted_values[-5:],
            )

        return {
            "status": "ok" if all_passed else "warning",
            "checks": checks,
            "stats": {
                "count": len(values),
                "unique": len(set(values)),
                "min": min(values),
                "max": max(values),
                "median": sorted_values[median_idx],
            },
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._percentile_executor.shutdown(wait=False)
