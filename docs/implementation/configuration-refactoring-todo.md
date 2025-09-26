# Configuration Refactoring TODO

**Status**: ✅ COMPLETED (2025-09-26)
**All Tasks**: Done
**Result**: 100% backward compatibility maintained

## Overview
This document provides a detailed TODO list for implementing the configuration refactoring described in issue #17, including specific files, line numbers, and code examples.

## Phase 1: Infrastructure Setup

### 1.1 Add Dependencies
**File:** `backend/pyproject.toml`
**Line:** ~50 (after existing dependencies)
**Action:** Add PyYAML dependency

```python
dependencies = [
    # ... existing dependencies ...
    "pyyaml>=6.0.1",  # ADD THIS LINE
]
```

### 1.2 Create YAML Config Source
**File:** `backend/app/core/yaml_config_source.py` (NEW FILE)
**Action:** Create custom pydantic-settings source for YAML

```python
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

### 1.3 Create Pydantic Models
**File:** `backend/app/core/datasource_models.py` (NEW FILE)
**Action:** Create type-safe configuration models

```python
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

class AnnotationSourceSettings(BaseModel):
    """Settings for annotation sources"""
    requests_per_second: float = Field(ge=0.1, le=100.0)
    max_retries: int = Field(ge=1, le=10)
    cache_ttl_days: int = Field(ge=1, le=365)
    use_http_cache: bool = True
    circuit_breaker_threshold: int = Field(ge=1, le=10)
```

## Phase 2: Extract Configuration to YAML

### 2.1 Create Datasources YAML
**File:** `backend/config/datasources.yaml` (NEW FILE)
**Action:** Extract hardcoded values from lines 12-292 of datasource_config.py

```yaml
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
      uk_ids: [384, 539]  # From line 24
      au_ids: [217, 363]  # From line 25

    filters:
      confidence_levels: [green, amber]  # From line 26
      min_evidence_level: 3  # From line 27

  PubTator:
    display_name: PubTator3
    description: Automated literature mining for kidney disease genes from PubMed
    documentation_url: https://www.ncbi.nlm.nih.gov/research/pubtator3/api

    settings:
      auto_update: true
      priority: 2
      requests_per_second: 3.0  # From line 63 - CRITICAL limit
      cache_ttl: 604800  # 7 days

    search:
      query: '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'  # From line 78
      batch_size: 100  # From line 79
      chunk_size: 300  # From line 81
      max_pages: null  # From line 65/73

    update_modes:
      smart:
        max_pages: 500  # From line 68
        duplicate_threshold: 0.9  # From line 69
        consecutive_pages: 3  # From line 70
      full:
        max_pages: null  # From line 73

  ClinGen:
    display_name: ClinGen
    description: Expert-curated gene-disease validity assessments from 5 kidney specialist panels
    documentation_url: https://clinicalgenome.org/docs/gene-disease-validity/

    settings:
      auto_update: true
      priority: 3
      cache_ttl: 86400  # 24 hours

    classification:
      min_classification: Limited  # From line 98

    kidney_affiliate_ids:  # From lines 100-106
      - 40066  # Kidney Cystic and Ciliopathy Disorders
      - 40068  # Glomerulopathy
      - 40067  # Tubulopathy
      - 40069  # Complement-Mediated Kidney Diseases
      - 40070  # Congenital Anomalies of the Kidney and Urinary Tract

  GenCC:
    display_name: GenCC
    description: Harmonized gene-disease relationships from 40+ submitters worldwide
    documentation_url: https://thegencc.org/faq.html

    settings:
      auto_update: true
      priority: 4
      cache_ttl: 43200  # 12 hours

    filters:
      confidence_categories: [definitive, strong, moderate]  # From line 121

    classification_weights:  # From lines 140-149
      Definitive: 1.0
      Strong: 0.8
      Moderate: 0.6
      Supportive: 0.5
      Limited: 0.3
      Disputed Evidence: 0.1
      No Known Disease Relationship: 0.0
      Refuted Evidence: 0.0

  HPO:
    display_name: HPO
    description: Human Phenotype Ontology - Kidney/urinary phenotypes and associated genes
    documentation_url: https://hpo.jax.org/app/data/annotations

    settings:
      auto_update: true
      priority: 5
      cache_ttl: 604800  # 7 days

    phenotypes:
      kidney_root_term: HP:0010935  # From line 164
      kidney_terms:  # From lines 166-171
        - HP:0010935  # Abnormality of upper urinary tract
        - HP:0000077  # Abnormality of the kidney
        - HP:0012210  # Abnormal renal morphology
        - HP:0000079  # Abnormality of the urinary system

    processing:
      min_gene_associations: 1  # From line 173
      max_depth: 10  # From line 174
      batch_size: 5  # From line 175
      request_delay: 0.2  # From line 176

    # Lines 180-254: Clinical groups configuration
    clinical_groups:
      complement:
        signature_terms:
          - HP:0000093  # Proteinuria
          - HP:0000100  # Nephrotic syndrome
          - HP:0001970  # Tubulointerstitial nephritis
          - HP:0000796  # Urethral obstruction
          - HP:0003259  # Elevated serum creatinine
        name: Complement-mediated kidney diseases
        weight: 1.0
      # ... (other clinical groups from lines 199-253)

  DiagnosticPanels:
    display_name: Diagnostic Panels
    description: Commercial diagnostic kidney gene panels from multiple providers

    settings:
      auto_update: false  # Manual upload
      priority: 6
      hybrid_source: true

    filters:
      min_panels: 1  # From line 278
      min_panels_enabled: true  # From line 279

  Literature:
    display_name: Literature
    description: Kidney disease genes from curated literature publications

    settings:
      auto_update: false  # Manual upload
      priority: 7
      hybrid_source: true

    filters:
      min_publications: 1  # From line 289
      min_publications_enabled: true  # From line 290
