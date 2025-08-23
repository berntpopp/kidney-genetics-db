"""
Cache management API endpoints.

Provides administrative endpoints for:
- Cache statistics and monitoring
- Cache clearing and management
- Cache warming and preloading
- Health checks and diagnostics
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.cache_service import get_cache_service
from app.core.cached_http_client import get_cached_http_client
from app.core.config import settings
from app.core.database import get_pool_status
from app.core.datasource_config import get_source_cache_ttl
from app.core.exceptions import CacheError, ValidationError
from app.core.logging import get_logger
from app.core.monitoring import get_monitoring_service

logger = get_logger(__name__)

router = APIRouter()

# Pydantic models for API responses


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""

    namespace: str | None = None
    total_entries: int = Field(ge=0, description="Total number of cache entries")
    memory_entries: int = Field(ge=0, description="Number of entries in memory cache")
    db_entries: int = Field(ge=0, description="Number of entries in database cache")
    hits: int = Field(ge=0, description="Cache hits")
    misses: int = Field(ge=0, description="Cache misses")
    hit_rate: float = Field(ge=0.0, le=1.0, description="Cache hit rate")
    total_size_bytes: int = Field(ge=0, description="Total cache size in bytes")
    total_size_mb: float = Field(ge=0.0, description="Total cache size in MB")


class NamespaceStatsResponse(BaseModel):
    """Namespace-specific cache statistics."""

    namespace: str
    total_entries: int = Field(ge=0)
    active_entries: int = Field(ge=0, description="Non-expired entries")
    expired_entries: int = Field(ge=0, description="Expired entries")
    total_accesses: int = Field(ge=0)
    avg_accesses: float = Field(ge=0.0)
    total_size_bytes: int = Field(ge=0)
    last_access_time: datetime | None = None
    oldest_entry: datetime | None = None
    newest_entry: datetime | None = None


class CacheHealthResponse(BaseModel):
    """Cache system health response."""

    status: str = Field(description="Overall health status")
    cache_enabled: bool
    memory_cache_size: int = Field(ge=0)
    database_connected: bool
    http_cache_size_mb: float = Field(ge=0.0)
    namespaces: list[str]
    issues: list[str] = Field(default_factory=list)
    last_cleanup: datetime | None = None


class CacheKeyListResponse(BaseModel):
    """Cache key listing response."""

    namespace: str
    keys: list[str]
    total_keys: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    has_more: bool


class CacheClearResponse(BaseModel):
    """Cache clear operation response."""

    success: bool
    entries_cleared: int = Field(ge=0)
    namespace: str | None = None
    message: str


class CacheWarmRequest(BaseModel):
    """Cache warming request model."""

    sources: list[str] = Field(description="Data sources to warm up")
    force_refresh: bool = Field(default=False, description="Force refresh of existing cache")
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")


class CacheWarmResponse(BaseModel):
    """Cache warming response."""

    success: bool
    sources_warmed: list[str]
    entries_created: int = Field(ge=0)
    time_taken_seconds: float = Field(ge=0.0)
    message: str


# API endpoints


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    namespace: str | None = Query(None, description="Specific namespace to get stats for"),
    db: AsyncSession = Depends(get_db),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Returns overall cache performance metrics including hit rates,
    memory usage, and entry counts.
    """
    try:
        cache_service = get_cache_service(db)
        stats = await cache_service.get_stats(namespace)

        # Convert to response model
        total_size_mb = stats.get("total_size", 0) / (1024 * 1024)

        return CacheStatsResponse(
            namespace=namespace,
            total_entries=stats.get("memory_entries", 0) + stats.get("db_entries", 0),
            memory_entries=stats.get("memory_entries", 0),
            db_entries=stats.get("db_entries", 0),
            hits=stats.get("hits", 0),
            misses=stats.get("misses", 0),
            hit_rate=stats.get("hit_rate", 0.0),
            total_size_bytes=stats.get("total_size", 0),
            total_size_mb=total_size_mb,
        )

    except Exception as e:
        await logger.error("Error getting cache stats", error=e, namespace=namespace)
        raise CacheError("get_stats", detail=str(e)) from e


