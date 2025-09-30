"""
Cache invalidation strategy for database views.
Ensures cache coherency when underlying data changes.
"""

import asyncio
from dataclasses import dataclass, field
from functools import wraps

from app.core.cache_service import CacheService
from app.core.logging import get_logger
from app.core.view_monitoring import track_cache_invalidation

logger = get_logger(__name__)


@dataclass
class ViewDependency:
    """Represents a view's dependencies on tables."""

    view_name: str
    depends_on_tables: set[str]
    cache_namespaces: set[str] = field(default_factory=set)


class CacheInvalidationManager:
    """
    Manages cache invalidation for database views.

    Tracks dependencies between views and tables to automatically
    invalidate caches when underlying data changes.
    """

    # View dependency mapping - defines which tables each view depends on
    VIEW_DEPENDENCIES: dict[str, ViewDependency] = {
        "gene_list_detailed": ViewDependency(
            view_name="gene_list_detailed",
            depends_on_tables={
                "genes",
                "gene_scores",
                "evidence_summary_view",
                "annotation_summary_view",
            },
            cache_namespaces={"views:gene_list", "api:genes"},
        ),
        "admin_logs_filtered": ViewDependency(
            view_name="admin_logs_filtered",
            depends_on_tables={"system_logs", "users"},
            cache_namespaces={"views:admin_logs", "api:logs"},
        ),
        "source_overlap_statistics": ViewDependency(
            view_name="source_overlap_statistics",
            depends_on_tables={"gene_evidence"},
            cache_namespaces={"views:statistics", "api:statistics"},
        ),
        "gene_distribution_analysis": ViewDependency(
            view_name="gene_distribution_analysis",
            depends_on_tables={"genes", "gene_scores"},
            cache_namespaces={"views:distribution", "api:statistics"},
        ),
        "upset_plot_data": ViewDependency(
            view_name="upset_plot_data",
            depends_on_tables={"gene_evidence"},
            cache_namespaces={"views:upset", "api:statistics"},
        ),
        "datasource_metadata_panelapp": ViewDependency(
            view_name="datasource_metadata_panelapp",
            depends_on_tables={"gene_evidence"},
            cache_namespaces={"views:datasource", "api:datasources"},
        ),
        "datasource_metadata_gencc": ViewDependency(
            view_name="datasource_metadata_gencc",
            depends_on_tables={"gene_evidence"},
            cache_namespaces={"views:datasource", "api:datasources"},
        ),
    }

    # Reverse mapping: table -> views that depend on it
    _table_to_views: dict[str, set[str]] | None = None

    def __init__(self, cache_service: CacheService):
        """
        Initialize the cache invalidation manager.

        Args:
            cache_service: The cache service to use for invalidation
        """
        self.cache_service = cache_service
        self._build_reverse_mapping()

    def _build_reverse_mapping(self):
        """Build reverse mapping of tables to dependent views."""
        self._table_to_views = {}

        for view_name, dep in self.VIEW_DEPENDENCIES.items():
            for table in dep.depends_on_tables:
                if table not in self._table_to_views:
                    self._table_to_views[table] = set()
                self._table_to_views[table].add(view_name)

        logger.info(
            "Built cache dependency mapping",
            view_count=len(self.VIEW_DEPENDENCIES),
            table_count=len(self._table_to_views),
        )

    async def invalidate_for_table(self, table_name: str) -> list[str]:
        """
        Invalidate all caches for views that depend on the given table.

        Args:
            table_name: Name of the table that was modified

        Returns:
            List of invalidated cache namespaces
        """
        invalidated = []

        # Find all views that depend on this table
        affected_views = self._table_to_views.get(table_name, set())

        logger.info(
            f"Invalidating caches for table {table_name}", affected_views=list(affected_views)
        )

        for view_name in affected_views:
            dep = self.VIEW_DEPENDENCIES.get(view_name)
            if dep:
                for namespace in dep.cache_namespaces:
                    try:
                        await self.cache_service.clear_namespace(namespace)
                        invalidated.append(namespace)

                        # Track invalidation in metrics
                        track_cache_invalidation(table_name, namespace)

                        logger.info(
                            f"Invalidated cache namespace {namespace}",
                            table=table_name,
                            view=view_name,
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to invalidate cache for {namespace}",
                            error=str(e),
                            table=table_name,
                            view=view_name,
                        )

        return invalidated

    async def invalidate_view(self, view_name: str) -> list[str]:
        """
        Invalidate caches for a specific view.

        Args:
            view_name: Name of the view to invalidate

        Returns:
            List of invalidated cache namespaces
        """
        invalidated = []

        dep = self.VIEW_DEPENDENCIES.get(view_name)
        if dep:
            logger.info(f"Invalidating caches for view {view_name}")

            for namespace in dep.cache_namespaces:
                try:
                    await self.cache_service.clear_namespace(namespace)
                    invalidated.append(namespace)

                    # Track invalidation
                    track_cache_invalidation(view_name, namespace)

                    logger.info(f"Invalidated cache namespace {namespace}", view=view_name)
                except Exception as e:
                    logger.error(
                        f"Failed to invalidate cache for {namespace}", view=view_name, error=str(e)
                    )
        else:
            logger.warning(f"No cache dependencies found for view {view_name}")

        return invalidated

    async def invalidate_all(self) -> list[str]:
        """
        Invalidate all view caches.

        Returns:
            List of all invalidated cache namespaces
        """
        logger.info("Invalidating all view caches")
        invalidated = []

        for view_name in self.VIEW_DEPENDENCIES:
            view_invalidated = await self.invalidate_view(view_name)
            invalidated.extend(view_invalidated)

        return invalidated

    def register_view_dependency(self, view_name: str, tables: set[str], namespaces: set[str]):
        """
        Register a new view dependency dynamically.

        Args:
            view_name: Name of the view
            tables: Set of tables the view depends on
            namespaces: Cache namespaces to invalidate
        """
        self.VIEW_DEPENDENCIES[view_name] = ViewDependency(
            view_name=view_name, depends_on_tables=tables, cache_namespaces=namespaces
        )

        # Update reverse mapping
        for table in tables:
            if table not in self._table_to_views:
                self._table_to_views[table] = set()
            self._table_to_views[table].add(view_name)

        logger.info(
            f"Registered view dependency: {view_name}",
            tables=list(tables),
            namespaces=list(namespaces),
        )

    def get_dependencies_for_table(self, table_name: str) -> set[str]:
        """
        Get all views that depend on a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Set of view names that depend on the table
        """
        return self._table_to_views.get(table_name, set()).copy()

    def get_dependencies_for_view(self, view_name: str) -> ViewDependency | None:
        """
        Get dependency information for a specific view.

        Args:
            view_name: Name of the view

        Returns:
            ViewDependency object or None if not found
        """
        return self.VIEW_DEPENDENCIES.get(view_name)