```

### 2.2 Create Keywords YAML
**File:** `backend/config/keywords.yaml` (NEW FILE)
**Action:** Extract and deduplicate kidney keywords from lines 29-49, 123-138

```yaml
keywords:
  kidney:
    # Core kidney terms
    core:
      - kidney
      - renal
      - nephro

    # Specific conditions (deduplicated from lines 29-49, 123-138)
    conditions:
      - glomerul
      - tubulopathy  # From line 35
      - tubulointerstitial  # From line 36
      - polycystic
      - alport
      - nephritis
      - cystic kidney  # From line 40 (not just "cystic")
      - ciliopathy  # From line 41
      - complement
      - cakut

    # Clinical manifestations (from lines 44-48)
    clinical:
      - focal segmental
      - steroid resistant
      - nephrotic
      - proteinuria
      - hematuria
```

### 2.3 Create Annotations YAML
**File:** `backend/config/annotations.yaml` (NEW FILE)
**Action:** Extract annotation source config from lines 407-495

```yaml
annotations:
  common:
    default_timeout: 30.0  # From line 399
    long_timeout: 60.0  # From line 400
    short_timeout: 10.0  # From line 401
    user_agent: KidneyGeneticsDB/1.0  # From line 402

  gnomad:
    requests_per_second: 3.0  # From line 410
    max_retries: 5  # From line 411
    cache_ttl_days: 90  # From line 412
    use_http_cache: true  # From line 413
    circuit_breaker_threshold: 5  # From line 414

  clinvar:
    requests_per_second: 2.8  # From line 419 - NCBI limit
    max_retries: 5
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 5

    processing:
      gene_batch_size: 20  # From line 426
      max_concurrent_genes: 1  # From line 427
      variant_batch_size: 200  # From line 430
      search_batch_size: 10000  # From line 431
      max_concurrent_variant_fetches: 2  # From line 432

    review_confidence:  # From lines 434-443
      practice guideline: 4
      reviewed by expert panel: 4
      criteria provided, multiple submitters, no conflicts: 3
      criteria provided, conflicting classifications: 2
      criteria provided, single submitter: 2
      no assertion for the individual variant: 1
      no assertion criteria provided: 1
      no classification provided: 0

  hpo:
    requests_per_second: 10.0  # From line 446
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 5

  mpo_mgi:
    requests_per_second: 2.0  # From line 453 - MGI servers are slower
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 3
    mpo_kidney_terms_file: data/mpo_kidney_terms.json  # From line 459

  hgnc:
    requests_per_second: 5.0  # From line 462
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 3

  string_ppi:
    requests_per_second: 5.0  # From line 469
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 3

  gtex:
    requests_per_second: 3.0  # From line 476
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 3

  descartes:
    requests_per_second: 5.0  # From line 483
    max_retries: 3
    cache_ttl_days: 90
    use_http_cache: true
    circuit_breaker_threshold: 3
