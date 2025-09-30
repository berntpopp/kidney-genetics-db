# Minimum Threshold Filters - Implementation TODO

## Overview
This document provides step-by-step implementation instructions with exact code changes, file locations, and line numbers for the minimum threshold filters refactoring.

## Prerequisites
- [ ] Backup database before implementation
- [ ] Test environment ready
- [ ] Current PubTator run completed or cancelled

## Phase 1: Configuration Setup

### 1.1 Update datasource_config.py
**File:** `backend/app/core/datasource_config.py`

**Line 51** - Update PubTator config:
```python
# Current (line 51):
"min_publications": 3,  # Minimum publications for gene inclusion

# Change to:
"min_publications": 3,  # Minimum publications for gene inclusion
"min_publications_enabled": True,  # Enable/disable filtering
"filter_after_complete": True,  # Apply filter after all chunks processed
```

**Line 217** - Add DiagnosticPanels config:
```python
# After line 217, add:
"min_panels": 2,  # Minimum diagnostic panels for gene inclusion
"min_panels_enabled": True,  # Enable/disable filtering
```

**Line 227** - Add Literature config:
```python
# After line 227, add:
"min_publications": 2,  # Minimum publications for gene inclusion
"min_publications_enabled": True,  # Enable/disable filtering
```

## Phase 2: Create Filtering Utilities

### 2.1 Create filtering_utils.py
**New File:** `backend/app/pipeline/sources/unified/filtering_utils.py`

