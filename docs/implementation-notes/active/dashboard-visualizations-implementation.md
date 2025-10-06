# Dashboard Visualizations - Implementation Plan v2 (REVISED)

**GitHub Issue**: #21
**Status**: 🔄 UPDATED - See D3.js Refactor Plan
**Priority**: High
**Estimated Effort**: 11-12 days (reduced from 12-13)
**Last Updated**: 2025-10-06 (D3.js refactor approach)
**Review**: Passed critical review + DRY config check

---

## 🔔 IMPORTANT UPDATE (2025-10-06)

**Frontend visualization approach has changed from vue-data-ui to D3.js**

Due to configuration issues with vue-data-ui (table components, legend removal, complex data formats), the frontend implementation is being refactored to use **pure D3.js** instead.

**📄 See new implementation plan**: [dashboard-d3js-refactor.md](./dashboard-d3js-refactor.md)

**Backend implementation** (Phases 0-1) remains unchanged and follows this plan.

---

## Executive Summary

Complete redesign of dashboard visualizations following DRY, SOLID principles and established codebase patterns. This revision addresses all critical issues from the initial review and ensures proper integration with existing systems.

**Key Principle**: ✅ **Use existing YAML config system** - No new constants.py or duplicate configuration!

**Approach**:
- ✅ Backend: Reuse existing endpoints, enhance where needed
- ✅ Backend: Follow all established patterns (ResponseBuilder, UnifiedLogger, gene_filters, async)
- ✅ Backend: Proper SOLID architecture with handler system
- ✅ Backend: Performance optimizations (indexes, thread pools)
- 🔄 Frontend: **Use D3.js for all visualizations** (see dashboard-d3js-refactor.md)

---

## Design Principles

Following [design-system.md](../../reference/design-system.md) and [CLAUDE.md](../../../CLAUDE.md):

1. **DRY** - Reuse gene_filters.py, ResponseBuilder, existing endpoints
2. **SOLID** - Handler pattern for extensibility
3. **KISS** - Simple patterns, no over-engineering
4. **Non-blocking** - ThreadPoolExecutor for sync DB operations
5. **Information Hierarchy** - Essential data first, tooltips for details

---

## Terminology Standards (CRITICAL)

### Source-Specific Classifications
**Labels**: "Definitive", "Strong", "Moderate", "Limited", "Disputed", "Refuted"
- **Source**: ClinGen, GenCC (direct from APIs)
- **Usage**: Source distribution charts
- **Example**: "ClinGen: 45 genes Definitive, 38 genes Strong"

### Aggregated Evidence Tiers
**Labels**: "Very High Confidence", "High Confidence", "Medium Confidence", "Low Confidence", "Very Low Confidence"
- **Source**: Computed from gene_scores view (all sources aggregated)
- **Usage**: Evidence composition/tiers visualization
- **Score Ranges**: 90-100, 70-90, 50-70, 30-50, 0-30

**Rule**: NEVER mix these two concepts!

---

## Phase 0: Foundation (2 days) - 14 hours

> **DRY Principle**: Use existing YAML config system, don't create new constants!
>
> See [`CONFIG-ANALYSIS.md`](./CONFIG-ANALYSIS.md) for full analysis of existing config.

### Task 0.1: Extend api_defaults.yaml (1h)

**File**: `backend/config/api_defaults.yaml`

```yaml
api_defaults:
  hide_zero_scores: true

  # Evidence tier configuration for aggregated scores (gene_scores view)
  evidence_tiers:
    ranges:
      - range: "90-100"
        label: "Very High Confidence"
        threshold: 90
        color: "#059669"
      - range: "70-90"
        label: "High Confidence"
        threshold: 70
        color: "#10B981"
      - range: "50-70"
        label: "Medium Confidence"
        threshold: 50
        color: "#34D399"
      - range: "30-50"
        label: "Low Confidence"
        threshold: 30
        color: "#FCD34D"
      - range: "0-30"
        label: "Very Low Confidence"
        threshold: 0
        color: "#F87171"

    # Filter thresholds for API tier filtering
    filter_thresholds:
      Very High: 90
      High: 70
      Medium: 50
      Low: 30

  # Source-specific classification order (ClinGen/GenCC)
  classification_order:
    Definitive: 1
    Strong: 2
    Moderate: 3
    Limited: 4
    Disputed: 5
    Refuted: 6
```

**Testing**:
```bash
# Verify config loads
cd backend && uv run python -c "from app.core.datasource_config import API_DEFAULTS_CONFIG; print(API_DEFAULTS_CONFIG.get('evidence_tiers'))"
```

---

### Task 0.1b: Complete datasources.yaml (30min)

**File**: `backend/config/datasources.yaml`