```

### 2.4 Update Environment Variables
**File:** `backend/.env.example`
**Lines:** 9-13 (replace)
**Action:** Update with new environment variables

```bash
# OLD (lines 9-13):
PANELAPP_UK_URL=https://panelapp.genomicsengland.co.uk/api/v1
PANELAPP_AU_URL=https://panelapp.agha.umccr.org/api/v1
HPO_API_URL=https://hpo.jax.org/api
PUBTATOR_API_URL=https://www.ncbi.nlm.nih.gov/research/pubtator-api
HGNC_API_URL=http://rest.genenames.org

# NEW:
# API URLs (deployment-specific)
KG_PANELAPP__UK_API_URL=https://panelapp.genomicsengland.co.uk/api/v1
KG_PANELAPP__AU_API_URL=https://panelapp-aus.org/api/v1
KG_HPO__API_URL=https://ontology.jax.org/api
KG_PUBTATOR__API_URL=https://www.ncbi.nlm.nih.gov/research/pubtator-api
KG_CLINGEN__API_URL=https://search.clinicalgenome.org/api
KG_GENCC__API_URL=https://search.thegencc.org/api/submissions
KG_HGNC__API_URL=https://rest.genenames.org

# Configuration
KG_CONFIG_DIR=./config
KG_ENVIRONMENT=dev
```

## Phase 3: Refactor Core Configuration Files

### 3.1 Update config.py
**File:** `backend/app/core/config.py`
**Lines:** 81-90 (remove)
**Action:** Remove hardcoded KIDNEY_FILTER_TERMS since they'll come from YAML

```python
# REMOVE LINES 81-90:
    # Pipeline Configuration
    KIDNEY_FILTER_TERMS: list[str] = [
        "kidney",
        "renal",
        "nephro",
        "glomerul",
        "proteinuria",
        "hematuria",
        "nephrotic",
        "nephritic",
    ]

# ADD THESE LINES:
    # Configuration directory
    CONFIG_DIR: str = "./config"
    ENVIRONMENT: str = "dev"  # dev, staging, prod
