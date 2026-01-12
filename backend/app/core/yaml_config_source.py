"""
YAML configuration source for pydantic-settings.

This module provides a custom settings source that loads configuration
from YAML files, following pydantic-settings 2.0+ patterns for type-safe
external configuration management.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from app.core.logging import get_logger

logger = get_logger(__name__)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    Custom source for YAML configuration following pydantic-settings patterns.

    This source enables loading configuration from YAML files with proper
    validation and type checking through pydantic models.

    Features:
    - Lazy loading of YAML files
    - Nested configuration support
    - Environment-specific overrides
    - Proper error handling with logging
    """

    def __init__(self, settings_cls: type[BaseSettings], yaml_file: Path):
        """
        Initialize YAML configuration source.

        Args:
            settings_cls: The settings class to populate
            yaml_file: Path to the YAML configuration file
        """
        super().__init__(settings_cls)
        self.yaml_file = yaml_file
        self._data: dict[str, Any] | None = None  # Lazy loading

    def _load_yaml(self) -> dict[str, Any]:
        """
        Load and cache YAML configuration.

        Returns:
            Dictionary of configuration values from YAML file
        """
        if self.yaml_file.exists():
            try:
                with open(self.yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    logger.sync_info(
                        "Loaded YAML configuration",
                        file=str(self.yaml_file),
                        keys=list(data.keys()),
                    )
                    return data
            except Exception as e:
                logger.sync_error(
                    "Failed to load YAML configuration", file=str(self.yaml_file), error=str(e)
                )
                return {}
        else:
            logger.sync_debug("YAML configuration file not found", file=str(self.yaml_file))
            return {}

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """
        Get field value from YAML data.

        Args:
            field: Field information from pydantic model
            field_name: Name of the field to retrieve

        Returns:
            Tuple of (field_value, field_name, is_complex)
        """
        if self._data is None:
            self._data = self._load_yaml()

        field_value = self._data.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        """
        Prepare field value for assignment to model.

        Args:
            field_name: Name of the field
            field: Field information
            value: Raw value from YAML
            value_is_complex: Whether value is complex type

        Returns:
            Prepared value ready for model assignment
        """
        return value

    def __call__(self) -> dict[str, Any]:
        """
        Return all configuration values.

        Returns:
            Dictionary of all configuration values from YAML
        """
        if self._data is None:
            self._data = self._load_yaml()
        return self._data.copy()


class MultiYamlConfigSource(PydanticBaseSettingsSource):
    """
    Settings source that merges multiple YAML files.

    This source enables loading configuration from multiple YAML files
    with proper merging strategy (later files override earlier ones).
    """

    def __init__(self, settings_cls: type[BaseSettings], yaml_files: list[Path]):
        """
        Initialize multi-YAML configuration source.

        Args:
            settings_cls: The settings class to populate
            yaml_files: List of YAML files to load (in priority order)
        """
        super().__init__(settings_cls)
        self.yaml_files = yaml_files
        self._data: dict[str, Any] | None = None

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Dictionary with override values

        Returns:
            Merged dictionary with overrides applied
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _load_all_yaml(self) -> dict[str, Any]:
        """
        Load and merge all YAML files.

        Returns:
            Merged configuration from all YAML files
        """
        merged_data: dict[str, Any] = {}

        for yaml_file in self.yaml_files:
            if yaml_file.exists():
                try:
                    with open(yaml_file, encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        merged_data = self._deep_merge(merged_data, data)
                        logger.sync_debug(
                            "Merged YAML configuration", file=str(yaml_file), keys=list(data.keys())
                        )
                except Exception as e:
                    logger.sync_error("Failed to load YAML file", file=str(yaml_file), error=str(e))

        return merged_data

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """
        Get field value from merged YAML data.

        Args:
            field: Field information from pydantic model
            field_name: Name of the field to retrieve

        Returns:
            Tuple of (field_value, field_name, is_complex)
        """
        if self._data is None:
            self._data = self._load_all_yaml()

        field_value = self._data.get(field_name)
        return field_value, field_name, False

    def __call__(self) -> dict[str, Any]:
        """
        Return all merged configuration values.

        Returns:
            Dictionary of all merged configuration values
        """
        if self._data is None:
            self._data = self._load_all_yaml()
        return self._data.copy()
