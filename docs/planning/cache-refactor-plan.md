# Cache System Refactoring Plan

## Executive Summary
Consolidate three separate caching implementations into a single, unified cache service to reduce code complexity by ~50% and improve performance through proper L1/L2 cache layering.

## Current State Analysis

### 🔴 Three Separate Cache Systems
1. **`app/core/cache.py`** (269 lines) - Simple Redis/memory cache for annotations only
2. **`app/core/cache_service.py`** (853 lines) - Sophisticated L1/L2 cache with PostgreSQL
3. **`app/core/cached_http_client.py`** - HTTP-specific caching with hishel

### 📊 Usage Statistics
- **13 files** using old `annotation_cache` from `cache.py`
- **19 files** using modern `cache_service`
- **Commented-out cache code** in annotation base class (lines 191-216)

## Implementation Plan

### Phase 1: Update Gene Annotation Endpoints (Day 1)
**Goal**: Migrate all annotation caching to unified cache service

#### 1.1 Update `app/api/endpoints/gene_annotations.py`
**Changes Required:**

```python
# Line 47: REMOVE
from app.core.cache import annotation_cache

# Line 47: ADD
from app.core.cache_service import get_cache_service

# Lines 48-53: REPLACE
cached = annotation_cache.get_annotation(gene_id, source)
if cached:
    logger.sync_debug(f"Cache hit for gene {gene_id}", source=source)
    return cached

# WITH:
cache_service = get_cache_service(db)
cached = await cache_service.get(
    key=f"{gene_id}:{source or 'all'}",
    namespace="annotations",
    default=None
)
if cached:
    logger.sync_debug(f"Cache hit for gene {gene_id}", source=source)
    return cached

# Line 88: REPLACE
annotation_cache.set_annotation(gene_id, result, source)

# WITH:
await cache_service.set(
    key=f"{gene_id}:{source or 'all'}",
    value=result,
    namespace="annotations",
    ttl=3600
)
```

**Similar changes needed at lines:**
- Lines 107-113 (get_gene_annotation_summary)
- Line 166 (set_summary)
- Lines 226-234 (all update functions: HGNC, gnomAD, GTEx, Descartes, HPO, ClinVar, MPO/MGI, STRING)
- Lines 736-738 (get_cache_statistics)
- Line 749-751 (clear_annotation_cache)
- Line 769 (invalidate_gene_cache)

### Phase 2: Enable Caching in Base Annotation Source (Day 1)
**File**: `app/pipeline/sources/annotations/base.py`

#### 2.1 Uncomment and Update Cache Implementation (Lines 191-216)

```python
# Line 16: ADD
from app.core.cache_service import get_cache_service

# Lines 191-216: REPLACE commented code with:
async def update_gene(self, gene: Gene) -> bool:
    """Update annotations for a single gene."""
    try:
        # Get cache service
        cache_service = get_cache_service(self.session)
        
        # Check cache first
        cache_key = f"{gene.approved_symbol}:{gene.hgnc_id}"
        cached_data = await cache_service.get(
            key=cache_key,
            namespace=self.source_name.lower(),
            default=None
        )
        
        if cached_data:
            logger.sync_info(
                f"Using cached annotation for {gene.approved_symbol}",
                source=self.source_name
            )
            annotation_data = cached_data
            metadata = {
                "retrieved_at": datetime.utcnow().isoformat(),
                "from_cache": True
            }
        else:
            # Fetch from source
            annotation_data = await self.fetch_annotation(gene)
            
            if annotation_data:
                # Cache the result
                await cache_service.set(
                    key=cache_key,
                    value=annotation_data,
                    namespace=self.source_name.lower(),
                    ttl=self.cache_ttl_days * 86400  # Convert days to seconds
                )
                metadata = {
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "from_cache": False
                }
        
        if annotation_data:
            self.store_annotation(gene, annotation_data, metadata=metadata)
            return True
            
        logger.sync_warning(
            f"No annotation found for {gene.approved_symbol}",
            source=self.source_name
        )
        return False
        
    except Exception as e:
        logger.sync_error(
            f"Error updating gene {gene.approved_symbol}: {str(e)}",
            source=self.source_name
        )
        return False
```