```python
"""
Unified filtering utilities for all data sources.
Provides consistent filtering logic and statistics tracking.
"""

from typing import Any
from datetime import datetime, timezone

from sqlalchemy import select, delete, func, cast, Integer
from sqlalchemy.orm import Session

from app.models.gene import Gene, GeneEvidence
from app.core.logging import get_logger

logger = get_logger(__name__)


class FilteringStats:
    """Track filtering statistics consistently across all sources."""
    
    def __init__(self, source_name: str, entity_name: str, threshold: int):
        self.source_name = source_name
        self.entity_name = entity_name
        self.threshold = threshold
        self.total_before = 0
        self.total_after = 0
        self.filtered_count = 0
        self.filtered_genes = []
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
    
    @property
    def filter_rate(self) -> float:
        if self.total_before == 0:
            return 0.0
        return (self.filtered_count / self.total_before) * 100
    
    @property
    def duration_seconds(self) -> float:
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    def complete(self):
        """Mark filtering as complete."""
        self.end_time = datetime.now(timezone.utc)
    
    def log_summary(self):
        """Log standardized summary across all sources."""
        logger.sync_info(
            f"{self.source_name} filtering complete",
            total_before=self.total_before,
            total_after=self.total_after,
            filtered_count=self.filtered_count,
            filter_rate=f"{self.filter_rate:.1f}%",
            threshold=f"min_{self.entity_name}={self.threshold}",
            duration_seconds=f"{self.duration_seconds:.2f}",
            sample_filtered=self.filtered_genes[:5] if self.filtered_genes else []
        )
        
        # Warn if aggressive
        if self.filter_rate > 50:
            logger.sync_warning(
                f"{self.source_name} filtered >50% of genes - review threshold",
                filter_rate=f"{self.filter_rate:.1f}%",
                threshold=self.threshold,
                entity=self.entity_name
            )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "source_name": self.source_name,
            "entity_name": self.entity_name,
            "threshold": self.threshold,
            "total_before": self.total_before,
            "total_after": self.total_after,
            "filtered_count": self.filtered_count,
            "filter_rate": f"{self.filter_rate:.1f}%",
            "duration_seconds": self.duration_seconds,
            "timestamp": self.end_time.isoformat() if self.end_time else None,
            "filtered_sample": self.filtered_genes[:10]
        }


def apply_database_filter(
    db: Session,
    source_name: str,
    count_field: str,
    min_threshold: int,
    entity_name: str,
    enabled: bool = True
) -> FilteringStats:
    """
    Apply filtering directly in database for complete datasets.
    Used by PubTator after all chunks processed.
    
    IMPORTANT: Caller must handle transaction commit/rollback.
    """
    stats = FilteringStats(source_name, entity_name, min_threshold)
    
    if not enabled or min_threshold <= 1:
        logger.sync_info(
            f"{source_name} filtering disabled",
            min_threshold=min_threshold,
            enabled=enabled
        )
        return stats
    
    try:
        # Count before filtering
        count_stmt = select(func.count()).select_from(GeneEvidence).where(
            GeneEvidence.source_name == source_name
        )
        stats.total_before = db.execute(count_stmt).scalar() or 0
        
        if stats.total_before == 0:
            stats.complete()
            return stats
        
        # More efficient: Delete directly with subquery
        delete_stmt = (
            delete(GeneEvidence)
            .where(
                GeneEvidence.source_name == source_name,
                cast(GeneEvidence.evidence_data[count_field], Integer) < min_threshold
            )
            .returning(GeneEvidence.id)
        )
        
        # Execute and get deleted count
        result = db.execute(delete_stmt)
        deleted_ids = result.fetchall()
        stats.filtered_count = len(deleted_ids)
        
        # Sample some deleted records for logging (before they're gone)
        if stats.filtered_count > 0:
            # Get sample of deleted genes for logging
            sample_stmt = (
                select(Gene.approved_symbol, GeneEvidence.evidence_data[count_field])
                .select_from(GeneEvidence)
                .join(Gene, GeneEvidence.gene_id == Gene.id)
                .where(
                    GeneEvidence.source_name == source_name,
                    cast(GeneEvidence.evidence_data[count_field], Integer) < min_threshold
                )
                .limit(10)
            )
            samples = db.execute(sample_stmt).all()
            
            for symbol, count in samples:
                stats.filtered_genes.append({
                    "symbol": symbol,
                    count_field: count,
                    "threshold": min_threshold
                })
            
            logger.sync_info(
                f"Deleted {stats.filtered_count} genes below threshold",
                source_name=source_name,
                threshold=min_threshold,
                sample=stats.filtered_genes[:3]
            )
        
        # Count after filtering
        stats.total_after = db.execute(count_stmt).scalar() or 0
        
    except Exception as e:
        logger.sync_error(
            f"Database filtering failed for {source_name}",
            error=str(e),
            threshold=min_threshold
        )
        raise
    
    stats.complete()
    stats.log_summary()
    
    return stats


def apply_memory_filter(
    data_dict: dict[str, Any],
    count_field: str,
    min_threshold: int,
    entity_name: str,
    source_name: str,
    enabled: bool = True
) -> tuple[dict[str, Any], FilteringStats]:
    """
    Apply filtering in memory for merged data.
    Used by DiagnosticPanels and Literature.
    """
    stats = FilteringStats(source_name, entity_name, min_threshold)
    stats.total_before = len(data_dict)
    
    if not enabled or min_threshold <= 1:
        logger.sync_info(
            f"{source_name} filtering disabled",
            gene_count=len(data_dict),
            min_threshold=min_threshold,
            enabled=enabled
        )
        stats.total_after = stats.total_before
        stats.complete()
        return data_dict, stats
    
    filtered_data = {}
    
    for gene_symbol, gene_data in data_dict.items():
        count = gene_data.get(count_field, 0)
        
        if count < min_threshold:
            stats.filtered_count += 1
            stats.filtered_genes.append({
                "symbol": gene_symbol,
                count_field: count,
                "threshold": min_threshold
            })
            continue
        
        filtered_data[gene_symbol] = gene_data
    
    stats.total_after = len(filtered_data)
    stats.complete()
    stats.log_summary()
    
    return filtered_data, stats


def validate_threshold_config(
    threshold: Any,
    entity_name: str,
    source_name: str
) -> int:
    """
    Validate threshold configuration with consistent error handling.
    """
    try:
        value = int(threshold)
        if value < 1:
            logger.sync_warning(
                f"Invalid threshold for {source_name}, using minimum",
                configured=value,
                entity=entity_name,
                using=1
            )
            return 1
        return value
    except (TypeError, ValueError):
        logger.sync_error(
            f"Invalid threshold type for {source_name}, disabling filter",
            configured=threshold,
            entity=entity_name,
            using=1
        )
        return 1
```

## Phase 3: Update PubTator

### 3.1 Update pubtator.py imports
**File:** `backend/app/pipeline/sources/unified/pubtator.py`