Add missing classification weights:
```yaml
GenCC:
  # ... existing config ...
  classification_weights:
    Definitive: 1.0
    Strong: 0.8
    Moderate: 0.6
    Limited: 0.3      # ADD
    Disputed: 0.1     # ADD
    Refuted: 0.0      # ADD
```

---

### Task 0.1c: Fix Existing DRY Violation (30min)

**File**: `backend/app/pipeline/sources/unified/clingen.py`

Replace hardcoded weights (lines 68-74):
```python
# BEFORE (hardcoded):
self.classification_weights = {
    "Definitive": 1.0,
    "Strong": 0.8,
    ...
}

# AFTER (from config):
from app.core.datasource_config import get_source_parameter

self.classification_weights = get_source_parameter(
    "GenCC",
    "classification_weights",
    {  # Fallback if config missing
        "Definitive": 1.0,
        "Strong": 0.8,
        "Moderate": 0.6,
        "Limited": 0.3,
        "Disputed": 0.1,
        "Refuted": 0.0,
    }
)
```

---

### Task 0.2: Extend Gene Filters (3h)

**File**: `backend/app/core/gene_filters.py`

```python
from app.core.datasource_config import API_DEFAULTS_CONFIG

def get_tier_filter_clause(min_tier: str | None = None) -> str:
    """
    Get WHERE clause for filtering genes by evidence tier.

    Args:
        min_tier: Minimum tier name (e.g., "Very High", "High", "Medium", "Low")

    Returns:
        SQL WHERE clause fragment
    """
    if min_tier:
        # Get thresholds from config
        tier_config = API_DEFAULTS_CONFIG.get("evidence_tiers", {})
        thresholds = tier_config.get("filter_thresholds", {})

        if min_tier in thresholds:
            threshold = thresholds[min_tier]
            return f"gs.percentage_score >= {threshold}"

    return "1=1"


def get_tier_filter_join_clause(
    min_tier: str | None = None
) -> tuple[str, str]:
    """
    Get JOIN and WHERE clauses for tier filtering.

    Combines score filter with tier filter for gene_evidence queries.

    Returns:
        Tuple of (join_clause, where_clause)
    """
    base_join, base_where = get_gene_evidence_filter_join()
    tier_clause = get_tier_filter_clause(min_tier)

    # Combine filters
    if base_where == "1=1" and tier_clause == "1=1":
        return ("", "1=1")
    elif base_where == "1=1":
        return (base_join, tier_clause)
    elif tier_clause == "1=1":
        return (base_join, base_where)
    else:
        return (base_join, f"{base_where} AND {tier_clause}")
```

**Testing**:
```python
def test_tier_filter_high():
    clause = get_tier_filter_clause("High")
    assert clause == "gs.percentage_score >= 70"

def test_tier_filter_none():
    clause = get_tier_filter_clause(None)
    assert clause == "1=1"
```

---

### Task 0.3: Create Handler System (4h)

**File**: `backend/app/crud/statistics_handlers.py`

