"""
Application startup functions

This module handles dynamic initialization tasks that should run on app startup,
including data source registration and system health checks.
"""

from datetime import datetime, timezone

from app.core.database import get_db
from app.core.datasource_config import DATA_SOURCE_CONFIG
from app.core.logging import get_logger
from app.models.progress import DataSourceProgress, SourceStatus

logger = get_logger(__name__)


def register_data_sources() -> None:
    """
    Register all configured data sources in the database if they don't exist.

    This ensures that progress tracking records exist for all data sources
    without requiring manual database seeding or migrations.
    """
    logger.sync_info("Registering data sources...")

    db = next(get_db())
    try:
        registered_count = 0
        updated_count = 0

        # Skip manual upload sources from progress tracking
        manual_upload_sources = ["DiagnosticPanels"]

        for source_name, config in DATA_SOURCE_CONFIG.items():
            # Skip manual upload sources - they don't need progress tracking
            if source_name in manual_upload_sources:
                continue

            # Check if progress record exists
            existing = db.query(DataSourceProgress).filter_by(source_name=source_name).first()

            if existing:
                # Update metadata if configuration has changed
                new_metadata = {
                    "auto_update": config.get("auto_update", False),
                    "priority": config.get("priority", 999),
                    "display_name": config.get("display_name", source_name),
                    "description": config.get("description", ""),
                    "url": config.get("url"),
                    "documentation_url": config.get("documentation_url"),
                }

                if existing.progress_metadata != new_metadata:
                    existing.progress_metadata = new_metadata
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                    logger.sync_debug(
                        f"Updated metadata for {source_name}",
                        source=source_name,
                        action="metadata_update",
                    )
            else:
                # Create new progress record
                progress_record = DataSourceProgress(
                    source_name=source_name,
                    status=SourceStatus.idle,
                    progress_metadata={
                        "auto_update": config.get("auto_update", False),
                        "priority": config.get("priority", 999),
                        "display_name": config.get("display_name", source_name),
                        "description": config.get("description", ""),
                        "url": config.get("url"),
                        "documentation_url": config.get("documentation_url"),
                    },
                )
                db.add(progress_record)
                registered_count += 1
                logger.sync_debug(
                    f"Registered new data source: {source_name}",
                    source=source_name,
                    action="register_new",
                )

        db.commit()

        if registered_count > 0 or updated_count > 0:
            logger.sync_info(
                "Data source registration complete",
                registered_count=registered_count,
                updated_count=updated_count,
            )
        else:
            logger.sync_info("All data sources already registered and up-to-date")

    except Exception as e:
        logger.sync_error("Failed to register data sources", error=e)
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_orphaned_sources() -> None:
    """
    Remove progress records for data sources that are no longer configured.

    This helps keep the database clean when data sources are removed from
    the application configuration.
    """
    logger.sync_info("Cleaning up orphaned data source records...")

    db = next(get_db())
    try:
        # Exclude manual upload sources from configured sources for progress tracking
        manual_upload_sources = ["DiagnosticPanels"]
        configured_sources = {
            k for k in DATA_SOURCE_CONFIG.keys() if k not in manual_upload_sources
        }

        # Find progress records for sources not in current config
        orphaned = (
            db.query(DataSourceProgress)
            .filter(~DataSourceProgress.source_name.in_(configured_sources))
            .all()
        )

        if orphaned:
            orphaned_names = [record.source_name for record in orphaned]
            logger.sync_warning("Found orphaned data source records", orphaned_names=orphaned_names)

            # Don't automatically delete - log for manual review
            logger.sync_warning(
                "Orphaned records found but not automatically removed",
                action_required="Review and manually remove if no longer needed",
            )
        else:
            logger.sync_info("No orphaned data source records found")

    except Exception as e:
        logger.sync_error("Failed to cleanup orphaned sources", error=e)
        raise
    finally:
        db.close()


def validate_dependencies() -> None:
    """
    Validate that all required dependencies and settings are available.

    This helps identify configuration issues early in the startup process.
    """
    logger.sync_info("Validating application dependencies...")

    try:
        from app.core.datasource_config import get_source_parameter

        # Validate required API URLs from datasource config
        required_urls = {
            "PubTator API": get_source_parameter("PubTator", "api_url"),
            "PanelApp UK API": get_source_parameter("PanelApp", "uk_api_url"),
            "PanelApp AU API": get_source_parameter("PanelApp", "au_api_url"),
            "HPO API": get_source_parameter("HPO", "api_url"),
            "HGNC API": get_source_parameter("HGNC", "api_url"),
        }

        for source_name, url in required_urls.items():
            if not url or not url.startswith("http"):
                logger.sync_warning(
                    f"Invalid {source_name} URL: {url}", source_name=source_name, url=url
                )

        # Test cache service initialization
        try:
            from app.core.cache_service import get_cache_service

            cache = get_cache_service()
            logger.sync_info("Cache service initialized", enabled=cache.enabled)
        except Exception as e:
            logger.sync_error("Cache service initialization failed", error=e)

        # Test HTTP client initialization
        try:
            from app.core.cached_http_client import get_cached_http_client

            get_cached_http_client()
            logger.sync_info("HTTP client initialized successfully")
        except Exception as e:
            logger.sync_error("HTTP client initialization failed", error=e)

        logger.sync_info("Dependency validation completed")

    except Exception as e:
        logger.sync_error("Dependency validation failed", error=e)
        # Don't re-raise - log the issue but continue startup


def run_startup_tasks() -> None:
    """
    Run all startup tasks for the application.

    This is the main entry point called from the FastAPI startup event.
    """
    logger.sync_info("Running application startup tasks...")

    try:
        # Validate dependencies first
        validate_dependencies()

        # Register data sources
        register_data_sources()

        # Cleanup orphaned records
        cleanup_orphaned_sources()

        logger.sync_info("Application startup tasks completed successfully")

    except Exception as e:
        logger.sync_error("Startup tasks failed", error=e)
        # Don't re-raise - allow app to start even if startup tasks fail
        # This prevents the app from failing to start due to database issues