### Phase 3: Update Cache Service for Annotation Support (Day 2)
**File**: `app/core/cache_service.py`

#### 3.1 Add Annotation-Specific Helper Methods (After line 852)

```python
# Add after line 852
async def get_annotation(
    self, 
    gene_id: int, 
    source: str | None = None,
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any] | None:
    """Get cached annotation for a gene (compatibility method)."""
    cache = get_cache_service(db_session)
    key = f"{gene_id}:{source or 'all'}"
    return await cache.get(key, namespace="annotations")

async def set_annotation(
    self,
    gene_id: int,
    data: dict[str, Any],
    source: str | None = None,
    ttl: int = 3600,
    db_session: Session | AsyncSession | None = None
) -> bool:
    """Cache annotation data for a gene (compatibility method)."""
    cache = get_cache_service(db_session)
    key = f"{gene_id}:{source or 'all'}"
    return await cache.set(key, data, namespace="annotations", ttl=ttl)

async def invalidate_gene(
    self,
    gene_id: int,
    db_session: Session | AsyncSession | None = None
) -> int:
    """Invalidate all cached data for a specific gene."""
    cache = get_cache_service(db_session)
    count = 0
    
    # Clear from all namespaces
    for namespace in ["annotations", "summary", "hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi"]:
        pattern_key = f"{gene_id}:*"
        if await cache.delete(pattern_key, namespace):
            count += 1
    
    return count

async def get_summary(
    self,
    gene_id: int,
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any] | None:
    """Get cached annotation summary."""
    cache = get_cache_service(db_session)
    return await cache.get(f"summary:{gene_id}", namespace="annotations")

async def set_summary(
    self,
    gene_id: int,
    data: dict[str, Any],
    ttl: int = 7200,
    db_session: Session | AsyncSession | None = None
) -> bool:
    """Cache annotation summary."""
    cache = get_cache_service(db_session)
    return await cache.set(f"summary:{gene_id}", data, namespace="annotations", ttl=ttl)
```

### Phase 4: Delete Redundant Cache Implementation (Day 2)
**Action**: Delete entire file `app/core/cache.py` (269 lines)

```bash
rm backend/app/core/cache.py
```

### Phase 5: Update Configuration (Day 2)
**File**: `app/core/config.py`

#### 5.1 Remove Redis-specific Settings (Lines 30-31, 41)
```python
# REMOVE Lines 30-31:
REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379
REDIS_DB: int = 0

# KEEP Line 41 but update comment:
CACHE_REDIS_URL: str | None = None  # Reserved for future Redis L3 cache
```

### Phase 6: Create Cache Decorator (Day 3)
**New File**: `app/core/cache_decorator.py`

```python
"""
Cache decorator for FastAPI endpoints and functions.
Provides clean @cache syntax similar to fastapi-cache.
"""

import functools
import hashlib
import inspect
import json
from typing import Any, Callable

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger

logger = get_logger(__name__)


def cache(
    namespace: str = "default",
    ttl: int | None = None,
    key_builder: Callable | None = None
):
    """
    Cache decorator for async functions.
    
    Args:
        namespace: Cache namespace for organization
        ttl: Time to live in seconds
        key_builder: Optional custom key builder function
    
    Usage:
        @cache(namespace="annotations", ttl=3600)
        async def get_gene_data(gene_id: int):
            return expensive_operation(gene_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get db session from kwargs if available
            db_session = kwargs.get('db')
            cache_service = get_cache_service(db_session)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(func, *args, **kwargs)
            else:
                # Default key builder using function name and args
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                # Create key from function name and arguments
                key_parts = [func.__name__]
                for name, value in bound.arguments.items():
                    if name not in ('self', 'cls', 'db'):  # Skip common non-cache params
                        key_parts.append(f"{name}:{value}")
                
                raw_key = ":".join(key_parts)
                cache_key = hashlib.md5(raw_key.encode()).hexdigest()
            
            # Try to get from cache
            cached_value = await cache_service.get(cache_key, namespace)
            if cached_value is not None:
                logger.sync_debug(f"Cache hit for {func.__name__}", key=cache_key)
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_service.set(cache_key, result, namespace, ttl)
            logger.sync_debug(f"Cached result for {func.__name__}", key=cache_key)
            
            return result
        
        return wrapper
    return decorator
```