```python
"""
Source-specific distribution handlers.
Follows Open/Closed Principle - add new sources without modifying existing code.
"""

from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class DistributionHandler(ABC):
    """Base handler for source distribution queries"""

    @abstractmethod
    def get_distribution(
        self,
        db: Session,
        join_clause: str,
        filter_clause: str
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        Get distribution data and metadata for a source.

        Returns:
            Tuple of (distribution_data, metadata_dict)
        """
        pass


class DiagnosticPanelsHandler(DistributionHandler):
    """Provider distribution for DiagnosticPanels"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating provider distribution", source="DiagnosticPanels")

        # Extract providers from JSONB panels array
        distribution_data = db.execute(
            text(f"""
                WITH provider_counts AS (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_elements(evidence_data->'panels')->>'provider' as provider
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'DiagnosticPanels'
                )
                SELECT
                    provider,
                    COUNT(DISTINCT gene_id) as gene_count
                FROM provider_counts
                WHERE provider IS NOT NULL
                GROUP BY provider
                ORDER BY gene_count DESC
            """)
        ).fetchall()

        total_providers = len(distribution_data)
        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_providers": total_providers,
            "total_genes": total_genes,
            "visualization_type": "provider_bar_chart",
        }

        logger.sync_info(
            "Provider distribution calculated",
            source="DiagnosticPanels",
            providers=total_providers,
            genes=total_genes
        )

        return distribution_data, metadata


class ClinGenHandler(DistributionHandler):
    """Classification distribution for ClinGen"""

    def get_distribution(self, db, join_clause, filter_clause):
        from app.core.constants import CLASSIFICATION_ORDER

        logger.sync_info("Calculating classification distribution", source="ClinGen")

        # ClinGen stores classifications as array of strings
        distribution_data = db.execute(
            text(f"""
                WITH classification_data AS (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_elements_text(evidence_data->'classifications') as classification
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'ClinGen'
                )
                SELECT
                    classification,
                    COUNT(DISTINCT gene_id) as gene_count
                FROM classification_data
                WHERE classification IS NOT NULL
                GROUP BY classification
                ORDER BY
                    CASE classification
                        WHEN 'Definitive' THEN 1
                        WHEN 'Strong' THEN 2
                        WHEN 'Moderate' THEN 3
                        WHEN 'Limited' THEN 4
                        WHEN 'Disputed' THEN 5
                        WHEN 'Refuted' THEN 6
                        ELSE 7
                    END
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_classifications": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "classification_donut",
        }

        logger.sync_info(
            "Classification distribution calculated",
            source="ClinGen",
            classifications=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class GenCCHandler(DistributionHandler):
    """Classification distribution for GenCC"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating classification distribution", source="GenCC")

        # GenCC stores single classification string
        distribution_data = db.execute(
            text(f"""
                SELECT
                    evidence_data->>'classification' as classification,
                    COUNT(DISTINCT gene_id) as gene_count
                FROM gene_evidence
                {join_clause}
                WHERE {filter_clause}
                    AND source_name = 'GenCC'
                    AND evidence_data->>'classification' IS NOT NULL
                GROUP BY classification
                ORDER BY gene_count DESC
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_classifications": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "classification_donut",
        }

        logger.sync_info(
            "Classification distribution calculated",
            source="GenCC",
            classifications=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class HPOHandler(DistributionHandler):
    """Phenotype count distribution for HPO"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating phenotype distribution", source="HPO")

        distribution_data = db.execute(
            text(f"""
                WITH phenotype_counts AS (
                    SELECT
                        gene_id,
                        jsonb_array_length(COALESCE(evidence_data->'phenotypes', '[]'::jsonb)) as phenotype_count
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'HPO'
                )
                SELECT
                    CASE
                        WHEN phenotype_count BETWEEN 1 AND 5 THEN '1-5'
                        WHEN phenotype_count BETWEEN 6 AND 10 THEN '6-10'
                        WHEN phenotype_count BETWEEN 11 AND 20 THEN '11-20'
                        WHEN phenotype_count BETWEEN 21 AND 50 THEN '21-50'
                        ELSE '50+'
                    END as phenotype_range,
                    COUNT(*) as gene_count
                FROM phenotype_counts
                GROUP BY phenotype_range
                ORDER BY MIN(phenotype_count)
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_ranges": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "phenotype_histogram",
        }

        logger.sync_info(
            "Phenotype distribution calculated",
            source="HPO",
            ranges=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class PanelAppHandler(DistributionHandler):
    """Panel count distribution for PanelApp (existing - keep as-is)"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating panel distribution", source="PanelApp")

        distribution_data = db.execute(
            text(f"""
                SELECT
                    panel_count,
                    COUNT(*) as gene_count
                FROM (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_length(COALESCE(gene_evidence.evidence_data->'panels', '[]'::jsonb)) as panel_count
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND gene_evidence.source_name = 'PanelApp'
                ) panel_counts
                GROUP BY panel_count
                ORDER BY panel_count
            """)
        ).fetchall()

        metadata = {
            "max_panels": max(row[0] for row in distribution_data) if distribution_data else 0,
            "visualization_type": "panel_histogram",
        }

        return distribution_data, metadata


class PubTatorHandler(DistributionHandler):
    """Publication count distribution for PubTator (existing - keep as-is)"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating publication distribution", source="PubTator")

        distribution_data = db.execute(
            text(f"""
                SELECT
                    pub_count,
                    COUNT(*) as gene_count
                FROM (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_length(COALESCE(gene_evidence.evidence_data->'pmids', '[]'::jsonb)) as pub_count
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND gene_evidence.source_name = 'PubTator'
                ) pub_counts
                GROUP BY pub_count
                ORDER BY pub_count
            """)
        ).fetchall()

        metadata = {
            "max_publications": max(row[0] for row in distribution_data) if distribution_data else 0,
            "visualization_type": "publication_histogram",
        }

        return distribution_data, metadata


class DefaultHandler(DistributionHandler):
    """Default handler for sources without specific logic"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_warning("Using default handler - no specific distribution logic")
        return [], {"note": "No distribution available"}


class SourceDistributionHandlerFactory:
    """Factory for getting appropriate handler"""

    _handlers = {
        "DiagnosticPanels": DiagnosticPanelsHandler(),
        "ClinGen": ClinGenHandler(),
        "GenCC": GenCCHandler(),
        "HPO": HPOHandler(),
        "PanelApp": PanelAppHandler(),
        "PubTator": PubTatorHandler(),
    }

    @classmethod
    def get_handler(cls, source_name: str) -> DistributionHandler:
        """Get handler for source"""
        return cls._handlers.get(source_name, DefaultHandler())
```