@router.get("/stats/{namespace}", response_model=NamespaceStatsResponse)
async def get_namespace_stats(
    namespace: str, db: AsyncSession = Depends(get_db)
) -> NamespaceStatsResponse:
    """
    Get detailed statistics for a specific cache namespace.
    """
    try:
        cache_service = get_cache_service(db)
        stats = await cache_service._get_namespace_stats(namespace)

        if not stats:
            raise ValidationError(field="namespace", reason=f"Namespace '{namespace}' not found")

        return NamespaceStatsResponse(
            namespace=namespace,
            total_entries=stats.get("total_entries", 0),
            active_entries=stats.get("active_entries", 0),
            expired_entries=stats.get("expired_entries", 0),
            total_accesses=stats.get("total_accesses", 0),
            avg_accesses=stats.get("avg_accesses", 0.0),
            total_size_bytes=stats.get("total_size_bytes", 0),
            last_access_time=stats.get("last_access_time"),
            oldest_entry=stats.get("oldest_entry"),
            newest_entry=stats.get("newest_entry"),
        )

    except CacheError:
        raise
    except Exception as e:
        await logger.error("Error getting namespace stats", error=e, namespace=namespace)
        raise CacheError("get_namespace_stats", detail=str(e)) from e


@router.get("/health", response_model=CacheHealthResponse)
async def get_cache_health(db: AsyncSession = Depends(get_db)) -> CacheHealthResponse:
    """
    Get cache system health status.

    Performs health checks on all cache components and returns
    overall system status.
    """
    try:
        cache_service = get_cache_service(db)
        http_client = get_cached_http_client()

        issues = []

        # Check if cache is enabled
        if not settings.CACHE_ENABLED:
            issues.append("Cache system is disabled in configuration")

        # Test database connectivity
        database_connected = True
        try:
            await cache_service._get_db_entry_count()
        except Exception as e:
            database_connected = False
            issues.append(f"Database connection error: {e!s}")

        # Get cache statistics
        stats = await cache_service.get_stats()
        http_stats = await http_client.get_cache_stats()

        # Check for potential issues
        hit_rate = stats.get("hit_rate", 0.0)
        if hit_rate < 0.5:  # Less than 50% hit rate
            issues.append(f"Low cache hit rate: {hit_rate:.1%}")

        memory_entries = stats.get("memory_entries", 0)
        if memory_entries >= settings.CACHE_MAX_MEMORY_SIZE * 0.9:  # 90% full
            issues.append("Memory cache near capacity")

        # Determine overall status
        if not database_connected or not settings.CACHE_ENABLED:
            status = "critical"
        elif issues:
            status = "warning"
        else:
            status = "healthy"

        # Get namespace list dynamically from database
        namespaces = await cache_service.get_distinct_namespaces()
        if not namespaces:
            # Fallback to known namespaces if database query fails
            await logger.warning("Using fallback namespace list", namespaces_count=len(namespaces))
            namespaces = [
                "hgnc",
                "pubtator",
                "gencc",
                "panelapp",
                "hpo",
                "clingen",
                "http",
                "files",
            ]

        return CacheHealthResponse(
            status=status,
            cache_enabled=settings.CACHE_ENABLED,
            memory_cache_size=memory_entries,
            database_connected=database_connected,
            http_cache_size_mb=http_stats.get("http_cache", {}).get("total_size_mb", 0.0),
            namespaces=namespaces,
            issues=issues,
            last_cleanup=None,  # Would track last cleanup time
        )

    except Exception as e:
        await logger.error("Error getting cache health", error=e)
        raise CacheError("get_health", detail=str(e)) from e


