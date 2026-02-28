# Minimum Threshold Filters - Final Refactor Plan

## Overview
Implement consistent, configurable minimum threshold filters across ALL data sources (PubTator, DiagnosticPanels, Literature) with unified configuration and logging patterns. This final revision includes PubTator improvements to eliminate chunk boundary effects.

## Core Design Principle: Filter After Complete Data

### Universal Pattern
```
Collect ALL Data → Merge/Accumulate → Apply Filter → Store/Delete
```

This applies to:
- **PubTator**: Process all chunks → Apply filter at end
- **DiagnosticPanels**: Upload → Merge with existing → Apply filter
- **Literature**: Upload → Merge with existing → Apply filter

## Why Include PubTator

### Original Problem (Chunk Boundary Effect)
```python
# Current implementation filters per-chunk:
Chunk 1: GENE1 has 2 publications → Filtered (< 3)
Chunk 50: GENE1 has 2 more publications → Filtered (< 3)
# Result: GENE1 never stored despite having 4 total publications!
```

### Solution: Two-Phase Processing
```python
# Phase 1: Stream and store ALL genes (no filtering)
for chunk in all_chunks:
    process_and_store(chunk)  # No min_publications check

# Phase 2: Apply filter on complete dataset
apply_final_filter()  # Delete genes with total_count < threshold
```

**Benefits:**
- ✅ No chunk boundary effects
- ✅ Consistent with other sources
- ✅ Cleaner, more predictable
- ✅ Same configuration/logging pattern

## Implementation Plan

### Phase 1: Unified Configuration Schema

**File:** `backend/app/core/datasource_config.py`

```python
DATA_SOURCE_CONFIG = {
    "PubTator": {
        # ... existing config ...
        "min_publications": 3,
        "min_publications_enabled": True,  # NEW: Consistent flag
        "filter_after_complete": True,  # NEW: Apply filter after all chunks
    },
    "DiagnosticPanels": {
        # ... existing config ...
        "min_panels": 2,
        "min_panels_enabled": True,
    },
    "Literature": {
        # ... existing config ...
        "min_publications": 2,
        "min_publications_enabled": True,
    }
}
```

### Phase 2: Unified Filtering Utilities

**File:** `backend/app/pipeline/sources/unified/filtering_utils.py`