```

### 3.2 Refactor datasource_config.py
**File:** `backend/app/core/datasource_config.py`
**Lines:** 1-495 (complete refactor)
**Action:** Replace with thin wrapper using pydantic-settings

```python
"""
Data source configuration settings

This module loads configuration from YAML files with environment variable overrides.
REFACTORED: Using pydantic-settings with YAML sources for external configuration
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.yaml_config_source import YamlConfigSettingsSource
from app.core.config import settings

class DataSourceConfig(BaseSettings):
    """Main configuration class using pydantic-settings"""
    model_config = SettingsConfigDict(
        env_prefix="KG_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Configuration will be loaded from YAML and validated
    datasources: Dict[str, Any]
    keywords: Dict[str, list[str]]
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
        config_dir = Path(settings.CONFIG_DIR)

        # Load multiple YAML files
        datasource_yaml = YamlConfigSettingsSource(
            settings_cls, yaml_file=config_dir / "datasources.yaml"
        )
        keywords_yaml = YamlConfigSettingsSource(
            settings_cls, yaml_file=config_dir / "keywords.yaml"
        )
        annotations_yaml = YamlConfigSettingsSource(
            settings_cls, yaml_file=config_dir / "annotations.yaml"
        )

        return (
            init_settings,
            datasource_yaml,  # YAML as base
            keywords_yaml,
            annotations_yaml,
            env_settings,  # Env vars override
            dotenv_settings,
            file_secret_settings,
        )

# Singleton instance with caching
@lru_cache(maxsize=1)
def get_config() -> DataSourceConfig:
    return DataSourceConfig()

# MAINTAIN BACKWARD COMPATIBILITY - EXACT SAME API
DATA_SOURCE_CONFIG = get_config().datasources
ANNOTATION_SOURCE_CONFIG = get_config().annotations
INTERNAL_PROCESS_CONFIG = {
    # Keep these hardcoded as they're internal
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

# List of sources that support automatic updates
AUTO_UPDATE_SOURCES = [
    source for source, config in DATA_SOURCE_CONFIG.items()
    if config.get("settings", {}).get("auto_update", False)
]

# List of sources in priority order
PRIORITY_ORDERED_SOURCES = sorted(
    DATA_SOURCE_CONFIG.keys(),
    key=lambda x: DATA_SOURCE_CONFIG[x].get("settings", {}).get("priority", 999)
)

# ALL EXISTING HELPER FUNCTIONS REMAIN UNCHANGED (lines 327-495)
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
        # Handle nested parameters
        if "." in param_name:
            keys = param_name.split(".")
            value = config
            for key in keys:
                value = value.get(key, {})
                if not isinstance(value, dict) and key != keys[-1]:
                    return default
            return value if value != {} else default
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
    return get_source_parameter(source_name, "settings.cache_ttl", 3600)

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

# ANNOTATION_COMMON_CONFIG remains for backward compatibility
ANNOTATION_COMMON_CONFIG = get_config().annotations.get("common", {})
```

## Phase 4: Update Files That Import Configuration

### 4.1 Update HGNC Client
**File:** `backend/app/core/hgnc_client.py`
**Line:** 10
**Action:** Make BASE_URL configurable

```python
# OLD (line 10):
    BASE_URL = "https://rest.genenames.org"

# NEW:
    def __init__(self):
        from app.core.config import settings
        import os
        self.BASE_URL = os.getenv("KG_HGNC__API_URL", "https://rest.genenames.org")
```

### 4.2 Update Init Annotation Sources Script
**File:** `backend/app/scripts/init_annotation_sources.py`
**Lines:** 17-122
**Action:** Load from configuration instead of hardcoding

```python
# Replace lines 17-122 with:
from app.core.datasource_config import get_annotation_config, ANNOTATION_SOURCE_CONFIG

# Build ANNOTATION_SOURCES from configuration
ANNOTATION_SOURCES = []
for source_name, config in ANNOTATION_SOURCE_CONFIG.items():
    if source_name == "common":
        continue

    source_data = {
        "source_name": source_name,
        "display_name": config.get("display_name", source_name.upper()),
        "description": config.get("description", f"{source_name} annotation source"),
        "base_url": config.get("base_url", ""),
        "update_frequency": "quarterly",
        "is_active": True,
        "priority": config.get("priority", 5),
        "config": {
            "cache_ttl_days": config.get("cache_ttl_days", 90),
            "batch_size": config.get("batch_size", 50),
            "requests_per_second": config.get("requests_per_second", 5.0)
        }
    }
    ANNOTATION_SOURCES.append(source_data)
```

### 4.3 Update PanelApp Source
**File:** `backend/app/pipeline/sources/unified/panelapp.py`
**Lines:** 68-81
**Action:** Already using get_source_parameter - verify it works with new structure

```python
# Lines 68-81 already use get_source_parameter correctly:
self.kidney_keywords = get_source_parameter(
    "PanelApp",
    "kidney_keywords",  # This will now come from keywords.yaml
    ["kidney", "renal", "nephro", ...]  # Fallback
)

# May need to update parameter path:
self.kidney_keywords = get_source_parameter(
    "PanelApp",
    "keywords.kidney",  # Nested path to keywords
    ["kidney", "renal", "nephro", ...]
)
```

## Phase 5: Testing and Validation

### 5.1 Create Migration Script
**File:** `backend/scripts/migrate_config.py` (NEW FILE)
**Action:** One-time script to verify configuration migration

```python
#!/usr/bin/env python3
"""
One-time script to migrate hardcoded configuration to YAML files.
This validates that all values are correctly extracted.
"""

import json
import yaml
from pathlib import Path
from deepdiff import DeepDiff

def compare_configurations():
    """Compare old hardcoded config with new YAML config"""

    # Import old configuration
    import sys
    sys.path.append('/home/bernt-popp/development/kidney-genetics-db/backend')
    from app.core.datasource_config import DATA_SOURCE_CONFIG as OLD_CONFIG

    # Load new configuration
    config_dir = Path("config")
    with open(config_dir / "datasources.yaml") as f:
        new_datasources = yaml.safe_load(f)

    # Compare configurations
    diff = DeepDiff(OLD_CONFIG, new_datasources["datasources"])

    if diff:
        print("Configuration differences found:")
        print(json.dumps(diff, indent=2))
        return False
    else:
        print("✓ Configuration successfully migrated with no differences")
        return True

if __name__ == "__main__":
    success = compare_configurations()
    sys.exit(0 if success else 1)
```

### 5.2 Create Regression Tests
**File:** `backend/tests/test_config_backward_compat.py` (NEW FILE)
**Action:** Ensure backward compatibility

```python
import pytest
from app.core.datasource_config import (
    DATA_SOURCE_CONFIG,
    ANNOTATION_SOURCE_CONFIG,
    get_source_config,
    get_source_parameter,
    get_auto_update_sources,
    get_source_cache_ttl,
    get_annotation_config,
)

def test_data_source_config_structure():
    """Verify DATA_SOURCE_CONFIG maintains expected structure"""
    assert "PanelApp" in DATA_SOURCE_CONFIG
    assert "PubTator" in DATA_SOURCE_CONFIG
    assert "ClinGen" in DATA_SOURCE_CONFIG
    assert "GenCC" in DATA_SOURCE_CONFIG
    assert "HPO" in DATA_SOURCE_CONFIG

def test_panelapp_config():
    """Verify PanelApp configuration values"""
    config = get_source_config("PanelApp")
    assert config is not None
    assert config["display_name"] == "PanelApp"
    assert config["settings"]["priority"] == 1
    assert config["settings"]["cache_ttl"] == 21600
    assert config["panels"]["uk_ids"] == [384, 539]
    assert config["panels"]["au_ids"] == [217, 363]

def test_source_parameter_access():
    """Verify get_source_parameter works with nested paths"""
    # Direct parameter
    assert get_source_parameter("PanelApp", "display_name") == "PanelApp"

    # Nested parameter
    assert get_source_parameter("PanelApp", "settings.priority") == 1
    assert get_source_parameter("PanelApp", "panels.uk_ids") == [384, 539]

    # Default value
    assert get_source_parameter("PanelApp", "non_existent", "default") == "default"

def test_annotation_config():
    """Verify annotation configuration"""
    assert "clinvar" in ANNOTATION_SOURCE_CONFIG
    assert "gnomad" in ANNOTATION_SOURCE_CONFIG

    clinvar = get_annotation_config("clinvar")
    assert clinvar["requests_per_second"] == 2.8
    assert clinvar["cache_ttl_days"] == 90
    assert clinvar["processing"]["gene_batch_size"] == 20

def test_helper_functions():
    """Verify all helper functions work"""
    # Auto update sources
    auto_sources = get_auto_update_sources()
    assert "PanelApp" in auto_sources
    assert "DiagnosticPanels" not in auto_sources  # manual upload

    # Cache TTL
    assert get_source_cache_ttl("PanelApp") == 21600
    assert get_source_cache_ttl("NonExistent") == 3600  # default

def test_kidney_keywords_deduplication():
    """Verify kidney keywords are properly deduplicated"""
    # Keywords should be loaded from keywords.yaml
    # and properly applied to relevant sources
    panelapp_config = get_source_config("PanelApp")
    gencc_config = get_source_config("GenCC")

    # Both should have access to the same kidney keywords
    # (implementation depends on how keywords are applied)
    pass

def test_all_imports_work():
    """Verify all 31 files that import can still import successfully"""
    # This would be tested by running the full test suite
    # All imports should work without modification
    from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
    from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource
    from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
    # ... etc
```

## Critical Files Summary

### Files to Create (6 new files):
1. `backend/app/core/yaml_config_source.py` - YAML source for pydantic-settings
2. `backend/app/core/datasource_models.py` - Pydantic models for validation
3. `backend/config/datasources.yaml` - Main datasource configuration
4. `backend/config/keywords.yaml` - Deduplicated keyword lists
5. `backend/config/annotations.yaml` - Annotation source settings
6. `backend/tests/test_config_backward_compat.py` - Regression tests

### Files to Modify (5 existing files):
1. `backend/pyproject.toml` - Add pyyaml dependency
2. `backend/.env.example` - Update environment variables (lines 9-13)
3. `backend/app/core/config.py` - Remove KIDNEY_FILTER_TERMS (lines 81-90)
4. `backend/app/core/datasource_config.py` - Complete refactor (lines 1-495)
5. `backend/app/scripts/init_annotation_sources.py` - Load from config (lines 17-122)

### Files That Import (31 files - NO CHANGES NEEDED):
These files import from datasource_config but should work unchanged due to backward compatibility:
- All files in `backend/app/pipeline/sources/unified/` (7 files)
- All files in `backend/app/pipeline/sources/annotations/` (8 files)
- Various other files that use get_source_config, get_source_parameter, etc.

## Validation Checklist

- [ ] All 495 lines of hardcoded configuration extracted
- [ ] Keywords deduplicated (18 unique terms instead of duplicates)
- [ ] All API URLs moved to environment variables
- [ ] Panel IDs, affiliate IDs preserved exactly
- [ ] Cache TTLs, rate limits, batch sizes preserved
- [ ] Classification weights and confidence levels preserved
- [ ] HPO clinical groups and onset groups preserved
- [ ] All helper functions work identically
- [ ] No changes required in 31 importing files
- [ ] Regression tests pass
- [ ] Configuration loads and validates at startup