---

### Task 0.4: Add JSONB Indexes (2h)

**File**: `backend/alembic/versions/xxx_add_visualization_jsonb_indexes.py`

```python
"""Add JSONB indexes for dashboard visualizations

Revision ID: xxx
Revises: [previous]
Create Date: 2025-10-03
"""

from alembic import op

revision = 'xxx'
down_revision = '[previous]'
branch_labels = None
depends_on = None


def upgrade():
    # Index for DiagnosticPanels provider queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gene_evidence_diagnostic_providers
        ON gene_evidence
        USING gin ((evidence_data->'panels'))
        WHERE source_name = 'DiagnosticPanels'
    """)

    # Index for GenCC classification queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gene_evidence_gencc_classification
        ON gene_evidence ((evidence_data->>'classification'))
        WHERE source_name = 'GenCC'
    """)

    # Index for ClinGen classifications array
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gene_evidence_clingen_classifications
        ON gene_evidence
        USING gin ((evidence_data->'classifications'))
        WHERE source_name = 'ClinGen'
    """)

    # Index for HPO phenotypes array
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gene_evidence_hpo_phenotypes
        ON gene_evidence
        USING gin ((evidence_data->'phenotypes'))
        WHERE source_name = 'HPO'
    """)


def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_gene_evidence_diagnostic_providers")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_gene_evidence_gencc_classification")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_gene_evidence_clingen_classifications")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_gene_evidence_hpo_phenotypes")
```

**Run**:
```bash
alembic revision -m "add_visualization_jsonb_indexes"
# Edit file with content above
alembic upgrade head
```

---

### Task 0.5: Add Thread Pool to CRUDStatistics (2h)