@router.get("/keys/{namespace}", response_model=CacheKeyListResponse)
async def list_cache_keys(
    namespace: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> CacheKeyListResponse:
    """
    List cache keys in a namespace with pagination.
    """
    try:
        # This would require implementing pagination in the cache service
        # For now, return a placeholder implementation
        get_cache_service(db)

        # TODO: Implement actual key listing with pagination
        # This is a complex operation that would require database queries

        return CacheKeyListResponse(
            namespace=namespace,
            keys=[],  # Placeholder
            total_keys=0,
            page=page,
            page_size=page_size,
            has_more=False,
        )

    except Exception as e:
        await logger.error("Error listing cache keys", error=e, namespace=namespace)
        raise CacheError("list_keys", detail=str(e)) from e


@router.delete("/{namespace}", response_model=CacheClearResponse)
async def clear_namespace(namespace: str, db: AsyncSession = Depends(get_db)) -> CacheClearResponse:
    """
    Clear all cache entries in a specific namespace.
    """
    try:
        cache_service = get_cache_service(db)
        entries_cleared = await cache_service.clear_namespace(namespace)

        return CacheClearResponse(
            success=True,
            entries_cleared=entries_cleared,
            namespace=namespace,
            message=f"Successfully cleared {entries_cleared} entries from namespace '{namespace}'",
        )

    except Exception as e:
        await logger.error("Error clearing namespace", error=e, namespace=namespace)
        raise CacheError("clear_namespace", detail=str(e)) from e


@router.delete("/{namespace}/{key}", response_model=CacheClearResponse)
async def delete_cache_key(
    namespace: str, key: str, db: AsyncSession = Depends(get_db)
) -> CacheClearResponse:
    """
    Delete a specific cache key.
    """
    try:
        cache_service = get_cache_service(db)
        success = await cache_service.delete(key, namespace)

        return CacheClearResponse(
            success=success,
            entries_cleared=1 if success else 0,
            namespace=namespace,
            message=f"Cache key '{key}' {'deleted' if success else 'not found'} in namespace '{namespace}'",
        )

    except Exception as e:
        await logger.error("Error deleting cache key", error=e, namespace=namespace, key=key)
        raise CacheError("cache_operation", detail=f"Error deleting cache key: {e!s}") from e


@router.post("/cleanup")
async def cleanup_expired_entries(db: AsyncSession = Depends(get_db)) -> CacheClearResponse:
    """
    Manually trigger cleanup of expired cache entries.
    """
    try:
        cache_service = get_cache_service(db)
        entries_cleared = await cache_service.cleanup_expired()

        return CacheClearResponse(
            success=True,
            entries_cleared=entries_cleared,
            namespace=None,
            message=f"Successfully cleaned up {entries_cleared} expired cache entries",
        )

    except Exception as e:
        await logger.error("Error during cache cleanup", error=e)
        raise CacheError("cache_operation", detail=f"Error during cache cleanup: {e!s}") from e


@router.post("/warm", response_model=CacheWarmResponse)
async def warm_cache(
    request: CacheWarmRequest, db: AsyncSession = Depends(get_db)
) -> CacheWarmResponse:
    """
    Warm up cache by preloading data from specified sources.

    This endpoint can be used to preload frequently accessed data
    to improve performance during peak usage.
    """
    try:
        start_time = datetime.now(timezone.utc)

        # TODO: Implement actual cache warming logic
        # This would involve calling the respective data source clients
        # to preload commonly accessed data

        sources_warmed = []
        entries_created = 0

        for source in request.sources:
            if source.lower() in ["hgnc", "pubtator", "gencc", "panelapp", "hpo", "clingen"]:
                # Placeholder for warming logic
                await logger.info("Warming cache for source", source=source, force_refresh=request.force_refresh)
                sources_warmed.append(source)
                # entries_created += await warm_source_cache(source, request.force_refresh)

        end_time = datetime.now(timezone.utc)
        time_taken = (end_time - start_time).total_seconds()

        return CacheWarmResponse(
            success=True,
            sources_warmed=sources_warmed,
            entries_created=entries_created,
            time_taken_seconds=time_taken,
            message=f"Cache warming completed for {len(sources_warmed)} sources",
        )

    except Exception as e:
        await logger.error("Error during cache warming", error=e, sources=request.sources)
        raise CacheError("cache_operation", detail=f"Error during cache warming: {e!s}") from e


@router.get("/config")
async def get_cache_config() -> dict[str, Any]:
    """
    Get current cache configuration settings.
    """
    return {
        "enabled": settings.CACHE_ENABLED,
        "default_ttl": settings.CACHE_DEFAULT_TTL,
        "max_memory_size": settings.CACHE_MAX_MEMORY_SIZE,
        "cleanup_interval": settings.CACHE_CLEANUP_INTERVAL,
        "namespace_ttls": {
            "hgnc": get_source_cache_ttl("HGNC"),
            "pubtator": get_source_cache_ttl("PubTator"),
            "gencc": get_source_cache_ttl("GenCC"),
            "panelapp": get_source_cache_ttl("PanelApp"),
            "hpo": get_source_cache_ttl("HPO"),
            "clingen": get_source_cache_ttl("ClinGen"),
        },
        "http_cache": {
            "enabled": settings.HTTP_CACHE_ENABLED,
            "directory": settings.HTTP_CACHE_DIR,
            "max_size_mb": settings.HTTP_CACHE_MAX_SIZE_MB,
            "default_ttl": settings.HTTP_CACHE_TTL_DEFAULT,
        },
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)) -> Response:
    """
    Get cache metrics in Prometheus format for monitoring.
    """
    try:
        cache_service = get_cache_service(db)
        stats = await cache_service.get_stats()

        # Generate Prometheus metrics format
        metrics = []
        metrics.append("# HELP cache_hits_total Total number of cache hits")
        metrics.append("# TYPE cache_hits_total counter")
        metrics.append(f"cache_hits_total {stats.get('hits', 0)}")

        metrics.append("# HELP cache_misses_total Total number of cache misses")
        metrics.append("# TYPE cache_misses_total counter")
        metrics.append(f"cache_misses_total {stats.get('misses', 0)}")

        metrics.append("# HELP cache_hit_rate Current cache hit rate")
        metrics.append("# TYPE cache_hit_rate gauge")
        metrics.append(f"cache_hit_rate {stats.get('hit_rate', 0.0)}")

        metrics.append("# HELP cache_memory_entries Current number of entries in memory cache")
        metrics.append("# TYPE cache_memory_entries gauge")
        metrics.append(f"cache_memory_entries {stats.get('memory_entries', 0)}")

        metrics.append("# HELP cache_db_entries Current number of entries in database cache")
        metrics.append("# TYPE cache_db_entries gauge")
        metrics.append(f"cache_db_entries {stats.get('db_entries', 0)}")

        metrics_text = "\n".join(metrics)

        return Response(content=metrics_text, media_type="text/plain; charset=utf-8")

    except Exception as e:
        await logger.error("Error generating Prometheus metrics", error=e)
        raise CacheError("cache_operation", detail=f"Error generating metrics: {e!s}") from e