**Line 10** - Add imports (after existing imports):
```python
from app.pipeline.sources.unified.filtering_utils import (
    apply_database_filter,
    validate_threshold_config,
    FilteringStats
)
```

### 3.2 Update __init__ method
**Line 77-87** - Replace with:
```python
# Current:
self.min_publications = get_source_parameter("PubTator", "min_publications", 3)

# Change to:
raw_threshold = get_source_parameter("PubTator", "min_publications", 3)
self.min_publications = validate_threshold_config(
    raw_threshold, "publications", self.source_name
)
self.filtering_enabled = get_source_parameter(
    "PubTator", "min_publications_enabled", True
)
self.filter_after_complete = get_source_parameter(
    "PubTator", "filter_after_complete", True
)

logger.sync_info(
    f"{self.source_name} initialized with filtering",
    max_pages="ALL" if self.max_pages is None else str(self.max_pages),
    min_publications=self.min_publications,
    filtering_enabled=self.filtering_enabled,
    filter_after_complete=self.filter_after_complete,
    chunk_size=self.chunk_size,
)
```

### 3.3 Remove filtering from _flush_buffers
**Lines 486-489** - Remove these lines:
```python
# DELETE THESE LINES:
# Apply minimum publication filter for quality control
if processed_data["publication_count"] < self.min_publications:
    filtered_count += 1
    continue  # Skip genes with insufficient publications
```

**Line 520** - Update log message:
```python
# Current:
f"({len(processed_genes)} kept, {filtered_count} filtered by min_publications={self.min_publications})"

# Change to:
f"{len(processed_genes)} genes processed (filtering will be applied after all chunks)"
```

### 3.4 Add final filtering to _stream_process_pubtator
**Line 420** - Add after the main processing loop, before return:
```python
# After line 420 (before return stats), add:

# Apply final filtering if enabled
if self.filtering_enabled and self.filter_after_complete:
    logger.sync_info(
        "Applying final filter to complete PubTator dataset",
        min_publications=self.min_publications
    )
    
    try:
        # Apply filter on complete database
        filter_stats = apply_database_filter(
            db=self.db_session,
            source_name=self.source_name,
            count_field="publication_count",
            min_threshold=self.min_publications,
            entity_name="publications",
            enabled=self.filtering_enabled
        )
        
        # Commit the deletions
        self.db_session.commit()
        
        # Add filter stats to overall stats
        stats["genes_filtered"] = filter_stats.filtered_count
        stats["genes_kept"] = filter_stats.total_after
        stats["filter_rate"] = filter_stats.filter_rate
        
        # Store filter statistics in metadata
        # Note: _update_source_metadata is async, need to handle properly
        # This is a simplified version - actual implementation may vary
        metadata = {
            "last_filter_stats": filter_stats.to_dict(),
            "filter_config": {
                "min_publications": self.min_publications,
                "enabled": self.filtering_enabled,
                "applied_after_complete": True
            }
        }
        # Store metadata (implementation depends on your system)
        
    except Exception as e:
        self.db_session.rollback()
        logger.sync_error(
            "Failed to apply final filter",
            source=self.source_name,
            error=str(e)
        )
        raise
```

## Phase 4: Update DiagnosticPanels

### 4.1 Update diagnostic_panels.py imports
**File:** `backend/app/pipeline/sources/unified/diagnostic_panels.py`

**Line 10** - Add imports:
```python
from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.unified.filtering_utils import (
    apply_memory_filter,
    validate_threshold_config,
    FilteringStats
)
```

### 4.2 Add __init__ method
**After line 50** - Add initialization:
```python
def __init__(self, db_session):
    super().__init__(db_session)
    
    # Load filtering configuration
    raw_threshold = get_source_parameter("DiagnosticPanels", "min_panels", 1)
    self.min_panels = validate_threshold_config(
        raw_threshold, "panels", self.source_name
    )
    self.filtering_enabled = get_source_parameter(
        "DiagnosticPanels", "min_panels_enabled", False
    )
    
    logger.sync_info(
        f"{self.source_name} initialized with filtering",
        min_panels=self.min_panels,
        filtering_enabled=self.filtering_enabled
    )
```