**File**: `backend/app/crud/statistics.py`

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.gene_filters import (
    count_filtered_genes_from_evidence_sql,
    get_gene_evidence_filter_join,
    get_tier_filter_join_clause,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CRUDStatistics:
    """CRUD operations for statistics and data analysis"""

    def __init__(self):
        # Thread pool for non-blocking sync DB operations
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def get_source_overlaps_async(
        self,
        db: Session,
        selected_sources: list[str] | None = None
    ) -> dict[str, Any]:
        """Async wrapper for source overlaps (heavy query)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.get_source_overlaps,
            db,
            selected_sources
        )

    def get_source_overlaps(
        self, db: Session, selected_sources: list[str] | None = None
    ) -> dict[str, Any]:
        """Calculate gene intersections (sync - runs in thread pool)"""
        # ... existing implementation ...

    # ... rest of existing methods ...
```

---

### Task 0.6: Verify JSONB Schemas (2h)

**File**: `backend/tests/crud/test_jsonb_schemas.py`

```python
"""
Verify JSONB field structures before using in queries.
Prevents runtime errors from incorrect field paths.
"""

import pytest
from sqlalchemy import text

def test_diagnostic_panels_structure(db):
    """Verify DiagnosticPanels JSONB structure"""
    result = db.execute(text("""
        SELECT evidence_data->'panels'
        FROM gene_evidence
        WHERE source_name = 'DiagnosticPanels'
        LIMIT 1
    """)).scalar()

    assert result is not None
    panels = result
    assert isinstance(panels, list)
    if len(panels) > 0:
        assert 'provider' in panels[0]

def test_clingen_structure(db):
    """Verify ClinGen JSONB structure"""
    result = db.execute(text("""
        SELECT evidence_data->'classifications'
        FROM gene_evidence
        WHERE source_name = 'ClinGen'
        LIMIT 1
    """)).scalar()

    assert result is not None
    assert isinstance(result, list)  # Array of strings

def test_gencc_structure(db):
    """Verify GenCC JSONB structure"""
    result = db.execute(text("""
        SELECT evidence_data->>'classification'
        FROM gene_evidence
        WHERE source_name = 'GenCC'
        LIMIT 1
    """)).scalar()

    assert result is not None
    assert isinstance(result, str)

def test_hpo_structure(db):
    """Verify HPO JSONB structure"""
    result = db.execute(text("""
        SELECT evidence_data->'phenotypes'
        FROM gene_evidence
        WHERE source_name = 'HPO'
        LIMIT 1
    """)).scalar()

    assert result is not None
    assert isinstance(result, list)
```

**Run**: `cd backend && uv run pytest tests/crud/test_jsonb_schemas.py -v`

---

### Task 0.7: Unit Test Setup (3h)

**File**: `backend/tests/crud/test_statistics_handlers.py`

```python
"""Unit tests for source distribution handlers"""

import pytest
from app.crud.statistics_handlers import (
    DiagnosticPanelsHandler,
    ClinGenHandler,
    GenCCHandler,
    HPOHandler,
    SourceDistributionHandlerFactory,
)

def test_diagnostic_panels_handler(db):
    handler = DiagnosticPanelsHandler()
    distribution, metadata = handler.get_distribution(db, "", "1=1")

    assert isinstance(distribution, list)
    assert isinstance(metadata, dict)
    assert "total_providers" in metadata
    assert "visualization_type" in metadata

def test_clingen_handler(db):
    handler = ClinGenHandler()
    distribution, metadata = handler.get_distribution(db, "", "1=1")

    assert isinstance(distribution, list)
    assert "total_classifications" in metadata
    # Check ordering (Definitive first)
    if len(distribution) > 0:
        assert distribution[0][0] in ["Definitive", "Strong", "Moderate"]

def test_handler_factory():
    handler = SourceDistributionHandlerFactory.get_handler("DiagnosticPanels")
    assert isinstance(handler, DiagnosticPanelsHandler)

    handler = SourceDistributionHandlerFactory.get_handler("UnknownSource")
    from app.crud.statistics_handlers import DefaultHandler
    assert isinstance(handler, DefaultHandler)
```

---

## Phase 1: Core Implementation (Week 1) - 20 hours

### Task 1.1: Update get_source_distributions() (6h)

**File**: `backend/app/crud/statistics.py`

```python
from app.crud.statistics_handlers import SourceDistributionHandlerFactory

class CRUDStatistics:
    # ... __init__ with executor ...

    def get_source_distributions(
        self,
        db: Session,
        min_tier: str | None = None
    ) -> dict[str, Any]:
        """
        Calculate source-specific distributions using handler pattern.

        Args:
            db: Database session
            min_tier: Optional minimum evidence tier for filtering

        Returns:
            Dict with source-specific distribution data
        """
        try:
            logger.sync_info("Calculating source distributions", min_tier=min_tier)

            # Get filter clauses (respects score filter + tier filter)
            join_clause, filter_clause = get_tier_filter_join_clause(min_tier)

            # Get all sources with filtering
            sources_query = f"""
                SELECT DISTINCT gene_evidence.source_name
                FROM gene_evidence
                {join_clause}
                WHERE {filter_clause}
                ORDER BY gene_evidence.source_name
            """
            sources = db.execute(text(sources_query)).fetchall()

            source_distributions = {}

            for source_row in sources:
                source_name = source_row[0]

                # Get appropriate handler for source
                handler = SourceDistributionHandlerFactory.get_handler(source_name)

                # Get distribution data using handler
                distribution_data, metadata = handler.get_distribution(
                    db, join_clause, filter_clause
                )

                # Convert to response format
                distribution = [
                    {"category": row[0], "gene_count": row[1]}
                    for row in distribution_data
                ]

                source_distributions[source_name] = {
                    "distribution": distribution,
                    "metadata": metadata,
                }

            logger.sync_info(
                "Source distributions calculated",
                sources=len(source_distributions),
                min_tier=min_tier
            )

            return source_distributions

        except Exception as e:
            logger.sync_error(
                "Error calculating source distributions",
                error=e,
                min_tier=min_tier
            )
            raise
```

---

### Task 1.2: Enhance evidence-composition Endpoint (6h)

**File**: `backend/app/crud/statistics.py`

```python
def get_evidence_composition(
    self,
    db: Session,
    min_tier: str | None = None
) -> dict[str, Any]:
    """
    Analyze evidence quality and composition with optional tier filtering.

    Args:
        db: Database session
        min_tier: Optional minimum evidence tier

    Returns:
        Dictionary with evidence composition analysis including tier distribution
    """
    try:
        from app.core.datasource_config import API_DEFAULTS_CONFIG
        from app.core.gene_filters import get_tier_filter_clause

        logger.sync_info("Calculating evidence composition", min_tier=min_tier)

        # Get tier config from YAML
        tier_config = API_DEFAULTS_CONFIG.get("evidence_tiers", {})
        tier_ranges = tier_config.get("ranges", [])

        # Build CASE statement from config
        case_clauses = [
            f"WHEN percentage_score >= {tier['threshold']} THEN '{tier['range']}'"
            for tier in sorted(tier_ranges, key=lambda x: x['threshold'], reverse=True)
        ]

        # Build WHERE clause for tier filtering
        tier_where = ""
        if min_tier:
            tier_clause = get_tier_filter_clause(min_tier)
            if tier_clause != "1=1":
                tier_where = f"WHERE {tier_clause}"

        # Get evidence score distribution (with tier labels)
        score_distribution = db.execute(
            text(f"""
                SELECT
                    CASE
                        {' '.join(case_clauses)}
                    END as score_range,
                    COUNT(*) as gene_count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
                FROM gene_scores
                {tier_where}
                GROUP BY 1
                ORDER BY MIN(percentage_score) DESC
            """)
        ).fetchall()

        # Map ranges to labels from config
        tier_label_map = {
            tier['range']: tier['label']
            for tier in tier_ranges
        }

        # Map ranges to colors from config
        tier_color_map = {
            tier['range']: tier.get('color', '#6B7280')
            for tier in tier_ranges
        }

        evidence_tier_distribution = [
            {
                "score_range": row[0],
                "gene_count": row[1],
                "percentage": row[2],
                "tier_label": tier_label_map.get(row[0], "Unknown"),
                "color": tier_color_map.get(row[0], "#6B7280"),
            }
            for row in score_distribution
        ]

        # ... existing source stats and coverage code ...

        return {
            "evidence_tier_distribution": evidence_tier_distribution,
            "evidence_quality_distribution": evidence_tier_distribution,  # Backward compat
            "source_contribution_weights": source_contribution_weights,
            "source_coverage_distribution": source_coverage_distribution,
            "summary_statistics": {
                "total_genes": sum(
                    item["gene_count"] for item in evidence_tier_distribution
                ),
                "total_evidence_records": total_evidence,
                "active_sources": len(source_stats),
                "avg_sources_per_gene": round(..., 2),
            },
        }

    except Exception as e:
        logger.sync_error("Error analyzing evidence composition", error=e)
        raise
```

---

### Task 1.3: Update API Endpoints (4h)

**File**: `backend/app/api/endpoints/statistics.py`

```python
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import ValidationError
from app.core.responses import ResponseBuilder
from app.crud.statistics import statistics_crud
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/source-distributions")
async def get_source_distributions(
    min_tier: str | None = Query(
        None,
        description="Minimum evidence tier (Very High, High, Medium, Low)"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get source-specific distributions for visualization.

    Returns different metrics per source:
    - DiagnosticPanels: Provider distribution
    - ClinGen/GenCC: Classification distribution
    - HPO: Phenotype count distribution
    - PanelApp/PubTator: Count distributions
    """
    start_time = time.time()

    try:
        logger.sync_info("API: source-distributions", min_tier=min_tier)

        distribution_data = statistics_crud.get_source_distributions(db, min_tier=min_tier)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=distribution_data,
            meta={
                "description": "Source-specific distributions for dashboard visualizations",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "multi_source_distributions",
                "source_count": len(distribution_data),
                "min_tier": min_tier,
            },
        )

    except Exception as e:
        logger.sync_error("API: source-distributions failed", error=e, min_tier=min_tier)
        raise ValidationError(
            field="source_distributions",
            message=f"Failed to calculate source distributions: {str(e)}",
        ) from e