```python
"""
Unified filtering utilities for all data sources.
Provides consistent filtering logic and statistics tracking.
"""

from typing import Any
from datetime import datetime, timezone

from sqlalchemy import select, delete
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
    
    Args:
        db: Database session
        source_name: Source name (e.g., "PubTator")
        count_field: JSONB field with count (e.g., "publication_count")
        min_threshold: Minimum threshold value
        entity_name: Entity being counted (e.g., "publications")
        enabled: Whether filtering is enabled
        
    Returns:
        FilteringStats object with results
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
        
        # More efficient: Delete directly with subquery, no need for separate SELECT
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
        
        # For logging, get sample of deleted genes (limited query)
        if stats.filtered_count > 0:
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
    
    Args:
        data_dict: Merged gene data dictionary
        count_field: Field containing the count
        min_threshold: Minimum threshold value
        entity_name: Entity being counted
        source_name: Source name for logging
        enabled: Whether filtering is enabled
        
    Returns:
        Tuple of (filtered_data, statistics)
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
    
    Args:
        threshold: Configured threshold value
        entity_name: Entity being counted
        source_name: Source name for logging
        
    Returns:
        Valid threshold (minimum 1)
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

### Phase 3: PubTator Refactor

**File:** `backend/app/pipeline/sources/unified/pubtator.py`

Key changes:
1. Remove filtering from `_flush_buffers()`
2. Add final filtering step after all chunks processed
3. Use consistent configuration pattern
4. Proper transaction handling for database operations

```python
class PubTatorUnifiedSource(UnifiedDataSource):
    def __init__(self, ...):
        super().__init__(...)
        
        # Consistent configuration loading
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
            min_publications=self.min_publications,
            filtering_enabled=self.filtering_enabled,
            filter_after_complete=self.filter_after_complete
        )
    
    async def _flush_buffers(
        self,
        article_buffer: list,
        gene_buffer: dict,
        stats: dict,
        tracker: "ProgressTracker" = None
    ):
        """
        Flush buffers WITHOUT filtering (moved to end).
        """
        if not gene_buffer:
            return
        
        processed_genes = {}
        
        for gene_symbol, new_data in gene_buffer.items():
            # Process data as before
            processed_data = new_data.copy()
            processed_data["pmids"] = list(new_data["pmids"])
            processed_data["identifiers"] = list(new_data["identifiers"])
            processed_data["publication_count"] = len(processed_data["pmids"])
            processed_data["total_mentions"] = len(processed_data["mentions"])
            
            # NO FILTERING HERE ANYMORE!
            # if processed_data["publication_count"] < self.min_publications:
            #     filtered_count += 1
            #     continue
            
            # Calculate average score
            if processed_data["publication_count"] > 0:
                processed_data["evidence_score"] = (
                    processed_data.get("evidence_score", 0) / 
                    processed_data["publication_count"]
                )
            
            # Keep only top mentions
            processed_data["mentions"] = sorted(
                processed_data["mentions"],
                key=lambda x: x.get("score", 0),
                reverse=True
            )[:20]
            
            processed_genes[gene_symbol] = processed_data
        
        # Store ALL genes (no filtering yet)
        await self._store_genes_in_database(
            self.db_session,
            processed_genes,
            stats,
            tracker
        )
        
        stats["processed_articles"] += len(article_buffer)
        stats["processed_genes"] = stats.get("processed_genes", 0) + len(gene_buffer)
        
        logger.sync_info(
            f"Flushed buffers: {len(article_buffer)} articles, "
            f"{len(gene_buffer)} genes (no filtering yet)"
        )
    
    async def _stream_process_pubtator(
        self, query: str, tracker: "ProgressTracker", mode: str
    ) -> dict[str, Any]:
        """
        Stream process with filtering at the END.
        """
        # ... existing streaming logic ...
        # Process all chunks WITHOUT filtering
        
        # At the END, after all chunks processed:
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
                
                # Commit the filtering changes
                self.db_session.commit()
                
                # Add filter stats to overall stats
                stats["genes_filtered"] = filter_stats.filtered_count
                stats["genes_kept"] = filter_stats.total_after
                stats["filter_rate"] = filter_stats.filter_rate
                
                # Store filter statistics
                await self._update_source_metadata({
                    "last_filter_stats": filter_stats.to_dict(),
                    "filter_config": {
                        "min_publications": self.min_publications,
                        "enabled": self.filtering_enabled,
                        "applied_after_complete": True
                    }
                })
                
            except Exception as e:
                # Rollback on error
                self.db_session.rollback()
                logger.sync_error(
                    f"Failed to apply final filter for {self.source_name}",
                    error=str(e)
                )
                raise
        
        return stats
```

### Phase 4: DiagnosticPanels Implementation

**File:** `backend/app/pipeline/sources/unified/diagnostic_panels.py`

```python
from app.pipeline.sources.unified.filtering_utils import (
    apply_memory_filter,
    validate_threshold_config,
    FilteringStats
)

class DiagnosticPanelsSource(UnifiedDataSource):
    def __init__(self, db_session):
        super().__init__(db_session)
        
        # Consistent configuration pattern
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
    
    async def store_evidence(
        self, db: Session, gene_data: dict[str, Any], source_detail: str | None = None
    ) -> dict[str, Any]:
        """
        Store evidence with consistent filtering pattern.
        """
        # ... existing merge logic ...
        
        # After merging, apply filter
        if self.filtering_enabled and self.min_panels > 1:
            filtered_data, filter_stats = apply_memory_filter(
                data_dict=merged_gene_data,
                count_field="panel_count",
                min_threshold=self.min_panels,
                entity_name="panels",
                source_name=self.source_name,
                enabled=self.filtering_enabled
            )
            
            # Handle deletions for filtered genes
            for symbol in merged_gene_data:
                if symbol not in filtered_data:
                    info = merged_gene_data[symbol]
                    if not info["is_new"] and info["record"]:
                        # Delete existing record that now fails filter
                        db.delete(info["record"])
                        logger.sync_info(
                            "Removing gene below threshold",
                            symbol=symbol,
                            panel_count=info["data"]["panel_count"],
                            threshold=self.min_panels
                        )
            
            # Use filtered data for storage
            merged_gene_data = filtered_data
            
            # Store statistics
            await self._update_source_metadata({
                "last_filter_stats": filter_stats.to_dict(),
                "filter_config": {
                    "min_panels": self.min_panels,
                    "enabled": self.filtering_enabled
                }
            })
        
        # ... continue with storage ...