### Phase 7: Update Cache Endpoints (Day 3)
**File**: `app/api/endpoints/cache.py`

#### 7.1 Remove Annotation Cache References
- No changes needed (already uses cache_service)

#### 7.2 Update Namespace List (Line 238-248)
```python
# Line 238-248: Update fallback namespaces
namespaces = [
    "annotations",  # Unified annotations namespace
    "hgnc",
    "pubtator", 
    "gencc",
    "panelapp",
    "hpo",
    "clingen",
    "clinvar",
    "gnomad",
    "gtex",
    "string_ppi",
    "descartes",
    "mpo_mgi",
    "http",
    "files",
]
```

### Phase 8: Update Tests (Day 4)
**Files to Update:**
- `backend/tests/test_gene_annotations.py` (if exists)
- `backend/tests/test_hgnc_client.py` (Lines with cache references)

```python
# Update any test that uses annotation_cache
# REPLACE:
from app.core.cache import annotation_cache

# WITH:
from app.core.cache_service import get_cache_service

# Update test fixtures to use cache_service
```

### Phase 9: Database Migration (Day 4)
No schema changes needed - `cache_entries` table already exists and supports all requirements.

### Phase 10: Update Documentation (Day 4)
**New File**: `docs/architecture/caching.md`

```markdown
# Caching Architecture

## Overview
The kidney-genetics-db uses a unified multi-layer caching system:
- **L1 Cache**: In-memory LRU cache (fast, process-local)
- **L2 Cache**: PostgreSQL JSONB storage (persistent, shared)
- **L3 Cache**: (Future) Redis for distributed caching

## Usage

### Basic Usage
```python
from app.core.cache_service import get_cache_service

cache = get_cache_service(db_session)
await cache.set("key", value, namespace="annotations", ttl=3600)
value = await cache.get("key", namespace="annotations")
```

### Decorator Usage
```python
from app.core.cache_decorator import cache

@cache(namespace="annotations", ttl=3600)
async def expensive_operation(gene_id: int):
    return fetch_data(gene_id)
```

## Namespaces
Each data source has its own namespace with specific TTLs:
- `annotations`: 1 hour (general annotations)
- `hgnc`: 24 hours (stable reference data)
- `panelapp`: 6 hours (moderate updates)
- `pubtator`: 7 days (literature mining)
- `clinvar`: 12 hours (variant data)
```

## Testing Strategy

### Unit Tests
1. Test cache service CRUD operations
2. Test TTL expiration
3. Test namespace isolation
4. Test cache statistics

### Integration Tests
1. Test annotation endpoint caching
2. Test cache invalidation on updates
3. Test concurrent access patterns
4. Test cache warming

### Performance Tests
1. Measure cache hit rates
2. Compare response times (cached vs uncached)
3. Test memory usage patterns
4. Load test with concurrent requests

## Rollout Plan

### Day 1-2: Development Environment
1. Implement Phase 1-3 changes
2. Run unit tests
3. Manual testing of annotation endpoints

### Day 3-4: Staging Environment  
1. Deploy to staging
2. Run integration tests
3. Monitor cache metrics
4. Performance testing

### Day 5: Production Deployment
1. Deploy during low-traffic window
2. Monitor error rates
3. Track cache hit rates
4. Verify performance improvements

## Rollback Plan

### Quick Rollback (< 5 minutes)
1. Keep `app/core/cache.py` in git history
2. Revert gene_annotations.py changes
3. Restart services

