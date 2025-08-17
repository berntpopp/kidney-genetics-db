"""
Application startup functions

This module handles dynamic initialization tasks that should run on app startup,
including data source registration and system health checks.
"""

import logging
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.datasource_config import DATA_SOURCE_CONFIG
from app.models.progress import DataSourceProgress, SourceStatus

logger = logging.getLogger(__name__)


def register_data_sources() -> None:
    """
    Register all configured data sources in the database if they don't exist.

    This ensures that progress tracking records exist for all data sources
    without requiring manual database seeding or migrations.
    """
    logger.info("Registering data sources...")

    db = next(get_db())
    try:
        registered_count = 0
        updated_count = 0

        for source_name, config in DATA_SOURCE_CONFIG.items():
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
                    logger.debug(f"Updated metadata for {source_name}")
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
                logger.debug(f"Registered new data source: {source_name}")

        db.commit()

        if registered_count > 0 or updated_count > 0:
            logger.info(
                f"Data source registration complete: "
                f"{registered_count} new, {updated_count} updated"
            )
        else:
            logger.info("All data sources already registered and up-to-date")

    except Exception as e:
        logger.error(f"Failed to register data sources: {e}")
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
    logger.info("Cleaning up orphaned data source records...")

    db = next(get_db())
    try:
        configured_sources = set(DATA_SOURCE_CONFIG.keys())

        # Find progress records for sources not in current config
        orphaned = (
            db.query(DataSourceProgress)
            .filter(~DataSourceProgress.source_name.in_(configured_sources))
            .all()
        )

        if orphaned:
            orphaned_names = [record.source_name for record in orphaned]
            logger.warning(f"Found orphaned data source records: {orphaned_names}")

            # Don't automatically delete - log for manual review
            logger.warning(
                "Orphaned records found but not automatically removed. "
                "Review and manually remove if no longer needed."
            )
        else:
            logger.info("No orphaned data source records found")

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned sources: {e}")
        raise
    finally:
        db.close()


def validate_dependencies() -> None:
    """
    Validate that all required dependencies and settings are available.

    This helps identify configuration issues early in the startup process.
    """
    logger.info("Validating application dependencies...")

    try:
        from app.core.config import settings

        # Validate required API URLs
        required_urls = {
            "PUBTATOR_API_URL": settings.PUBTATOR_API_URL,
            "PANELAPP_UK_URL": settings.PANELAPP_UK_URL,
            "PANELAPP_AU_URL": settings.PANELAPP_AU_URL,
            "HPO_API_URL": settings.HPO_API_URL,
            "HGNC_API_URL": settings.HGNC_API_URL,
        }

        for setting_name, url in required_urls.items():
            if not url or not url.startswith("http"):
                logger.warning(f"Invalid {setting_name}: {url}")

        # Test cache service initialization
        try:
            from app.core.cache_service import get_cache_service

            cache = get_cache_service()
            logger.info(f"Cache service initialized: enabled={cache.enabled}")
        except Exception as e:
            logger.error(f"Cache service initialization failed: {e}")

        # Test HTTP client initialization
        try:
            from app.core.cached_http_client import get_cached_http_client

            get_cached_http_client()
            logger.info("HTTP client initialized successfully")
        except Exception as e:
            logger.error(f"HTTP client initialization failed: {e}")

        logger.info("Dependency validation completed")

    except Exception as e:
        logger.error(f"Dependency validation failed: {e}")
        # Don't re-raise - log the issue but continue startup


def run_startup_tasks() -> None:
    """
    Run all startup tasks for the application.

    This is the main entry point called from the FastAPI startup event.
    """
    logger.info("Running application startup tasks...")

    try:
        # Validate dependencies first
        validate_dependencies()

        # Register data sources
        register_data_sources()

        # Cleanup orphaned records
        cleanup_orphaned_sources()

        logger.info("Application startup tasks completed successfully")

    except Exception as e:
        logger.error(f"Startup tasks failed: {e}")
        # Don't re-raise - allow app to start even if startup tasks fail
        # This prevents the app from failing to start due to database issues
