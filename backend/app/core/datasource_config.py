"""
Data source configuration settings

This module loads configuration from YAML files with environment variable overrides.
REFACTORED: Using pydantic-settings with YAML sources for external configuration

Maintains 100% backward compatibility with all existing APIs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import settings
from app.core.logging import get_logger
from app.core.yaml_config_source import MultiYamlConfigSource

logger = get_logger(__name__)


class DataSourceConfig(BaseSettings):
    """
    Main configuration class using pydantic-settings.

    Loads configuration from YAML files with environment variable overrides.
    Environment variables use the pattern: KG_<SOURCE>__<PARAM>
    For example: KG_PANELAPP__UK_API_URL
    """

    model_config = SettingsConfigDict(
        env_prefix="KG_",
        env_nested_delimiter="__",
        case_sensitive=False,
        validate_default=False,  # Don't validate defaults from YAML
    )

    # These will be populated from YAML files
    datasources: dict[str, Any] = {}
    keywords: dict[str, list[str]] = {}
    annotations: dict[str, Any] = {}
    api_defaults: dict[str, Any] = {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """
        Define source priority: environment variables override YAML files.

        The order matters - later sources override earlier ones.
        """
        config_dir = Path(settings.CONFIG_DIR)

        # Load all YAML files
        yaml_source = MultiYamlConfigSource(
            settings_cls,
            yaml_files=[
                config_dir / "datasources.yaml",
                config_dir / "keywords.yaml",
                config_dir / "annotations.yaml",
                config_dir / "api_defaults.yaml",
            ],
        )

        return (
            init_settings,
            yaml_source,  # YAML as base configuration
            env_settings,  # Environment variables override YAML
            dotenv_settings,
            file_secret_settings,
        )


# Singleton instance with caching to ensure configuration is loaded only once
@lru_cache(maxsize=1)
def get_config() -> DataSourceConfig:
    """
    Get the singleton configuration instance.

    Returns:
        DataSourceConfig instance with loaded configuration
    """
    try:
        config = DataSourceConfig()
        logger.sync_info(
            "Configuration loaded successfully",
            datasources=len(config.datasources),
            keywords=len(config.keywords),
            annotations=len(config.annotations),
            api_defaults=len(config.api_defaults),
        )
        return config
    except Exception as e:
        logger.sync_error("Failed to load configuration", error=str(e))
        # Return default configuration to maintain backward compatibility
        return DataSourceConfig()


# Apply keyword configuration to data sources
def _apply_keywords_to_sources():
    """Apply shared keyword configuration to relevant data sources."""
    config = get_config()
    kidney_keywords = config.keywords.get("kidney", [])

    # Apply keywords to sources that need them
    for source_name in ["PanelApp", "GenCC"]:
        if source_name in config.datasources:
            config.datasources[source_name]["kidney_keywords"] = kidney_keywords


# Initialize configuration and apply keywords
_config = get_config()
_apply_keywords_to_sources()

# =============================================================================
# BACKWARD COMPATIBILITY EXPORTS - MAINTAIN EXACT SAME API
# =============================================================================

# Main configuration dictionaries - same structure as before
DATA_SOURCE_CONFIG: dict[str, dict[str, Any]] = _config.datasources

# Internal process configurations - kept hardcoded as they're internal only
INTERNAL_PROCESS_CONFIG: dict[str, dict[str, Any]] = {
    "annotation_pipeline": {
        "display_name": "Gene Annotation Pipeline",
        "description": "Post-processing pipeline that adds ClinVar annotations and computed scores",
        "category": "internal_process",
        "icon": "mdi-cog",
    },
    "Evidence_Aggregation": {
        "display_name": "Evidence Aggregation",
        "description": "Combines and scores evidence from all data sources",
        "category": "internal_process",
        "icon": "mdi-chart-timeline-variant",
    },
    "HGNC_Normalization": {
        "display_name": "HGNC Normalization",
        "description": "Normalizes gene symbols using HGNC database",
        "category": "internal_process",
        "icon": "mdi-format-align-center",
    },
}

# Annotation source configurations
ANNOTATION_SOURCE_CONFIG: dict[str, dict[str, Any]] = _config.annotations

# Common annotation configuration
ANNOTATION_COMMON_CONFIG = _config.annotations.get("common", {})

# API default configurations
API_DEFAULTS_CONFIG: dict[str, Any] = _config.api_defaults

# List of sources that support automatic updates
AUTO_UPDATE_SOURCES = [
    source for source, config in DATA_SOURCE_CONFIG.items() if config.get("auto_update", False)
]

# List of sources in priority order
PRIORITY_ORDERED_SOURCES = sorted(
    DATA_SOURCE_CONFIG.keys(), key=lambda x: DATA_SOURCE_CONFIG[x].get("priority", 999)
)

# =============================================================================
# HELPER FUNCTIONS - ALL REMAIN UNCHANGED FOR BACKWARD COMPATIBILITY
# =============================================================================


def get_source_config(source_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific data source"""
    return DATA_SOURCE_CONFIG.get(source_name)


def get_all_source_names() -> list[str]:
    """Get list of all configured data source names"""
    return list(DATA_SOURCE_CONFIG.keys())


def get_auto_update_sources() -> list[str]:
    """Get list of sources that support automatic updates"""
    return AUTO_UPDATE_SOURCES.copy()


def is_source_configured(source_name: str) -> bool:
    """Check if a data source is configured"""
    return source_name in DATA_SOURCE_CONFIG


def get_source_parameter(source_name: str, param_name: str, default: Any = None) -> Any:
    """
    Get a specific parameter for a data source.

    Args:
        source_name: Name of the data source
        param_name: Name of the parameter
        default: Default value if parameter not found

    Returns:
        Parameter value or default
    """
    config = get_source_config(source_name)
    if config:
        # Handle nested parameters with dot notation
        if "." in param_name:
            keys = param_name.split(".")
            value = config
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, {})
                else:
                    return default
            return value if value != {} else default
        else:
            # Direct parameter access
            return config.get(param_name, default)
    return default


def get_internal_process_config(process_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific internal process"""
    return INTERNAL_PROCESS_CONFIG.get(process_name)


def get_source_cache_ttl(source_name: str) -> int:
    """
    Get cache TTL for a data source.

    Args:
        source_name: Name of the data source

    Returns:
        Cache TTL in seconds, defaults to 3600 (1 hour)
    """
    return get_source_parameter(source_name, "cache_ttl", 3600)


def get_source_api_url(source_name: str) -> str | None:
    """
    Get API URL for a data source.

    Args:
        source_name: Name of the data source

    Returns:
        API URL or None
    """
    return get_source_parameter(source_name, "api_url")


def get_annotation_config(source_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific annotation source"""
    return ANNOTATION_SOURCE_CONFIG.get(source_name)
