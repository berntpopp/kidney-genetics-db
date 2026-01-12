"""
Log-based health monitoring and alerting.

Provides health checks based on log patterns, error rates, and performance metrics.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class LogHealthMonitor:
    """Monitors system health based on log patterns."""

    def __init__(
        self,
        error_rate_warning: float = 0.05,  # 5% error rate
        error_rate_critical: float = 0.10,  # 10% error rate
        response_time_warning_ms: float = 1000,
        response_time_critical_ms: float = 3000,
        min_logs_for_analysis: int = 100,
    ):
        """
        Initialize health monitor thresholds.

        Args:
            error_rate_warning: Warning threshold for error rate
            error_rate_critical: Critical threshold for error rate
            response_time_warning_ms: Warning threshold for response time
            response_time_critical_ms: Critical threshold for response time
            min_logs_for_analysis: Minimum logs needed for meaningful analysis
        """
        self.error_rate_warning = error_rate_warning
        self.error_rate_critical = error_rate_critical
        self.response_time_warning_ms = response_time_warning_ms
        self.response_time_critical_ms = response_time_critical_ms
        self.min_logs_for_analysis = min_logs_for_analysis

    async def check_health(self, window_minutes: int = 5) -> dict[str, Any]:
        """
        Perform comprehensive health check based on recent logs.

        Args:
            window_minutes: Time window to analyze (in minutes)

        Returns:
            Health check results with status and metrics
        """
        # Import here to avoid circular import
        from app.core.database import get_db

        db = next(get_db())
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

            # Get error rate
            error_stats = self._check_error_rate(db, cutoff_time)

            # Get performance metrics
            perf_stats = self._check_performance(db, cutoff_time)

            # Check for critical patterns
            critical_patterns = self._check_critical_patterns(db, cutoff_time)

            # Get recent issues
            recent_issues = self._get_recent_issues(db, cutoff_time)

            # Determine overall health status
            overall_status = self._determine_overall_status(
                error_stats, perf_stats, critical_patterns
            )

            result = {
                "status": overall_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "window_minutes": window_minutes,
                "metrics": {
                    "error_rate": error_stats,
                    "performance": perf_stats,
                    "critical_patterns": critical_patterns,
                    "recent_issues": recent_issues,
                },
                "thresholds": {
                    "error_rate_warning": self.error_rate_warning,
                    "error_rate_critical": self.error_rate_critical,
                    "response_time_warning_ms": self.response_time_warning_ms,
                    "response_time_critical_ms": self.response_time_critical_ms,
                },
            }

            # Log health check result if not healthy
            if overall_status != HealthStatus.HEALTHY:
                await logger.warning(
                    "System health degraded",
                    health_status=overall_status,
                    error_rate=error_stats.get("rate"),
                    avg_response_time=perf_stats.get("avg_response_time_ms"),
                )

            return result

        except Exception as e:
            await logger.error("Health check failed", error=e)
            return {
                "status": HealthStatus.CRITICAL,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            db.close()

    def _check_error_rate(self, db: Session, cutoff_time: datetime) -> dict:
        """Check error rate in the time window."""
        query = """
            SELECT
                COUNT(*) as total_logs,
                COUNT(*) FILTER (WHERE level = 'ERROR') as error_count,
                COUNT(*) FILTER (WHERE level = 'WARNING') as warning_count
            FROM system_logs
            WHERE timestamp >= :cutoff
        """

        result = db.execute(text(query), {"cutoff": cutoff_time}).first()

        if result.total_logs < self.min_logs_for_analysis:
            return {"total_logs": result.total_logs, "insufficient_data": True}

        error_rate = result.error_count / result.total_logs if result.total_logs > 0 else 0
        warning_rate = result.warning_count / result.total_logs if result.total_logs > 0 else 0

        return {
            "total_logs": result.total_logs,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "rate": round(error_rate, 4),
            "warning_rate": round(warning_rate, 4),
            "status": self._get_error_rate_status(error_rate),
        }

    def _check_performance(self, db: Session, cutoff_time: datetime) -> dict:
        """Check performance metrics from logs."""
        # Look for performance data in extra_data JSONB
        query = """
            SELECT
                AVG((extra_data->>'duration_ms')::float) as avg_duration,
                MAX((extra_data->>'duration_ms')::float) as max_duration,
                PERCENTILE_CONT(0.95) WITHIN GROUP (
                    ORDER BY (extra_data->>'duration_ms')::float
                ) as p95_duration
            FROM system_logs
            WHERE timestamp >= :cutoff
                AND extra_data->>'duration_ms' IS NOT NULL
        """

        result = db.execute(text(query), {"cutoff": cutoff_time}).first()

        if not result.avg_duration:
            return {"no_performance_data": True}

        return {
            "avg_response_time_ms": round(result.avg_duration, 2),
            "max_response_time_ms": round(result.max_duration, 2),
            "p95_response_time_ms": round(result.p95_duration, 2),
            "status": self._get_performance_status(result.avg_duration),
        }

    def _check_critical_patterns(self, db: Session, cutoff_time: datetime) -> dict:
        """Check for critical error patterns."""
        patterns = {
            "database_errors": "message ILIKE '%database%' AND level = 'ERROR'",
            "timeout_errors": "message ILIKE '%timeout%' AND level = 'ERROR'",
            "memory_errors": "message ILIKE '%memory%' AND level = 'ERROR'",
            "authentication_errors": "message ILIKE '%auth%' AND level = 'ERROR'",
        }

        results = {}
        for pattern_name, condition in patterns.items():
            query = f"""
                SELECT COUNT(*)
                FROM system_logs
                WHERE timestamp >= :cutoff AND {condition}
            """
            count = db.execute(text(query), {"cutoff": cutoff_time}).scalar()
            if count > 0:
                results[pattern_name] = count

        return results

    def _get_recent_issues(self, db: Session, cutoff_time: datetime, limit: int = 5) -> list:
        """Get recent error messages."""
        query = """
            SELECT DISTINCT ON (message)
                message,
                source,
                COUNT(*) as occurrence_count
            FROM system_logs
            WHERE timestamp >= :cutoff AND level = 'ERROR'
            GROUP BY message, source
            ORDER BY message, occurrence_count DESC
            LIMIT :limit
        """

        results = db.execute(text(query), {"cutoff": cutoff_time, "limit": limit}).fetchall()

        return [
            {"message": row.message, "source": row.source, "occurrences": row.occurrence_count}
            for row in results
        ]

    def _get_error_rate_status(self, error_rate: float) -> HealthStatus:
        """Determine health status based on error rate."""
        if error_rate >= self.error_rate_critical:
            return HealthStatus.CRITICAL
        elif error_rate >= self.error_rate_warning:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _get_performance_status(self, avg_response_time: float) -> HealthStatus:
        """Determine health status based on performance."""
        if avg_response_time >= self.response_time_critical_ms:
            return HealthStatus.CRITICAL
        elif avg_response_time >= self.response_time_warning_ms:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _determine_overall_status(
        self, error_stats: dict, perf_stats: dict, critical_patterns: dict
    ) -> HealthStatus:
        """Determine overall system health status."""
        # If we have critical patterns, system is critical
        if critical_patterns:
            return HealthStatus.CRITICAL

        # Check individual component statuses
        statuses = []

        if "status" in error_stats:
            statuses.append(error_stats["status"])

        if "status" in perf_stats:
            statuses.append(perf_stats["status"])

        # Return worst status
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY


# Global instance
health_monitor = LogHealthMonitor()


async def get_system_health(window_minutes: int = 5) -> dict[str, Any]:
    """
    Get current system health based on logs.

    Args:
        window_minutes: Time window to analyze

    Returns:
        Health check results
    """
    return await health_monitor.check_health(window_minutes)
