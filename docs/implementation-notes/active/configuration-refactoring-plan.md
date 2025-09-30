# Configuration Refactoring Implementation Plan

**Status**: ✅ COMPLETED (2025-09-26)
**Implementation**: Successful
**Tests**: All passing (36/36)

## Issue Overview
**GitHub Issue:** [#17](https://github.com/berntpopp/kidney-genetics-db/issues/17) - Extract hardcoded configuration to external config files
**Objective:** Enable environment-specific deployments without code changes

## Executive Summary
This plan addresses the refactoring of hardcoded configuration values in `datasource_config.py` following SOLID, DRY, and KISS principles. The solution leverages pydantic-settings 2.0+ with custom YAML sources for type-safe, validated configuration management.

## Current State Analysis

### 1. Configuration Architecture
- **Primary Config:** `backend/app/core/config.py` - Uses pydantic_settings for environment variables
- **Datasource Config:** `backend/app/core/datasource_config.py` - Contains 495 lines of hardcoded configuration
- **Pattern:** Already supports environment variables via `.env` file using pydantic_settings
- **Scrapers:** Use YAML configuration files (`scrapers/*/config/config.yaml`)

### 2. Hardcoded Configuration Categories
Analysis of `datasource_config.py` reveals the following configuration types:

#### A. API Endpoints and URLs
- PanelApp UK/AU API URLs
- PubTator API endpoints
- ClinGen API URLs
- GenCC API endpoints
- HPO API URLs
- HGNC endpoints

#### B. Domain-Specific Keywords
- Kidney-related keywords (18+ terms) repeated across multiple sources
- Panel IDs for various sources
- Affiliate/expert panel IDs for ClinGen

#### C. Processing Parameters
- Rate limits (requests_per_second)
- Batch sizes
- Cache TTL values
- Retry configurations
- Timeout settings
- Min/max thresholds

#### D. Feature Toggles
- `auto_update` flags
- `min_publications_enabled`
- `use_cache` flags

#### E. Classification/Scoring Weights
- GenCC classification weights
- ClinVar review confidence levels
- Evidence scoring parameters

## Proposed Solution Architecture

### Design Principles
- **SOLID**: Single responsibility per config module, extensible via custom sources
- **DRY**: Centralized configuration loading, no duplicate keyword definitions
- **KISS**: Leverage pydantic-settings native capabilities, minimal custom code
- **Zero Regressions**: Maintain backward compatibility, preserve all existing APIs

### Three-Tier Configuration System

```
┌─────────────────────────────────────────────────┐
│         Environment Variables (.env)            │  ← Secrets, URLs, deployment-specific
├─────────────────────────────────────────────────┤
│         YAML Configuration Files                │  ← Static config, domain keywords, weights
├─────────────────────────────────────────────────┤
│         Pydantic Models (validated)             │  ← Type-safe, validated defaults
└─────────────────────────────────────────────────┘
```

### File Structure

```
backend/
├── config/
│   ├── datasources.yaml        # Main datasource configuration
│   ├── datasources.dev.yaml    # Development overrides
│   ├── datasources.prod.yaml   # Production overrides
│   ├── annotations.yaml        # Annotation source config
│   ├── keywords.yaml           # Domain keywords (kidney terms)
│   └── schema/
│       └── config.schema.json  # JSON schema for validation
├── app/
│   └── core/
│       ├── config.py           # Existing pydantic settings (enhanced)
│       ├── config_loader.py    # New: YAML loader with validation
│       └── datasource_config.py # Refactored: Thin wrapper
```

## Implementation Phases

### Phase 1: Infrastructure Setup

#### Dependencies and Schema
- [ ] Add PyYAML and jsonschema to dependencies
- [ ] Create JSON schema for configuration validation
- [ ] Implement ConfigLoader class with:
  - YAML file loading
  - Schema validation
  - Environment override support
  - Merge logic for multiple files

#### Configuration Loader Implementation

Using pydantic-settings 2.0+ custom sources pattern:
```python
# backend/app/core/yaml_config_source.py
from pathlib import Path
from typing import Any, Dict
import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
)

class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Custom source for YAML configuration following pydantic-settings patterns"""

    def __init__(self, settings_cls: type[BaseSettings], yaml_file: Path):
        super().__init__(settings_cls)
        self.yaml_file = yaml_file
        self._data = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load and cache YAML configuration"""
        if self.yaml_file.exists():
            with open(self.yaml_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        """Get field value from YAML data"""
        field_value = self._data.get(field_name)
        return field_value, field_name, False

    def __call__(self) -> Dict[str, Any]:
        """Return all configuration values"""
        return self._data.copy()
```

### Phase 2: Extract Datasource Configuration

#### Create YAML Configuration Files

**datasources.yaml:**
```yaml
# Data source configurations
datasources:
  PanelApp:
    display_name: PanelApp
    description: Expert-curated gene panels from UK Genomics England and Australian Genomics
    documentation_url: https://panelapp.genomicsengland.co.uk/api/docs/

    settings:
      auto_update: true
      priority: 1
      cache_ttl: 21600  # 6 hours

    panels:
      uk_ids: [384, 539]
      au_ids: [217, 363]

    filters:
      confidence_levels: [green, amber]
      min_evidence_level: 3

    # API URLs moved to environment variables for flexibility
    # UK_API_URL and AU_API_URL in .env

  PubTator:
    display_name: PubTator3
    description: Automated literature mining for kidney disease genes

    settings:
      auto_update: true
      priority: 2
      requests_per_second: 3.0  # CRITICAL: Official limit
      cache_ttl: 604800  # 7 days

    search:
      query: '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'
      batch_size: 100
      chunk_size: 300

    update_modes:
      smart:
        max_pages: 500
        duplicate_threshold: 0.9
        consecutive_pages: 3
      full:
        max_pages: null  # unlimited
```

**keywords.yaml:**
```yaml
# Domain-specific keywords configuration
keywords:
  kidney:
    # Core kidney terms
    core:
      - kidney
      - renal
      - nephro

    # Specific conditions
    conditions:
      - glomerul
      - tubulopathy
      - tubulointerstitial
      - polycystic
      - alport
      - nephritis
      - cystic kidney
      - ciliopathy
      - complement
      - cakut

    # Clinical manifestations
    clinical:
      - proteinuria
      - hematuria
      - nephrotic
      - focal segmental
      - steroid resistant

    # Terms to exclude (false positives)
    exclude:
      - tubul  # Too broad, matches brain disorders
```

#### Update Environment Variables

**.env.example:**
```bash
# API URLs (deployment-specific)
PANELAPP_UK_URL=https://panelapp.genomicsengland.co.uk/api/v1
PANELAPP_AU_URL=https://panelapp-aus.org/api/v1
HPO_API_URL=https://ontology.jax.org/api
PUBTATOR_API_URL=https://www.ncbi.nlm.nih.gov/research/pubtator-api
CLINGEN_API_URL=https://search.clinicalgenome.org/api
GENCC_API_URL=https://search.thegencc.org/api/submissions

# Feature flags
ENABLE_AUTO_UPDATE=true
ENABLE_CACHING=true

# Environment
ENVIRONMENT=dev  # dev, staging, prod
CONFIG_DIR=./config
```

### Phase 3: Refactor datasource_config.py

#### Pydantic Models for Type Safety
```python
# backend/app/core/datasource_models.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class DataSourceSettings(BaseModel):
    """Base model for data source settings with validation"""
    auto_update: bool = True
    priority: int = Field(ge=1, le=100)
    cache_ttl: int = Field(ge=0)
    requests_per_second: Optional[float] = Field(None, ge=0.1, le=100.0)

class PanelAppConfig(BaseModel):
    """PanelApp specific configuration with validation"""
    display_name: str
    description: str
    settings: DataSourceSettings
    uk_api_url: Optional[str] = None  # From env var
    au_api_url: Optional[str] = None  # From env var
    uk_panels: List[int]
    au_panels: List[int]
    confidence_levels: List[str]
    min_evidence_level: int = Field(ge=1, le=5)

# backend/app/core/datasource_config.py (refactored)
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.yaml_config_source import YamlConfigSettingsSource

class DataSourceConfig(BaseSettings):
    """Main configuration class using pydantic-settings"""
    model_config = SettingsConfigDict(
        env_prefix="KG_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Configuration will be loaded from YAML and validated
    datasources: Dict[str, Any]
    keywords: Dict[str, List[str]]
    annotations: Dict[str, Any]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Define source priority: env vars override YAML"""
        yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=Path("config/datasources.yaml")
        )
        return (
            init_settings,
            yaml_source,  # YAML as base
            env_settings,  # Env vars override
            dotenv_settings,
            file_secret_settings,
        )

# Singleton instance with caching
@lru_cache(maxsize=1)
def get_config() -> DataSourceConfig:
    return DataSourceConfig()

# Maintain backward compatibility - exact same API
DATA_SOURCE_CONFIG = get_config().datasources
ANNOTATION_SOURCE_CONFIG = get_config().annotations

# All existing functions remain unchanged
def get_source_config(source_name: str) -> Dict[str, Any] | None:
    return DATA_SOURCE_CONFIG.get(source_name)
```

### Phase 4: Validation and Migration

#### Pydantic Schema Validation (Built-in)
```python
# Validation is automatic with pydantic models
# Example validation error handling:
try:
    config = DataSourceConfig()
except ValidationError as e:
    logger.error("Configuration validation failed", errors=e.errors())
    raise
```

#### One-Time Migration Script
```python
# scripts/migrate_config.py
"""One-time script to migrate from hardcoded to YAML configuration"""

def migrate_datasource_config():
    """Extract configuration from datasource_config.py to YAML files"""
    from app.core.datasource_config import DATA_SOURCE_CONFIG

    # Separate concerns
    datasources = {}
    keywords = set()

    for source, config in DATA_SOURCE_CONFIG.items():
        # Extract keywords
        if "kidney_keywords" in config:
            keywords.update(config["kidney_keywords"])

        # Build datasource config
        datasources[source] = {
            "display_name": config.get("display_name"),
            "description": config.get("description"),
            "settings": extract_settings(config),
            # ... more extraction logic
        }

    # Save to YAML files
    save_yaml("config/datasources.yaml", {"datasources": datasources})
    save_yaml("config/keywords.yaml", {"keywords": {"kidney": list(keywords)}})
```

### Phase 5: Testing and Documentation

#### Test Coverage
- [ ] Unit tests for ConfigLoader class
- [ ] Schema validation tests
- [ ] Environment override tests
- [ ] Backward compatibility tests
- [ ] Integration tests with existing code

#### Documentation Updates
- [ ] Configuration management guide
- [ ] Environment setup documentation
- [ ] Migration guide for deployments
- [ ] Schema documentation

## Key Benefits

- **Environment Flexibility**: Deploy to dev/staging/prod without code changes
- **Type Safety**: Pydantic validation prevents configuration errors at startup
- **DRY Principle**: Single source of truth for keywords and configurations
- **Zero Regressions**: Complete backward compatibility with existing code
- **Security**: Secrets stay in environment variables, not in version control

## Critical Requirements

### Non-Negotiable
- **Zero Breaking Changes**: All existing code must work unchanged
- **Performance**: Configuration loaded once at startup, cached thereafter
- **Validation**: Fail fast at startup if configuration is invalid
- **Security**: Never commit secrets to YAML files

## Success Criteria

- [ ] All 495 lines of hardcoded config extracted to YAML/env vars
- [ ] Pydantic models validate all configuration at startup
- [ ] Zero changes required in consumer code (31 files)
- [ ] All existing helper functions work identically
- [ ] Performance unchanged (config cached after first load)
- [ ] Comprehensive test suite prevents regressions


## Regression Prevention

### Backward Compatibility Guarantees
1. **API Preservation**: All existing functions maintain exact signatures
2. **Data Structure**: `DATA_SOURCE_CONFIG` dict structure unchanged
3. **Import Paths**: No changes to import statements in consumer code
4. **Default Values**: All existing defaults preserved
5. **Performance**: Config loaded once and cached (via `@lru_cache`)

### Testing Strategy
```python
# Regression test example
def test_backward_compatibility():
    """Ensure all existing APIs work unchanged"""
    from app.core.datasource_config import (
        DATA_SOURCE_CONFIG,
        get_source_config,
        get_source_parameter,
        get_auto_update_sources,
    )

    # Test existing API
    assert "PanelApp" in DATA_SOURCE_CONFIG
    assert get_source_config("PanelApp") is not None
    assert get_source_parameter("PanelApp", "priority") == 1
    assert "PanelApp" in get_auto_update_sources()
```

## Implementation Details

See `configuration-refactoring-todo.md` for:
- Detailed implementation checklist with all phases
- Specific files to create/modify with exact line numbers
- Code examples for each change
- Complete YAML configuration templates
- Regression test suite
- Validation checklist

The TODO document provides line-by-line guidance for extracting all 495 lines of hardcoded configuration while maintaining 100% backward compatibility.

## Technical Notes

### Configuration Loading Order
1. YAML files provide base configuration
2. Environment variables override specific values
3. Pydantic validates final merged configuration
4. Configuration cached for lifetime of application

### File Organization
```
backend/
├── config/                    # New directory
│   ├── datasources.yaml      # Main source configurations
│   ├── keywords.yaml         # Shared keyword lists
│   └── annotations.yaml      # Annotation settings
├── app/core/
│   ├── datasource_config.py  # Refactored thin wrapper
│   ├── datasource_models.py  # New pydantic models
│   └── yaml_config_source.py # New YAML source loader
```


## Architecture Compliance

### SOLID Principles
- **Single Responsibility**: Each config module handles one domain (datasources, keywords, annotations)
- **Open/Closed**: New config sources can be added without modifying existing code
- **Liskov Substitution**: All config sources implement `PydanticBaseSettingsSource` interface
- **Interface Segregation**: Small, focused configuration interfaces per domain
- **Dependency Inversion**: Code depends on config abstractions, not concrete YAML files

### DRY (Don't Repeat Yourself)
- Kidney keywords defined once in `keywords.yaml`, used by multiple sources
- Base configuration patterns inherited via pydantic models
- Configuration loading logic centralized in one place

### KISS (Keep It Simple, Stupid)
- Leverages pydantic-settings native capabilities instead of custom solutions
- Simple YAML format familiar to all developers
- Minimal code changes - only refactor the config module itself

### Modularization
- Clear separation: datasources / keywords / annotations
- Each config domain can evolve independently
- Environment-specific overrides without affecting base configuration

## Conclusion

This refactoring extracts 495 lines of hardcoded configuration while maintaining 100% backward compatibility. By leveraging pydantic-settings 2.0+ with custom YAML sources, we achieve type-safe, validated configuration that follows SOLID principles and enables zero-downtime deployments across environments. The solution requires minimal custom code, reuses existing patterns from the codebase (UnifiedLogger, CacheService), and guarantees no regressions through comprehensive testing.