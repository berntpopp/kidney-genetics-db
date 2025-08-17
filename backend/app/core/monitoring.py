"""
Comprehensive monitoring and statistics service for the cache system.

Provides detailed metrics, performance tracking, and health monitoring
across all cache components and data sources.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.cached_http_client import get_cached_http_client
from app.core.hgnc_client import get_hgnc_client_cached
from app.pipeline.sources.gencc_unified import get_gencc_client

logger = logging.getLogger(__name__)


class CacheMonitoringService:
    """
    Comprehensive cache monitoring service providing detailed metrics
    and performance tracking across all cache components.
    """

    def __init__(self, db_session: Session | AsyncSession | None = None):
        """Initialize the monitoring service."""
        self.cache_service = get_cache_service(db_session)
        self.http_client = get_cached_http_client()
        self.db_session = db_session

        # Data source clients for individual monitoring
        self.data_source_clients = {}
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize cached clients for monitoring."""
        try:
            self.data_source_clients = {
                'hgnc': get_hgnc_client_cached(db_session=self.db_session),
                'gencc': get_gencc_client(db_session=self.db_session),
                # Note: Other data sources (PubTator, PanelApp, HPO) use unified cache through namespace
                # Cache stats for these are retrieved via namespace in get_comprehensive_stats
            }
        except Exception as e:
            logger.error(f"Error initializing data source clients: {e}")
            self.data_source_clients = {}

    async def get_comprehensive_stats(self) -> dict[str, Any]:
        """
        Get comprehensive statistics across all cache components.

        Returns:
            Dictionary with detailed cache statistics
        """
        stats = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall": {},
            "namespaces": {},
            "data_sources": {},
            "database": {},
            "http_cache": {},
            "performance": {},
            "health": {},
        }

        try:
            # Overall cache statistics
            overall_stats = await self.cache_service.get_stats()
            stats["overall"] = overall_stats

            # Namespace-specific statistics
            namespaces = ["hgnc", "pubtator", "gencc", "panelapp", "hpo", "http", "files"]
            for namespace in namespaces:
                try:
                    ns_stats = await self.cache_service.get_stats(namespace)
                    if ns_stats.get("db_entries", 0) > 0 or ns_stats.get("memory_entries", 0) > 0:
                        stats["namespaces"][namespace] = ns_stats
                except Exception as e:
                    logger.warning(f"Error getting stats for namespace {namespace}: {e}")

            # Data source-specific statistics
            for source_name, client in self.data_source_clients.items():
                try:
                    if hasattr(client, 'get_cache_stats'):
                        source_stats = await client.get_cache_stats()
                        stats["data_sources"][source_name] = source_stats
                except Exception as e:
                    logger.warning(f"Error getting stats for data source {source_name}: {e}")

            # HTTP cache statistics
            try:
                http_stats = await self.http_client.get_cache_stats()
                stats["http_cache"] = http_stats
            except Exception as e:
                logger.warning(f"Error getting HTTP cache stats: {e}")

            # Database statistics
            try:
                db_stats = await self._get_database_stats()
                stats["database"] = db_stats
            except Exception as e:
                logger.warning(f"Error getting database stats: {e}")

            # Performance metrics
            try:
                perf_stats = await self._get_performance_stats()
                stats["performance"] = perf_stats
            except Exception as e:
                logger.warning(f"Error getting performance stats: {e}")

            # Health checks
            try:
                health_stats = await self._get_health_stats()
                stats["health"] = health_stats
            except Exception as e:
                logger.warning(f"Error getting health stats: {e}")

        except Exception as e:
            logger.error(f"Error getting comprehensive stats: {e}")
            stats["error"] = str(e)

        return stats

    async def _get_database_stats(self) -> dict[str, Any]:
        """Get database-specific cache statistics."""
        if not self.db_session:
            return {"error": "No database session available"}

        try:
            # Get cache table statistics
            queries = {
                "total_entries": "SELECT COUNT(*) FROM cache_entries",
                "total_size_mb": "SELECT ROUND(SUM(data_size)::numeric / 1024 / 1024, 2) FROM cache_entries WHERE data_size IS NOT NULL",
                "expired_entries": f"SELECT COUNT(*) FROM cache_entries WHERE expires_at < '{datetime.now(timezone.utc).isoformat()}'",
                "entries_last_24h": f"SELECT COUNT(*) FROM cache_entries WHERE created_at > '{(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}'",
                "most_accessed": "SELECT cache_key, namespace, access_count FROM cache_entries ORDER BY access_count DESC LIMIT 10",
                "largest_entries": "SELECT cache_key, namespace, data_size FROM cache_entries WHERE data_size IS NOT NULL ORDER BY data_size DESC LIMIT 10",
            }

            results = {}

            if isinstance(self.db_session, AsyncSession):
                # Async session
                for name, query in queries.items():
                    try:
                        if name in ["most_accessed", "largest_entries"]:
                            result = await self.db_session.execute(text(query))
                            results[name] = [dict(row._mapping) for row in result.fetchall()]
                        else:
                            result = await self.db_session.execute(text(query))
                            value = result.scalar()
                            results[name] = value if value is not None else 0
                    except Exception as e:
                        logger.warning(f"Error executing query {name}: {e}")
                        results[name] = None
            else:
                # Sync session
                for name, query in queries.items():
                    try:
                        if name in ["most_accessed", "largest_entries"]:
                            result = self.db_session.execute(text(query))
                            results[name] = [dict(row._mapping) for row in result.fetchall()]
                        else:
                            result = self.db_session.execute(text(query))
                            value = result.scalar()
                            results[name] = value if value is not None else 0
                    except Exception as e:
                        logger.warning(f"Error executing query {name}: {e}")
                        results[name] = None

            return results

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    async def _get_performance_stats(self) -> dict[str, Any]:
        """Get performance-related statistics."""
        try:
            overall_stats = await self.cache_service.get_stats()

            # Calculate derived performance metrics
            total_requests = overall_stats.get("hits", 0) + overall_stats.get("misses", 0)
            hit_rate = overall_stats.get("hit_rate", 0.0)

            # Performance indicators
            performance = {
                "total_requests": total_requests,
                "hit_rate_percentage": round(hit_rate * 100, 2),
                "cache_efficiency": self._calculate_cache_efficiency(hit_rate),
                "memory_utilization": await self._calculate_memory_utilization(),
                "response_time_estimate": self._estimate_response_time_improvement(hit_rate),
            }

            # Add namespace-specific performance
            namespace_performance = {}
            namespaces = ["hgnc", "pubtator", "gencc", "panelapp", "hpo"]

            for namespace in namespaces:
                try:
                    ns_stats = await self.cache_service.get_stats(namespace)
                    ns_total = ns_stats.get("hits", 0) + ns_stats.get("misses", 0)
                    ns_hit_rate = ns_stats.get("hit_rate", 0.0)

                    if ns_total > 0:
                        namespace_performance[namespace] = {
                            "requests": ns_total,
                            "hit_rate": round(ns_hit_rate * 100, 2),
                            "efficiency": self._calculate_cache_efficiency(ns_hit_rate),
                        }
                except Exception as e:
                    logger.warning(f"Error getting performance stats for {namespace}: {e}")

            performance["namespaces"] = namespace_performance

            return performance

        except Exception as e:
            logger.error(f"Error calculating performance stats: {e}")
            return {"error": str(e)}

    async def _get_health_stats(self) -> dict[str, Any]:
        """Get health status of all cache components."""
        health = {
            "overall_status": "healthy",
            "components": {},
            "issues": [],
            "recommendations": [],
        }

        try:
            # Check cache service health
            try:
                cache_stats = await self.cache_service.get_stats()
                hit_rate = cache_stats.get("hit_rate", 0.0)

                cache_health = {
                    "status": "healthy",
                    "hit_rate": hit_rate,
                    "issues": []
                }

                if hit_rate < 0.3:
                    cache_health["status"] = "warning"
                    cache_health["issues"].append("Low hit rate (< 30%)")
                    health["issues"].append("Overall cache hit rate is below optimal threshold")
                    health["recommendations"].append("Consider cache warming or reviewing cache TTL settings")

                health["components"]["cache_service"] = cache_health

            except Exception as e:
                health["components"]["cache_service"] = {
                    "status": "error",
                    "error": str(e)
                }
                health["issues"].append(f"Cache service error: {e}")

            # Check HTTP client health
            try:
                http_stats = await self.http_client.get_cache_stats()
                circuit_breakers = http_stats.get("circuit_breakers", {})

                http_health = {
                    "status": "healthy",
                    "circuit_breakers": len(circuit_breakers),
                    "open_circuits": 0,
                    "issues": []
                }

                for domain, breaker in circuit_breakers.items():
                    if breaker.get("state") == "open":
                        http_health["open_circuits"] += 1
                        http_health["issues"].append(f"Circuit breaker open for {domain}")

                if http_health["open_circuits"] > 0:
                    http_health["status"] = "warning"
                    health["issues"].append(f"{http_health['open_circuits']} circuit breakers are open")

                health["components"]["http_client"] = http_health

            except Exception as e:
                health["components"]["http_client"] = {
                    "status": "error",
                    "error": str(e)
                }
                health["issues"].append(f"HTTP client error: {e}")

            # Check data source health
            for source_name, client in self.data_source_clients.items():
                try:
                    if hasattr(client, 'get_cache_stats'):
                        source_stats = await client.get_cache_stats()

                        source_health = {
                            "status": "healthy",
                            "cached_entries": source_stats.get("db_entries", 0),
                            "issues": []
                        }

                        if source_stats.get("db_entries", 0) == 0:
                            source_health["status"] = "warning"
                            source_health["issues"].append("No cached data available")
                            health["recommendations"].append(f"Consider warming {source_name} cache")

                        health["components"][f"source_{source_name}"] = source_health

                except Exception as e:
                    health["components"][f"source_{source_name}"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health["issues"].append(f"{source_name} source error: {e}")

            # Determine overall health status
            component_statuses = [comp.get("status", "error") for comp in health["components"].values()]

            if "error" in component_statuses:
                health["overall_status"] = "error"
            elif "warning" in component_statuses or health["issues"]:
                health["overall_status"] = "warning"
            else:
                health["overall_status"] = "healthy"

        except Exception as e:
            logger.error(f"Error checking health stats: {e}")
            health["overall_status"] = "error"
            health["error"] = str(e)

        return health

    def _calculate_cache_efficiency(self, hit_rate: float) -> str:
        """Calculate cache efficiency rating based on hit rate."""
        if hit_rate >= 0.8:
            return "excellent"
        elif hit_rate >= 0.6:
            return "good"
        elif hit_rate >= 0.4:
            return "fair"
        elif hit_rate >= 0.2:
            return "poor"
        else:
            return "very_poor"

    async def _calculate_memory_utilization(self) -> dict[str, Any]:
        """Calculate memory cache utilization."""
        try:
            from app.core.config import settings

            overall_stats = await self.cache_service.get_stats()
            memory_entries = overall_stats.get("memory_entries", 0)
            max_memory_size = settings.CACHE_MAX_MEMORY_SIZE

            utilization_percent = (memory_entries / max_memory_size * 100) if max_memory_size > 0 else 0

            return {
                "current_entries": memory_entries,
                "max_entries": max_memory_size,
                "utilization_percent": round(utilization_percent, 2),
                "status": "high" if utilization_percent > 80 else "normal" if utilization_percent > 50 else "low"
            }

        except Exception as e:
            logger.error(f"Error calculating memory utilization: {e}")
            return {"error": str(e)}

    def _estimate_response_time_improvement(self, hit_rate: float) -> dict[str, Any]:
        """Estimate response time improvement from caching."""
        # Rough estimates based on typical API response times
        typical_api_time_ms = 500  # Average API response time
        cache_hit_time_ms = 10     # Cache hit response time

        avg_response_time = (hit_rate * cache_hit_time_ms) + ((1 - hit_rate) * typical_api_time_ms)
        improvement_factor = typical_api_time_ms / avg_response_time if avg_response_time > 0 else 1

        return {
            "estimated_avg_response_ms": round(avg_response_time, 2),
            "improvement_factor": round(improvement_factor, 2),
            "time_saved_percent": round((1 - avg_response_time / typical_api_time_ms) * 100, 2)
        }

    async def warm_all_caches(self) -> dict[str, Any]:
        """
        Warm all data source caches in parallel.

        Returns:
            Dictionary with warming results for each source
        """
        logger.info("Starting cache warming for all data sources...")

        results = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources": {},
            "total_entries_cached": 0,
            "errors": []
        }

        # Create warming tasks for all sources
        warming_tasks = {}
        for source_name, client in self.data_source_clients.items():
            if hasattr(client, 'warm_cache'):
                warming_tasks[source_name] = client.warm_cache()

        # Execute warming tasks in parallel
        if warming_tasks:
            task_results = await asyncio.gather(*warming_tasks.values(), return_exceptions=True)

            for i, (source_name, _task) in enumerate(warming_tasks.items()):
                result = task_results[i]

                if isinstance(result, Exception):
                    logger.error(f"Error warming {source_name} cache: {result}")
                    results["sources"][source_name] = {
                        "status": "error",
                        "error": str(result),
                        "entries_cached": 0
                    }
                    results["errors"].append(f"{source_name}: {result}")
                else:
                    results["sources"][source_name] = {
                        "status": "success",
                        "entries_cached": result
                    }
                    results["total_entries_cached"] += result

        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        duration = (
            datetime.fromisoformat(results["completed_at"]) -
            datetime.fromisoformat(results["started_at"])
        ).total_seconds()
        results["duration_seconds"] = round(duration, 2)

        logger.info(f"Cache warming completed: {results['total_entries_cached']} entries cached in {duration:.2f}s")

        return results

    async def clear_all_caches(self) -> dict[str, Any]:
        """
        Clear all data source caches.

        Returns:
            Dictionary with clearing results for each source
        """
        logger.info("Starting cache clearing for all data sources...")

        results = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "sources": {},
            "total_entries_cleared": 0,
            "errors": []
        }

        # Clear caches for all sources
        for source_name, client in self.data_source_clients.items():
            try:
                if hasattr(client, 'clear_cache'):
                    entries_cleared = await client.clear_cache()
                    results["sources"][source_name] = {
                        "status": "success",
                        "entries_cleared": entries_cleared
                    }
                    results["total_entries_cleared"] += entries_cleared
                else:
                    results["sources"][source_name] = {
                        "status": "skipped",
                        "reason": "No clear_cache method available"
                    }
            except Exception as e:
                logger.error(f"Error clearing {source_name} cache: {e}")
                results["sources"][source_name] = {
                    "status": "error",
                    "error": str(e),
                    "entries_cleared": 0
                }
                results["errors"].append(f"{source_name}: {e}")

        results["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Cache clearing completed: {results['total_entries_cleared']} entries cleared")

        return results


# Global monitoring service instance
_monitoring_service: CacheMonitoringService | None = None


def get_monitoring_service(db_session: Session | AsyncSession | None = None) -> CacheMonitoringService:
    """Get or create the global cache monitoring service instance."""
    global _monitoring_service

    if _monitoring_service is None:
        _monitoring_service = CacheMonitoringService(db_session)

    return _monitoring_service