### 4.3 Update store_evidence method
**Line 290-330** - Modify the evidence processing section:

**After merging logic (around line 310), add:**
```python
# After all merging is complete, before storing to database:

# Prepare merged data dictionary
merged_gene_data = {}
for symbol, data in gene_data.items():
    gene_id = gene_map.get(symbol)
    if not gene_id:
        continue
    
    # Check if exists and merge
    if gene_id in existing_map:
        record = existing_map[gene_id]
        current_data = record.evidence_data or {}
        
        # Merge panels and providers
        existing_panels = set(current_data.get("panels", []))
        new_panels = set(data["panels"])
        merged_panels = sorted(existing_panels | new_panels)
        
        existing_providers = set(current_data.get("providers", []))
        new_providers = set(data.get("providers", []))
        if current_provider:
            new_providers.add(current_provider)
        merged_providers = sorted(existing_providers | new_providers)
        
        merged_data = {
            "panels": merged_panels,
            "providers": merged_providers,
            "panel_count": len(merged_panels),
            "provider_count": len(merged_providers),
        }
        
        merged_gene_data[symbol] = {
            "gene_id": gene_id,
            "data": merged_data,
            "record": record,
            "is_new": False
        }
    else:
        # New gene
        merged_gene_data[symbol] = {
            "gene_id": gene_id,
            "data": data,
            "record": None,
            "is_new": True
        }

# Apply filtering if enabled
if self.filtering_enabled and self.min_panels > 1:
    # Extract data for filtering
    data_to_filter = {
        symbol: info["data"] 
        for symbol, info in merged_gene_data.items()
    }
    
    filtered_data, filter_stats = apply_memory_filter(
        data_dict=data_to_filter,
        count_field="panel_count",
        min_threshold=self.min_panels,
        entity_name="panels",
        source_name=self.source_name,
        enabled=self.filtering_enabled
    )
    
    # Handle filtered genes
    genes_to_remove = []
    for symbol, info in merged_gene_data.items():
        if symbol not in filtered_data:
            if not info["is_new"] and info["record"]:
                # Delete existing record that now fails filter
                db.delete(info["record"])
                logger.sync_info(
                    "Removing gene below threshold",
                    symbol=symbol,
                    panel_count=info["data"]["panel_count"],
                    threshold=self.min_panels
                )
            genes_to_remove.append(symbol)
            stats["filtered"] = stats.get("filtered", 0) + 1
    
    # Remove filtered genes
    for symbol in genes_to_remove:
        del merged_gene_data[symbol]

# Continue with storing the filtered data...
```

## Phase 5: Update Literature

### 5.1 Update literature.py
**File:** `backend/app/pipeline/sources/unified/literature.py`

Follow the exact same pattern as DiagnosticPanels:
- Add imports (line 10)
- Add __init__ method (after line 50)
- Modify store_evidence method (lines 290-330)

Key differences:
- Use `min_publications` instead of `min_panels`
- Use `publication_count` instead of `panel_count`
- Use "publications" instead of "panels" for entity_name

## Phase 6: Testing

### 6.1 Unit Tests
**New File:** `backend/tests/test_filtering.py`

```python
import pytest
from app.pipeline.sources.unified.filtering_utils import (
    apply_memory_filter,
    validate_threshold_config,
    FilteringStats
)

def test_memory_filter_basic():
    """Test basic filtering logic."""
    data = {
        "GENE1": {"panel_count": 1, "panels": ["A"]},
        "GENE2": {"panel_count": 2, "panels": ["A", "B"]},
        "GENE3": {"panel_count": 3, "panels": ["A", "B", "C"]},
    }
    
    filtered, stats = apply_memory_filter(
        data_dict=data,
        count_field="panel_count",
        min_threshold=2,
        entity_name="panels",
        source_name="Test",
        enabled=True
    )
    
    assert len(filtered) == 2
    assert "GENE1" not in filtered
    assert "GENE2" in filtered
    assert "GENE3" in filtered
    assert stats.filtered_count == 1
    assert stats.filter_rate == pytest.approx(33.3, 0.1)

def test_filter_disabled():
    """Test that filtering can be disabled."""
    data = {
        "GENE1": {"panel_count": 1},
        "GENE2": {"panel_count": 2},
    }
    
    filtered, stats = apply_memory_filter(
        data_dict=data,
        count_field="panel_count",
        min_threshold=2,
        entity_name="panels",
        source_name="Test",
        enabled=False  # Disabled
    )
    
    assert len(filtered) == 2
    assert stats.filtered_count == 0

def test_validate_threshold():
    """Test threshold validation."""
    assert validate_threshold_config(3, "test", "Test") == 3
    assert validate_threshold_config(0, "test", "Test") == 1  # Min is 1
    assert validate_threshold_config(-5, "test", "Test") == 1  # Min is 1
    assert validate_threshold_config("invalid", "test", "Test") == 1  # Invalid
```