@router.get("/evidence-composition")
async def get_evidence_composition(
    min_tier: str | None = Query(
        None,
        description="Minimum evidence tier for filtering"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get evidence quality and composition analysis.

    Includes evidence tier distribution with proper labels.
    """
    start_time = time.time()

    try:
        logger.sync_info("API: evidence-composition", min_tier=min_tier)

        composition_data = statistics_crud.get_evidence_composition(db, min_tier=min_tier)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=composition_data,
            meta={
                "description": "Evidence quality and composition analysis with tier distribution",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "composition_and_tiers",
                "min_tier": min_tier,
            },
        )

    except Exception as e:
        logger.sync_error("API: evidence-composition failed", error=e, min_tier=min_tier)
        raise ValidationError(
            field="evidence_composition",
            message=f"Failed to analyze evidence composition: {str(e)}",
        ) from e
```

---

### Task 1.4: Update source-overlaps for Tier Filtering (4h)

**File**: `backend/app/crud/statistics.py` + `backend/app/api/endpoints/statistics.py`

```python
# In CRUDStatistics
def get_source_overlaps(
    self,
    db: Session,
    selected_sources: list[str] | None = None,
    min_tier: str | None = None,
) -> dict[str, Any]:
    """Calculate gene intersections with optional tier filtering"""
    try:
        # Build WHERE clause with tier filter
        join_clause, filter_clause = get_tier_filter_join_clause(min_tier)
        where_clauses = [filter_clause]
        params = {}

        if selected_sources:
            where_clauses.append("gene_evidence.source_name = ANY(:selected_sources)")
            params["selected_sources"] = selected_sources

        where_clause = "WHERE " + " AND ".join(where_clauses)

        # ... rest of existing logic with updated where_clause ...

# In API endpoint
@router.get("/source-overlaps")
async def get_source_overlaps(
    sources: list[str] | None = Query(None),
    min_tier: str | None = Query(None),
    db: Session = Depends(get_db),
):
    overlap_data = statistics_crud.get_source_overlaps(
        db,
        selected_sources=sources,
        min_tier=min_tier
    )
    # ... return with ResponseBuilder ...
```

---

## Phase 2: Frontend Updates (Week 2) - 24 hours

> **⚠️ NOTE**: This phase has been replaced with the D3.js refactor approach.
>
> **See**: [dashboard-d3js-refactor.md](./dashboard-d3js-refactor.md) for the updated frontend implementation using pure D3.js instead of vue-data-ui.
>
> The content below is kept for reference but will NOT be implemented.

---

<details>
<summary><strong>Original vue-data-ui Plan (NOT BEING IMPLEMENTED)</strong></summary>

### Task 2.1: Replace All Progress Bars (8h)

**Delete old files (alpha - OK to break)**:
- Any components using `v-progress-linear`

**Update**: `frontend/src/components/visualizations/SourceDistributionsChart.vue`

```vue
<template>
  <v-card>
    <v-card-title>{{ sourceData.metadata.source }} Distribution</v-card-title>

    <!-- DiagnosticPanels: Horizontal bar for providers -->
    <VueUiStackbar
      v-if="sourceData.metadata.visualization_type === 'provider_bar_chart'"
      :dataset="providerDataset"
      :config="stackbarConfig"
    />

    <!-- ClinGen/GenCC: Donut for classifications -->
    <VueUiDonut
      v-else-if="sourceData.metadata.visualization_type === 'classification_donut'"
      :dataset="classificationDataset"
      :config="donutConfig"
    />

    <!-- HPO/PanelApp/PubTator: Histogram -->
    <VueUiXy
      v-else
      :dataset="histogramDataset"
      :config="xyConfig"
    />
  </v-card>
</template>

<script setup>
import { VueUiDonut, VueUiStackbar, VueUiXy } from 'vue-data-ui'
import { useTheme } from 'vuetify'
import { computed } from 'vue'

const theme = useTheme()

const props = defineProps({
  sourceData: Object
})

// Dataset transformations based on visualization type
const providerDataset = computed(() => ({
  labels: props.sourceData.distribution.map(d => d.category),
  datasets: [{
    name: 'Genes',
    values: props.sourceData.distribution.map(d => d.gene_count)
  }]
}))

const classificationDataset = computed(() =>
  props.sourceData.distribution.map(d => ({
    name: d.category,
    value: d.gene_count
  }))
)

// Configs with theme integration
const donutConfig = computed(() => ({
  chart: {
    fontFamily: 'Roboto',
    backgroundColor: theme.current.value.colors.surface
  },
  userOptions: { show: true },
  style: {
    chart: {
      layout: {
        labels: {
          dataLabels: {
            show: true
          }
        }
      }
    }
  }
}))
</script>
```

---

### Task 2.2: Add Global Evidence Filter (6h)

**File**: `frontend/src/views/Dashboard.vue`

```vue
<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Data Visualization Dashboard</h1>
      </v-col>
    </v-row>

    <!-- Global Filter Row -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-select
          v-model="minEvidenceTier"
          :items="tierOptions"
          label="Minimum Evidence Tier"
          density="compact"
          variant="outlined"
          clearable
          hint="Filter all visualizations by evidence quality"
          persistent-hint
        />
      </v-col>
      <v-col cols="12" md="6" class="d-flex align-center">
        <v-chip size="small" class="mr-2">
          {{ filteredStats.total_genes }} total genes
        </v-chip>
        <v-chip v-if="minEvidenceTier" size="small" color="primary">
          {{ minEvidenceTier }}+ confidence
        </v-chip>
      </v-col>
    </v-row>

    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="primary">
      <v-tab value="overlaps">Gene Source Overlaps</v-tab>
      <v-tab value="distributions">Source Distributions</v-tab>
      <v-tab value="composition">Evidence Tiers</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="overlaps">
        <UpSetChart :min-tier="minEvidenceTier" />
      </v-window-item>

      <v-window-item value="distributions">
        <SourceDistributionsChart :min-tier="minEvidenceTier" />
      </v-window-item>

      <v-window-item value="composition">
        <EvidenceCompositionChart :min-tier="minEvidenceTier" />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const minEvidenceTier = ref(route.query.min_tier || null)
const activeTab = ref(route.query.tab || 'overlaps')

const tierOptions = [
  'Very High',
  'High',
  'Medium',
  'Low'
]

// Sync filter with URL
watch(minEvidenceTier, (value) => {
  router.push({
    query: { ...route.query, min_tier: value || undefined }
  })
})

// Sync tab with URL
watch(activeTab, (value) => {
  router.push({
    query: { ...route.query, tab: value }
  })
})
</script>
```

---

### Task 2.3: Update Evidence Composition Chart (6h)

**File**: `frontend/src/components/visualizations/EvidenceCompositionChart.vue`

```vue
<template>
  <v-card>
    <v-card-title>Evidence Tier Distribution</v-card-title>

    <v-row>
      <v-col cols="12" md="6">
        <VueUiDonut
          :dataset="tierDonutData"
          :config="donutConfig"
        />
      </v-col>

      <v-col cols="12" md="6">
        <v-table density="compact">
          <thead>
            <tr>
              <th>Tier</th>
              <th>Genes</th>
              <th>Percentage</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tier in tierDistribution" :key="tier.tier_label">
              <td>{{ tier.tier_label }}</td>
              <td>{{ tier.gene_count }}</td>
              <td>{{ tier.percentage }}%</td>
            </tr>
          </tbody>
        </v-table>
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup>
import { VueUiDonut } from 'vue-data-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { useTheme } from 'vuetify'
import api from '@/services/api'

const theme = useTheme()
const props = defineProps({
  minTier: String
})

const tierDistribution = ref([])

const tierDonutData = computed(() =>
  tierDistribution.value.map(tier => ({
    name: tier.tier_label,
    value: tier.gene_count,
    color: getTierColor(tier.score_range)
  }))
)

function getTierColor(range) {
  const colors = {
    '90-100': '#059669',
    '70-90': '#10B981',
    '50-70': '#34D399',
    '30-50': '#FCD34D',
    '0-30': '#F87171'
  }
  return colors[range] || '#6B7280'
}

async function fetchData() {
  const params = {}
  if (props.minTier) params.min_tier = props.minTier

  const response = await api.get('/statistics/evidence-composition', { params })
  tierDistribution.value = response.data.evidence_tier_distribution
}

onMounted(fetchData)
watch(() => props.minTier, fetchData)
</script>
```

---

### Task 2.4: Update UpSet Chart for Filtering (4h)

Pass `min_tier` prop to UpSetChart and update API call to include filter parameter.

</details>

---

## Phase 3: Advanced Features (Week 3) - 18 hours

> **⚠️ NOTE**: These advanced features are deferred. Focus is on D3.js refactor first.

<details>
<summary><strong>Advanced Features (Deferred)</strong></summary>

### Task 3.1: Click-to-Filter Drill-Down (8h)

Implement event handlers on charts to navigate to gene browser with filters.

### Task 3.2: Gene×Source Heatmap (10h)

Use handler pattern + thread pool for heavy query, implement VueUiHeatmap component.

</details>

---

## Testing & Documentation (Ongoing)

### Unit Tests
- ✅ Constants validation
- ✅ Filter clause generation
- ✅ Handler pattern coverage
- ✅ JSONB schema verification

### Integration Tests
- API endpoint responses
- Filter combinations
- Performance benchmarks

### Documentation
- User guide for evidence tiers vs classifications
- Developer guide for adding new sources (handler pattern)

---

## Success Criteria

- [ ] All Vuetify progress bars replaced with vue-data-ui
- [ ] Evidence tier distribution uses correct labels (Very High/High Confidence)
- [ ] Source distributions show meaningful metrics (providers, classifications, phenotypes)
- [ ] Global tier filter works across all visualizations
- [ ] API responses use ResponseBuilder pattern
- [ ] All queries use gene_filters.py system
- [ ] All operations logged with UnifiedLogger
- [ ] JSONB indexes improve query performance
- [ ] No event loop blocking (thread pool for heavy queries)
- [ ] Unit test coverage >80%

---

## Files Changed Summary

### Backend
- ✅ `app/core/constants.py` (new)
- ✅ `app/core/gene_filters.py` (extend)
- ✅ `app/crud/statistics_handlers.py` (new)
- ✅ `app/crud/statistics.py` (modify)
- ✅ `app/api/endpoints/statistics.py` (modify)
- ✅ `alembic/versions/xxx_add_visualization_jsonb_indexes.py` (new)
- ✅ `tests/core/test_constants.py` (new)
- ✅ `tests/crud/test_jsonb_schemas.py` (new)
- ✅ `tests/crud/test_statistics_handlers.py` (new)

### Frontend
- ✅ `views/Dashboard.vue` (modify - add global filter)
- ✅ `components/visualizations/SourceDistributionsChart.vue` (replace progress bars)
- ✅ `components/visualizations/EvidenceCompositionChart.vue` (replace progress bars)
- ✅ `components/visualizations/UpSetChart.vue` (add tier filter)

---

**Status**: ✅ Ready for Implementation
**Next Step**: Begin Phase 0, Task 0.1 (Create constants.py)
**Estimated Timeline**: 12-13 days total
