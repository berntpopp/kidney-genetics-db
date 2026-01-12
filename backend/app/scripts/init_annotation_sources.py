#!/usr/bin/env python3
"""
Initialize all annotation sources in the database from YAML configuration.
This script ensures all annotation sources are properly registered and configured.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import yaml

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.gene_annotation import AnnotationSource

logger = get_logger(__name__)


def load_annotation_config() -> dict[str, Any]:
    """Load annotation source configuration from YAML file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "annotations.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    annotations = config.get("annotations", {}) if config else {}
    return cast(dict[str, Any], annotations)


def prepare_annotation_sources(config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Prepare annotation source configurations from YAML data.

    Args:
        config: Dictionary of annotation configurations from YAML

    Returns:
        List of annotation source configurations ready for database insertion
    """
    sources = []

    for source_name, source_config in config.items():
        # Skip the 'common' section
        if source_name == "common":
            continue

        # Extract database fields
        db_config = {
            "source_name": source_name,
            "display_name": source_config.get("display_name", source_name),
            "description": source_config.get("description", ""),
            "base_url": source_config.get("base_url", ""),
            "update_frequency": source_config.get("update_frequency", "quarterly"),
            "is_active": source_config.get("is_active", True),
            "priority": source_config.get("priority", 0),
        }

        # Extract config parameters (everything else goes into the JSON config field)
        config_params = {}
        skip_fields = {
            "display_name",
            "description",
            "base_url",
            "update_frequency",
            "is_active",
            "priority",
        }

        for key, value in source_config.items():
            if key not in skip_fields:
                config_params[key] = value

        # Ensure cache_ttl_days and batch_size are present
        if "cache_ttl_days" not in config_params:
            config_params["cache_ttl_days"] = 90
        if "batch_size" not in config_params:
            config_params["batch_size"] = 100
        if "requests_per_second" not in config_params:
            config_params["requests_per_second"] = 5.0

        db_config["config"] = config_params
        sources.append(db_config)

    # Sort by priority (highest first)
    sources.sort(key=lambda x: x["priority"], reverse=True)

    return sources


async def init_annotation_sources() -> dict[str, Any]:
    """Initialize all annotation sources in the database from YAML configuration."""

    # Get database session
    db = next(get_db())

    try:
        await logger.info("Loading annotation source configuration from YAML")

        # Load configuration from YAML
        config = load_annotation_config()
        annotation_sources = prepare_annotation_sources(config)

        await logger.info(f"Found {len(annotation_sources)} annotation sources in configuration")

        created_count = 0
        updated_count = 0

        for source_config in annotation_sources:
            # Check if source already exists
            existing = (
                db.query(AnnotationSource)
                .filter_by(source_name=source_config["source_name"])
                .first()
            )

            if existing:
                # Update existing source
                for key, value in source_config.items():
                    if key != "source_name":  # Don't update the primary identifier
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
                await logger.info(f"Updated annotation source: {source_config['source_name']}")
            else:
                # Create new source
                new_source = AnnotationSource(**source_config)
                new_source.created_at = datetime.now(timezone.utc)
                new_source.updated_at = datetime.now(timezone.utc)
                db.add(new_source)
                created_count += 1
                await logger.info(f"Created annotation source: {source_config['source_name']}")

        # Commit all changes
        db.commit()

        await logger.info(
            "Annotation source initialization complete",
            created=created_count,
            updated=updated_count,
            total=len(annotation_sources),
        )

        # Display current status
        all_sources = db.query(AnnotationSource).order_by(AnnotationSource.priority.desc()).all()
        await logger.info("Current annotation sources status:")
        for source in all_sources:
            await logger.info(
                f"  - {source.source_name}: active={source.is_active}, "
                f"priority={source.priority}, last_update={source.last_update}"
            )

        return {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(all_sources),
        }

    except Exception as e:
        await logger.error(f"Failed to initialize annotation sources: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


async def clear_corrupted_cache() -> None:
    """Clear any corrupted cache entries to prevent deserialization errors."""

    db = next(get_db())

    try:
        await logger.info("Clearing cache to prevent corruption issues")

        # Clear all cache entries to ensure clean slate
        from app.models.cache import CacheEntry

        cache_count = db.query(CacheEntry).count()
        if cache_count > 0:
            db.query(CacheEntry).delete()
            db.commit()
            await logger.info(f"Cleared {cache_count} cache entries")
        else:
            await logger.info("Cache already empty")

    except Exception as e:
        await logger.error(f"Failed to clear cache: {str(e)}")
        db.rollback()
    finally:
        db.close()


async def main() -> None:
    """Main entry point for the script."""

    # Clear cache first to prevent issues
    await clear_corrupted_cache()

    # Initialize annotation sources from YAML
    result = await init_annotation_sources()

    if result["success"]:
        print(f"\n✅ Successfully initialized {result['total']} annotation sources from YAML")
        print(f"   Created: {result['created']}")
        print(f"   Updated: {result['updated']}")
        print("\n🚀 You can now run the annotation pipeline to fetch data from all sources")
    else:
        print("\n❌ Failed to initialize annotation sources")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