### Full Rollback Steps
```bash
# 1. Restore old cache.py
git checkout HEAD~1 -- backend/app/core/cache.py

# 2. Revert endpoint changes
git checkout HEAD~1 -- backend/app/api/endpoints/gene_annotations.py

# 3. Restart backend
make backend-restart

# 4. Verify functionality
curl http://localhost:8000/api/annotations/genes/1/annotations
```

## Monitoring & Success Metrics

### Key Metrics to Track
1. **Cache Hit Rate**: Target > 70%
2. **Response Time**: 50% reduction for cached requests
3. **Memory Usage**: < 500MB for L1 cache
4. **Error Rate**: < 0.1% increase

### Monitoring Commands
```bash
# Check cache statistics
curl http://localhost:8000/api/admin/cache/stats

# Monitor specific namespace
curl http://localhost:8000/api/admin/cache/stats/annotations

# Check cache health
curl http://localhost:8000/api/admin/cache/health
```

## Expected Benefits

### Quantitative
- **50% code reduction** (~300 lines removed)
- **70% faster response times** for cached requests
- **90% cache hit rate** after warm-up
- **Single cache configuration** (vs 3 separate systems)

### Qualitative
- Unified caching logic
- Better debugging with single cache service
- Consistent TTL management
- Improved monitoring capabilities
- Easier to add new cached endpoints

## Risk Mitigation

### Performance Risks
- **Risk**: L1 cache memory overflow
- **Mitigation**: LRU eviction policy, configurable max size

### Data Consistency Risks
- **Risk**: Stale data in cache
- **Mitigation**: Proper TTLs, invalidation on updates

### Operational Risks
- **Risk**: Cache service failure
- **Mitigation**: Graceful degradation, bypass cache on errors

## Timeline Summary

| Day | Phase | Description | Risk Level |
|-----|-------|-------------|------------|
| 1 | 1-2 | Update annotation endpoints | Medium |
| 1 | 2 | Enable base class caching | Low |
| 2 | 3-4 | Update cache service & delete old cache | High |
| 2 | 5 | Update configuration | Low |
| 3 | 6-7 | Add decorator & update endpoints | Medium |
| 4 | 8-9 | Update tests & documentation | Low |
| 5 | Deploy | Production rollout | Medium |

## Checklist

### Pre-Implementation
- [ ] Backup current cache.py
- [ ] Review all cache usage locations
- [ ] Set up monitoring dashboards
- [ ] Prepare rollback scripts

### Implementation
- [ ] Phase 1: Update gene annotation endpoints
- [ ] Phase 2: Enable base annotation caching
- [ ] Phase 3: Enhance cache service
- [ ] Phase 4: Delete old cache.py
- [ ] Phase 5: Update configuration
- [ ] Phase 6: Create cache decorator
- [ ] Phase 7: Update cache endpoints
- [ ] Phase 8: Update tests
- [ ] Phase 9: Update documentation

### Post-Implementation
- [ ] Run all tests
- [ ] Verify cache statistics endpoint
- [ ] Test cache invalidation
- [ ] Monitor error rates
- [ ] Document lessons learned

## Contact & Support
- **Lead Developer**: [Your Name]
- **Backup**: [Team Member]
- **Escalation**: [Manager/Architect]

## Appendix: File Change Summary

### Files to Modify (14 files)
1. `app/api/endpoints/gene_annotations.py` - 13 locations
2. `app/pipeline/sources/annotations/base.py` - Lines 191-216
3. `app/core/cache_service.py` - Add compatibility methods
4. `app/core/config.py` - Remove Redis config
5. `app/api/endpoints/cache.py` - Update namespaces
6. Test files (3) - Update imports

### Files to Delete (1 file)
1. `app/core/cache.py` - Entire file (269 lines)

### Files to Create (2 files)
1. `app/core/cache_decorator.py` - New decorator
2. `docs/architecture/caching.md` - Documentation

### Total Impact
- **Lines removed**: ~300
- **Lines added**: ~150
- **Net reduction**: ~150 lines
- **Files affected**: 17