# Decorator for automatic cache invalidation
def invalidates_cache(*tables: str):
    """
    Decorator to automatically invalidate caches when tables are modified.

    Usage:
        @invalidates_cache("genes", "gene_scores")
        async def update_gene(gene_id: int, data: dict):
            ...
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute the function
            result = await func(*args, **kwargs)

            # Invalidate caches
            from app.core.dependencies import get_cache_invalidation_manager

            manager = await get_cache_invalidation_manager()

            for table in tables:
                await manager.invalidate_for_table(table)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Execute the function
            result = func(*args, **kwargs)

            # Schedule cache invalidation asynchronously
            asyncio.create_task(_invalidate_sync(tables))

            return result

        async def _invalidate_sync(table_names):
            """Helper to invalidate caches from sync context."""
            from app.core.dependencies import get_cache_invalidation_manager

            manager = await get_cache_invalidation_manager()

            for table in table_names:
                await manager.invalidate_for_table(table)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Batch invalidation context manager
class BatchInvalidation:
    """
    Context manager for batching cache invalidations.

    Collects invalidation requests and executes them all at once
    when the context exits.
    """

    def __init__(self, manager: CacheInvalidationManager):
        self.manager = manager
        self.pending_tables: set[str] = set()
        self.pending_views: set[str] = set()

    def add_table(self, table_name: str):
        """Add a table to the pending invalidation list."""
        self.pending_tables.add(table_name)

    def add_view(self, view_name: str):
        """Add a view to the pending invalidation list."""
        self.pending_views.add(view_name)

    async def __aenter__(self):
        """Enter the batch context."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Execute all pending invalidations."""
        invalidated = []

        # Invalidate by table
        for table in self.pending_tables:
            result = await self.manager.invalidate_for_table(table)
            invalidated.extend(result)

        # Invalidate by view
        for view in self.pending_views:
            result = await self.manager.invalidate_view(view)
            invalidated.extend(result)

        if invalidated:
            logger.info(
                "Batch invalidation complete",
                namespaces_invalidated=len(set(invalidated)),
                tables=list(self.pending_tables),
                views=list(self.pending_views),
            )

        return False  # Don't suppress exceptions