### 6.2 Integration Tests
```bash
# Test PubTator filtering
curl -X POST http://localhost:8000/api/datasources/PubTator/update

# Check results after completion
curl http://localhost:8000/api/datasources/ | jq '.data.sources[] | select(.name=="PubTator")'

# Test DiagnosticPanels upload with filtering
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -F "file=@test_panels.csv" \
  -F "provider_name=TestProvider"
```

## Phase 7: Database Verification

### 7.1 Check filtering worked
```sql
-- PubTator: No genes with < 3 publications
SELECT COUNT(*) 
FROM gene_evidence 
WHERE source_name = 'PubTator' 
  AND (evidence_data->>'publication_count')::int < 3;
-- Should return 0

-- DiagnosticPanels: No genes with < 2 panels
SELECT COUNT(*)
FROM gene_evidence
WHERE source_name = 'DiagnosticPanels'
  AND (evidence_data->>'panel_count')::int < 2;
-- Should return 0

-- Literature: No genes with < 2 publications
SELECT COUNT(*)
FROM gene_evidence
WHERE source_name = 'Literature'
  AND (evidence_data->>'publication_count')::int < 2;
-- Should return 0
```

### 7.2 Check statistics
```sql
-- View filtering statistics
SELECT 
    source_name,
    COUNT(*) as gene_count,
    MIN((evidence_data->>'publication_count')::int) as min_pubs,
    MAX((evidence_data->>'publication_count')::int) as max_pubs,
    AVG((evidence_data->>'publication_count')::int) as avg_pubs
FROM gene_evidence
WHERE source_name IN ('PubTator', 'Literature')
GROUP BY source_name;
```

## Phase 8: Rollback Plan

### 8.1 To disable filtering without code changes:
```python
# In datasource_config.py, set:
"min_publications_enabled": False,  # For PubTator
"min_panels_enabled": False,  # For DiagnosticPanels
```

### 8.2 To restore filtered data:
```bash
# Re-run PubTator without filtering
# Re-upload diagnostic panel files
# Re-upload literature files
```

## Migration Checklist

- [ ] Backup database
- [ ] Update configuration files
- [ ] Create filtering_utils.py
- [ ] Update PubTator implementation
- [ ] Update DiagnosticPanels implementation
- [ ] Update Literature implementation
- [ ] Run unit tests
- [ ] Test PubTator with small dataset
- [ ] Test file uploads
- [ ] Verify database constraints
- [ ] Document configuration changes
- [ ] Update API documentation

## Notes

1. **Transaction Safety**: All database operations should be wrapped in try/except with proper rollback
2. **Async Handling**: PubTator's async methods need careful handling when calling sync database operations
3. **Performance**: For large datasets (>10K genes), the DELETE operation may take time
4. **Monitoring**: Watch logs during first production run for any unexpected behavior
5. **Configuration**: Consider adding these to environment variables for easy adjustment

## Troubleshooting

### If PubTator hangs during filtering:
```python
# Check for lock:
SELECT * FROM pg_locks WHERE NOT granted;

# Cancel long-running query:
SELECT pg_cancel_backend(pid) 
FROM pg_stat_activity 
WHERE query LIKE '%gene_evidence%' 
  AND state = 'active';
```

### If too many genes filtered:
1. Check threshold values in config
2. Review sample filtered genes in logs
3. Adjust thresholds and re-run

### If memory issues during filtering:
1. Reduce chunk size for PubTator
2. Process file uploads in smaller batches
3. Consider pagination for large result sets