```

### Phase 5: Literature Implementation

**File:** `backend/app/pipeline/sources/unified/literature.py`

```python
# Identical pattern to DiagnosticPanels
# Just different field names:
# - count_field="publication_count"
# - entity_name="publications"
# - min_threshold=self.min_publications
```

## Unified Logging Format

All sources now use identical logging patterns:

```python
# Initialization
"{source_name} initialized with filtering | min_{entity}={value} | filtering_enabled={bool}"

# Filtering complete
"{source_name} filtering complete | total_before={n} | total_after={n} | filtered_count={n} | filter_rate={n}% | threshold=min_{entity}={n}"

# Warning for aggressive filtering
"{source_name} filtered >50% of genes - review threshold | filter_rate={n}% | threshold={n}"

# Individual gene removal
"Removing gene below threshold | symbol={symbol} | {entity}_count={n} | threshold={n}"
```

## Testing Strategy

### 1. PubTator Chunk Boundary Test
```python
def test_pubtator_no_chunk_boundary_effect():
    """Ensure genes split across chunks are kept."""
    # Simulate gene appearing in multiple chunks
    # Each chunk has < 3 publications
    # Total has >= 3 publications
    # Should be KEPT after final filter
```

### 2. Consistent Filter Application
```python
def test_all_sources_filter_consistently():
    """Ensure all sources apply same filtering logic."""
    # Test each source with same threshold patterns
    # Verify identical behavior
```

### 3. Configuration Tests
```python
def test_unified_configuration():
    """Test configuration loading is consistent."""
    for source in ["PubTator", "DiagnosticPanels", "Literature"]:
        assert hasattr(source, "filtering_enabled")
        assert hasattr(source, f"min_{entity}")
```

## Migration Plan

### Phase 1: Deploy with Filtering Disabled
```python
"min_publications_enabled": False,  # All sources
"min_panels_enabled": False,
```

### Phase 2: Test in Staging
1. Enable PubTator filtering first (most data)
2. Monitor statistics
3. Enable others if successful

### Phase 3: Production Rollout
1. Run PubTator with new filtering
2. Compare gene counts before/after
3. Enable for upload sources

## Benefits of Final Plan

### 1. Consistency
- ✅ All sources use same configuration pattern
- ✅ Identical logging format
- ✅ Shared filtering utilities

### 2. Correctness
- ✅ PubTator: No chunk boundary effects
- ✅ DiagnosticPanels/Literature: Filter after merge
- ✅ All sources: Clear audit trail

### 3. Flexibility
- ✅ Enable/disable per source
- ✅ Configurable thresholds
- ✅ Option to filter during or after processing

### 4. Maintainability
- ✅ Single filtering module
- ✅ Consistent patterns
- ✅ Clear documentation

## Technical Improvements in This Plan

### 1. Efficient Database Operations
- **Single DELETE with subquery** instead of SELECT then DELETE
- **RETURNING clause** to get deleted count without extra query
- **Limited sample query** for logging (max 10 records)

### 2. Proper Transaction Management
- **No commit in utility functions** - caller controls transaction
- **Try/catch with rollback** in all database operations
- **Explicit error handling** with proper logging

### 3. Performance Optimizations
- **Early return** if no records to filter
- **Batch operations** instead of row-by-row processing
- **Indexed JSONB queries** using cast for better performance

### 4. Consistent Error Handling
- **Validation at configuration load** time
- **Safe defaults** when config invalid
- **Clear error messages** with context

### 5. DRY Implementation
- **Single FilteringStats class** for all sources
- **Shared validation function** for thresholds
- **Consistent logging format** across all sources

## Key Improvements Over Previous Plans

1. **PubTator Fixed**: Eliminates chunk boundary effects
2. **Unified Utilities**: Single `filtering_utils.py` for all sources
3. **Consistent Configuration**: All sources use `min_{entity}_enabled`
4. **Standard Logging**: Identical format across sources
5. **Database Filtering**: Efficient filtering for large datasets
6. **Memory Filtering**: Appropriate for smaller upload sources

## Success Metrics

✅ **No Data Loss**: Chunk boundaries don't affect PubTator  
✅ **Consistent Behavior**: All sources filter identically  
✅ **Clear Statistics**: Unified logging and tracking  
✅ **Configuration Driven**: No hardcoded values  
✅ **Performance**: Minimal impact (filter once at end)  
✅ **Audit Trail**: Complete record of filtering  

## Conclusion

This final plan provides a complete, consistent solution for minimum threshold filtering across all data sources. PubTator's unique streaming architecture is properly handled by filtering after complete processing, eliminating chunk boundary effects while maintaining the benefits of streaming. All sources share the same configuration pattern, logging format, and filtering utilities, creating a maintainable and predictable system.