@router.get("/monitoring/dashboard")
async def get_monitoring_dashboard(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Get comprehensive monitoring dashboard data.

    Provides detailed statistics, performance metrics, and health status
    across all cache components and data sources.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        dashboard_data = await monitoring_service.get_comprehensive_stats()

        return dashboard_data

    except Exception as e:
        await logger.error("Error getting monitoring dashboard", error=e)
        raise CacheError("cache_operation", detail=f"Error getting dashboard data: {e!s}") from e


@router.get("/monitoring/performance")
async def get_performance_metrics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Get detailed performance metrics for cache optimization.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        stats = await monitoring_service.get_comprehensive_stats()

        return {
            "performance": stats.get("performance", {}),
            "namespaces": stats.get("namespaces", {}),
            "recommendations": stats.get("health", {}).get("recommendations", []),
        }

    except Exception as e:
        await logger.error("Error getting performance metrics", error=e)
        raise CacheError("get_performance_metrics", detail=str(e)) from e


@router.post("/monitoring/warm-all")
async def warm_all_caches(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Warm all data source caches in parallel.

    This endpoint triggers cache warming for all supported data sources
    to improve performance during peak usage.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        results = await monitoring_service.warm_all_caches()

        return {
            "success": True,
            "message": f"Cache warming completed: {results['total_entries_cached']} entries cached",
            "results": results,
        }

    except Exception as e:
        await logger.error("Error warming all caches", error=e)
        raise CacheError("cache_operation", detail=f"Error warming caches: {e!s}") from e


@router.post("/monitoring/clear-all")
async def clear_all_caches(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Clear all data source caches.

    This endpoint clears all cache entries across all data sources.
    Use with caution as this will impact performance until caches are rebuilt.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        results = await monitoring_service.clear_all_caches()

        return {
            "success": True,
            "message": f"Cache clearing completed: {results['total_entries_cleared']} entries cleared",
            "results": results,
        }

    except Exception as e:
        await logger.error("Error clearing all caches", error=e)
        raise CacheError("cache_operation", detail=f"Error clearing caches: {e!s}") from e


@router.get("/monitoring/health")
async def get_cache_system_health(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Get comprehensive health status of the cache system.

    Provides health checks for all cache components including
    circuit breakers, data sources, and performance indicators.
    """
    try:
        monitoring_service = get_monitoring_service(db)
        stats = await monitoring_service.get_comprehensive_stats()

        health_data = stats.get("health", {})

        # Add summary information
        summary = {
            "overall_status": health_data.get("overall_status", "unknown"),
            "components_healthy": len(
                [
                    c
                    for c in health_data.get("components", {}).values()
                    if c.get("status") == "healthy"
                ]
            ),
            "total_components": len(health_data.get("components", {})),
            "issues_count": len(health_data.get("issues", [])),
            "recommendations_count": len(health_data.get("recommendations", [])),
        }

        return {"summary": summary, "health": health_data, "timestamp": stats.get("timestamp")}

    except Exception as e:
        await logger.error("Error getting cache system health", error=e)
        raise CacheError("cache_operation", detail=f"Error getting health status: {e!s}") from e


@router.get("/database/pool-health")
async def get_database_pool_health() -> dict[str, Any]:
    """
    Get database connection pool health metrics.

    MONITORING: Tracks connection pool usage to detect leaks and optimize performance.
    Returns pool size, connections in use, overflow status, and historical statistics.
    """
    try:
        pool_status = get_pool_status()

        # Calculate health indicators
        total_connections = pool_status["total"]
        checked_out = pool_status["checked_in"]

        # Determine health status
        if checked_out > total_connections * 0.9:  # >90% connections in use
            health_status = "critical"
            health_message = "Connection pool near exhaustion"
        elif checked_out > total_connections * 0.7:  # >70% connections in use
            health_status = "warning"
            health_message = "High connection pool usage"
        else:
            health_status = "healthy"
            health_message = "Connection pool operating normally"

        # Check for potential leaks
        stats = pool_status["stats"]
        potential_leak = False
        if stats["connections_checked_out"] > stats["connections_checked_in"] + 10:
            potential_leak = True
            health_status = "warning"
            health_message = "Potential connection leak detected"

        return {
            "status": health_status,
            "message": health_message,
            "pool": {
                "size": pool_status["size"],
                "checked_out": checked_out,
                "overflow": pool_status["overflow"],
                "total": total_connections,
            },
            "statistics": stats,
            "potential_leak": potential_leak,
        }

    except Exception as e:
        await logger.error("Error getting database pool health", error=e)
        raise CacheError("cache_operation", detail=f"Error getting pool health: {e!s}") from e
