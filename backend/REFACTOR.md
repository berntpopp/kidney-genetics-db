# Backend Refactoring Plan: Eliminating Code Duplication and Implementing Best Practices

## Executive Summary

This refactoring plan addresses critical code duplication issues identified in the backend codebase, particularly in data source modules, gene normalization, HGNC clients, and background task management. The plan follows DRY (Don't Repeat Yourself), KISS (Keep It Simple, Stupid), and SOLID principles to create a maintainable, testable, and scalable architecture.

## Current Issues Analysis

### 1. Data Source Module Duplication (Critical Priority)

**Problem**: Multiple implementations for each data source:
- **GenCC**: 3 files (`gencc.py`, `gencc_async.py`, `gencc_cached.py`)
- **PubTator**: 4 files (`pubtator.py`, `pubtator_async.py`, `pubtator_cache.py`, `pubtator_cached.py`)
- **PanelApp**: 2 files (`panelapp.py`, `panelapp_cached.py`)

**Impact**: 
- Code maintenance nightmare (changes need to be made in multiple places)
- Inconsistent behavior between implementations
- Increased bug surface area
- Developer confusion about which version to use

### 2. Gene Normalization Duplication (High Priority)

**Problem**: Two separate implementations:
- `gene_normalization.py`: Uses inefficient `asyncio.run()` within sync functions
- `gene_normalization_async.py`: Proper async implementation

**Impact**:
- `asyncio.run()` cannot be called from a running event loop (causing current crashes)
- Duplicated business logic
- Performance degradation from sync wrapper

### 3. HGNC Client Duplication (High Priority)

**Problem**: Two client implementations:
- `hgnc_client.py`: Uses in-memory `lru_cache`
- `hgnc_client_cached.py`: Uses persistent `CacheService`

**Impact**:
- Inconsistent caching strategies
- Lost cache data between application restarts with old client
- Developer confusion about which to use

### 4. Background Task Boilerplate (Medium Priority)

**Problem**: Repetitive setup/teardown code in each `_run_*` method in `background_tasks.py`

**Impact**:
- Violation of DRY principle
- Error-prone when adding new tasks
- Inconsistent error handling

### 5. Cache Service Type Issues (High Priority)

**Problem**: Cache service expecting string keys but receiving other types

**Impact**:
- Runtime errors: `'int' object has no attribute 'strip'`
- Degraded user experience
- Failed cache operations

## Refactoring Strategy

### Phase 1: Unified Data Source Architecture (Weeks 1-2)

#### 1.1 Create Abstract Base Data Source Client

**Implementation Strategy**: Factory + Template Method patterns

```python
# app/core/data_source_base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.cache_service import CacheService, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.progress_tracker import ProgressTracker

class DataSourceClient(ABC):
    """Abstract base class for all data source clients."""
    
    def __init__(
        self, 
        cache_service: Optional[CacheService] = None,
        http_client: Optional[CachedHttpClient] = None,
        db_session: Optional[Session] = None
    ):
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)
        self.db_session = db_session
        
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        pass
        
    @property
    @abstractmethod
    def namespace(self) -> str:
        """Return the cache namespace for this data source."""
        pass
    
    @abstractmethod
    async def fetch_raw_data(self) -> Any:
        """Fetch raw data from the external source."""
        pass
        
    @abstractmethod
    async def process_data(self, raw_data: Any) -> Dict[str, Any]:
        """Process raw data into structured format."""
        pass
        
    @abstractmethod
    def is_kidney_related(self, record: Dict[str, Any]) -> bool:
        """Check if a record is kidney-related."""
        pass
        
    async def update_data(self, db: Session, tracker: ProgressTracker) -> Dict[str, Any]:
        """Template method for data update process."""
        stats = self._initialize_stats()
        
        try:
            tracker.start(f"Starting {self.source_name} update")
            
            # Fetch raw data
            tracker.update(operation="Fetching data")
            raw_data = await self.fetch_raw_data()
            
            # Process data
            tracker.update(operation="Processing data")
            processed_data = await self.process_data(raw_data)
            
            # Store in database
            tracker.update(operation="Storing in database")
            await self._store_data(db, processed_data, stats, tracker)
            
            tracker.complete(f"{self.source_name} update completed")
            return stats
            
        except Exception as e:
            tracker.error(str(e))
            stats["error"] = str(e)
            raise
    
    def _initialize_stats(self) -> Dict[str, Any]:
        """Initialize statistics dictionary."""
        return {
            "source": self.source_name,
            "kidney_related": 0,
            "genes_processed": 0,
            "genes_created": 0,
            "evidence_created": 0,
            "errors": 0,
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
    async def _store_data(
        self, 
        db: Session, 
        data: Dict[str, Any], 
        stats: Dict[str, Any], 
        tracker: ProgressTracker
    ) -> None:
        """Template method for storing processed data."""
        # Common database storage logic
        # This can be overridden by subclasses if needed
        pass
```

#### 1.2 Refactor GenCC Client

```python
# app/pipeline/sources/gencc.py (unified implementation)
from app.core.data_source_base import DataSourceClient

class GenCCClient(DataSourceClient):
    @property
    def source_name(self) -> str:
        return "GenCC"
        
    @property 
    def namespace(self) -> str:
        return "gencc"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.download_url = "https://search.thegencc.org/download/action/submissions-export-xlsx"
        self.kidney_keywords = [
            "kidney", "renal", "nephro", "glomerul",
            "tubul", "polycystic", "alport", "nephritis",
            "cystic", "ciliopathy", "complement", "cakut"
        ]
        
    async def fetch_raw_data(self) -> pd.DataFrame:
        """Fetch and parse GenCC Excel file with caching."""
        cache_key = "gencc_raw_data"
        
        # Try cache first
        cached_data = await self.cache_service.get(cache_key, self.namespace)
        if cached_data:
            return cached_data
            
        # Download and parse
        response = await self.http_client.get(self.download_url)
        df = pd.read_excel(BytesIO(response.content))
        
        # Cache the result
        await self.cache_service.set(
            cache_key, 
            df, 
            namespace=self.namespace,
            ttl=86400  # 24 hours
        )
        
        return df
        
    async def process_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Process GenCC data into gene information."""
        gene_data_map = {}
        
        for _, row in df.iterrows():
            if not self.is_kidney_related(row):
                continue
                
            gene_info = self._extract_gene_info(row)
            if not gene_info:
                continue
                
            symbol = gene_info["symbol"]
            if symbol not in gene_data_map:
                gene_data_map[symbol] = {
                    "hgnc_id": gene_info["hgnc_id"],
                    "submissions": [],
                    "diseases": set(),
                    "classifications": set(),
                }
                
            gene_data_map[symbol]["submissions"].append(gene_info)
            gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
            gene_data_map[symbol]["classifications"].add(gene_info["classification"])
            
        return gene_data_map
        
    def is_kidney_related(self, row: pd.Series) -> bool:
        """Check if GenCC record is kidney-related."""
        # Implementation from existing code
        pass
        
    def _extract_gene_info(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Extract gene information from GenCC row."""
        # Implementation from existing code
        pass

# Factory function for backward compatibility
def get_gencc_client(**kwargs) -> GenCCClient:
    return GenCCClient(**kwargs)
```

#### 1.3 Direct Replacement Strategy

**Files to Delete Immediately**:
- `app/pipeline/sources/gencc_async.py` 
- `app/pipeline/sources/gencc_cached.py`
- `app/pipeline/sources/pubtator_async.py`
- `app/pipeline/sources/pubtator_cache.py` 
- `app/pipeline/sources/pubtator_cached.py`
- `app/pipeline/sources/panelapp_cached.py`

**Direct Replacement**:
- Replace all duplicate implementations with the single unified async-first client
- Update all imports immediately to use the correct implementation
- No backward compatibility layers - clean direct migration

### Phase 2: Unified Gene Normalization (Week 2)

#### 2.1 Async-First Implementation

```python
# app/core/gene_normalizer.py (new unified module)
import asyncio
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.core.hgnc_client_cached import get_hgnc_client_cached

logger = logging.getLogger(__name__)

class GeneNormalizer:
    """Unified async-first gene normalization service."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.hgnc_client = get_hgnc_client_cached(db_session=db_session)
        
    async def normalize_batch_async(
        self,
        db: Session,
        gene_texts: List[str],
        source_name: str,
        original_data_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Async batch normalization of gene symbols."""
        if not gene_texts:
            return {}
            
        logger.info(f"[{source_name}] Normalizing {len(gene_texts)} gene texts")
        
        # Clean and prepare
        cleaned_genes = []
        gene_mapping = {}
        
        for i, gene_text in enumerate(gene_texts):
            if not gene_text:
                continue
                
            cleaned = self._clean_gene_text(gene_text)
            if cleaned and self._is_likely_gene_symbol(cleaned):
                cleaned_genes.append(cleaned)
                gene_mapping[cleaned] = {
                    "original": gene_text,
                    "index": i,
                    "original_data": original_data_list[i] if original_data_list else None
                }
        
        if not cleaned_genes:
            return {}
            
        # Check existing genes in database
        existing_genes = self._get_existing_genes(db, cleaned_genes)
        
        # HGNC lookup for remaining genes
        genes_to_lookup = [g for g in cleaned_genes if g not in existing_genes]
        hgnc_results = {}
        
        if genes_to_lookup:
            hgnc_results = await self.hgnc_client.standardize_symbols_parallel(genes_to_lookup)
            
        # Compile results
        return self._compile_results(gene_mapping, existing_genes, hgnc_results)
    
    def _clean_gene_text(self, gene_text: str) -> str:
        """Clean gene text for normalization."""
        # Implementation from existing code
        pass
        
    def _is_likely_gene_symbol(self, gene_text: str) -> bool:
        """Check if text is likely a gene symbol."""
        # Implementation from existing code
        pass
        
    def _get_existing_genes(self, db: Session, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get existing genes from database."""
        # Implementation from existing code
        pass
        
    def _compile_results(
        self, 
        gene_mapping: Dict[str, Dict[str, Any]], 
        existing_genes: Dict[str, Dict[str, Any]], 
        hgnc_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Compile final normalization results."""
        # Implementation from existing code
        pass

# Global instance
_normalizer = None

def get_gene_normalizer(db_session: Optional[Session] = None) -> GeneNormalizer:
    """Get or create gene normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = GeneNormalizer(db_session)
    return _normalizer

# Convenience function - async only
async def normalize_genes_batch_async(
    db: Session,
    gene_texts: List[str], 
    source_name: str,
    original_data_list: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Dict[str, Any]]:
    """Async batch gene normalization - the only correct implementation."""
    normalizer = get_gene_normalizer(db)
    return await normalizer.normalize_batch_async(db, gene_texts, source_name, original_data_list)
```

#### 2.2 Remove Deprecated Files

**Files to Delete**:
- `app/core/gene_normalization.py`
- `app/core/gene_normalization_async.py`

### Phase 3: Unified HGNC Client (Week 2)

#### 3.1 Use Only the Correct Cached Implementation

**Actions**:
1. **Delete** `app/core/hgnc_client.py` immediately
2. **Rename** `hgnc_client_cached.py` to `hgnc_client.py` 
3. **Update** all imports to use the unified implementation

```python
# All code should use:
from app.core.hgnc_client import HGNCClientCached, get_hgnc_client_cached

# Or simplified after renaming:
from app.core.hgnc_client import HGNCClient, get_hgnc_client
```

**Rationale**: The cached implementation with persistent storage is the only correct approach. The in-memory LRU cache version loses data on restart and doesn't share cache across instances.

### Phase 4: Background Task Refactoring (Week 3)

#### 4.1 Task Decorator Pattern

```python
# app/core/task_decorator.py
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Dict
from app.core.database import get_db
from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

def managed_task(source_name: str):
    """Decorator for background tasks with common setup/teardown."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, resume: bool = False) -> Dict[str, Any]:
            """Wrapper with common task management logic."""
            db = None
            tracker = None
            
            try:
                # Setup
                db = next(get_db())
                tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                
                logger.info(f"Starting {source_name} update (resume={resume})")
                
                # Execute the actual task
                result = await func(self, db, tracker, resume)
                
                logger.info(f"{source_name} update completed: {result}")
                return result
                
            except Exception as e:
                logger.error(f"{source_name} update failed: {e}")
                if tracker:
                    tracker.error(str(e))
                raise
                
            finally:
                # Cleanup
                if db:
                    try:
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to close database session: {e}")
                        
        return wrapper
    return decorator

class TaskMixin:
    """Mixin providing common task functionality."""
    
    @managed_task("PubTator")
    async def _run_pubtator(self, db, tracker, resume: bool = False):
        """Run PubTator update with managed lifecycle."""
        from app.pipeline.sources.pubtator import get_pubtator_client
        client = get_pubtator_client(db_session=db)
        return await client.update_data(db, tracker)
    
    @managed_task("GenCC") 
    async def _run_gencc(self, db, tracker, resume: bool = False):
        """Run GenCC update with managed lifecycle."""
        from app.pipeline.sources.gencc import get_gencc_client
        client = get_gencc_client(db_session=db)
        return await client.update_data(db, tracker)
        
    @managed_task("PanelApp")
    async def _run_panelapp(self, db, tracker, resume: bool = False):
        """Run PanelApp update with managed lifecycle."""
        from app.pipeline.sources.panelapp import get_panelapp_client
        client = get_panelapp_client(db_session=db)
        return await client.update_data(db, tracker)
```

#### 4.2 Updated Background Task Manager

```python
# app/core/background_tasks.py (refactored)
from app.core.task_decorator import TaskMixin

class BackgroundTaskManager(TaskMixin):
    """Manages background tasks with unified lifecycle management."""
    
    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.broadcast_callback = None
        self._shutdown = False

    async def run_source(self, source_name: str, resume: bool = False):
        """Run update for a specific data source."""
        if source_name in self.running_tasks and not self.running_tasks[source_name].done():
            logger.warning(f"{source_name} is already running")
            return

        # Dynamic task dispatch
        task_method = getattr(self, f"_run_{source_name.lower()}", None)
        if not task_method:
            logger.error(f"Unknown source: {source_name}")
            return

        task = asyncio.create_task(task_method(resume=resume))
        self.running_tasks[source_name] = task
```

### Phase 5: Fix Cache Service Type Issues (Week 1)

#### 5.1 Type-Safe Cache Keys

```python
# app/core/cache_service.py (enhanced)
class CacheService:
    def _normalize_key(self, key: Any) -> str:
        """Normalize cache key to string."""
        if isinstance(key, str):
            return key.strip()
        elif isinstance(key, (int, float)):
            return str(key)
        elif isinstance(key, (list, dict)):
            # Serialize complex types to JSON
            import json
            return json.dumps(key, sort_keys=True)
        else:
            return str(key)
    
    async def get(self, key: Any, namespace: str = "default") -> Any:
        """Get value from cache with type-safe key handling."""
        normalized_key = self._normalize_key(key)
        # Rest of implementation...
        
    async def set(self, key: Any, value: Any, namespace: str = "default", ttl: Optional[int] = None) -> None:
        """Set value in cache with type-safe key handling."""
        normalized_key = self._normalize_key(key)
        # Rest of implementation...
```

## Implementation Timeline

### Week 1: Foundation & Critical Fixes
- [ ] Fix cache service type issues
- [ ] Create `DataSourceClient` base class
- [ ] Create unified `GeneNormalizer`
- [ ] Remove duplicate HGNC client

### Week 2: Data Source Unification  
- [ ] Refactor GenCC to unified implementation
- [ ] Refactor PubTator to unified implementation
- [ ] Refactor PanelApp to unified implementation
- [ ] Update all imports and remove deprecated files

### Week 3: Background Tasks & Testing
- [ ] Implement task decorator pattern
- [ ] Refactor `BackgroundTaskManager`
- [ ] Comprehensive testing suite
- [ ] Performance validation

### Week 4: Documentation & Final Validation
- [ ] Update documentation
- [ ] Code review and refinement
- [ ] Production deployment preparation

## Testing Strategy

### Unit Tests
```python
# tests/test_data_source_base.py
class TestDataSourceClient:
    async def test_template_method_flow(self):
        """Test the template method pattern execution."""
        pass
        
    async def test_error_handling(self):
        """Test proper error handling and cleanup."""
        pass

# tests/test_gene_normalizer.py  
class TestGeneNormalizer:
    async def test_batch_normalization(self):
        """Test batch gene normalization."""
        pass
        
    def test_sync_wrapper_error(self):
        """Test sync wrapper error in async context."""
        pass
```

### Integration Tests
```python
# tests/integration/test_unified_sources.py
class TestUnifiedDataSources:
    async def test_gencc_end_to_end(self):
        """Test complete GenCC data flow."""
        pass
        
    async def test_consistency_across_sources(self):
        """Test consistent behavior across data sources."""
        pass
```

### Performance Tests
```python
# tests/performance/test_refactored_performance.py
class TestPerformance:
    async def test_normalization_performance(self):
        """Ensure refactoring doesn't degrade performance."""
        pass
        
    async def test_cache_efficiency(self):
        """Test cache hit rates and efficiency."""
        pass
```

## Direct Implementation Approach

This refactoring eliminates all duplicate implementations immediately and uses only the correct, optimal patterns:

### Key Principles
1. **One Implementation Per Concern**: Each data source, client, or service has exactly one implementation
2. **Async-First**: All I/O operations use proper async patterns with no sync wrappers
3. **Unified Caching**: All clients use the same persistent cache service with proper type handling
4. **Clean Architecture**: Base classes and interfaces enforce consistent patterns

## Benefits

### Code Quality Improvements
- **90% reduction** in duplicated code across data source modules
- **Elimination** of async/sync duplication in gene normalization
- **Consistent** error handling and caching strategies
- **Type-safe** cache operations

### Maintenance Benefits  
- **Single source of truth** for each data source implementation
- **Easier testing** with unified interfaces
- **Simplified debugging** with consistent patterns
- **Faster development** of new data sources

### Performance Improvements
- **Elimination** of `asyncio.run()` in running event loops
- **Consistent caching** strategies across all components
- **Reduced memory usage** from eliminating duplicate code paths
- **Better error recovery** with unified error handling

### Development Experience
- **Clear patterns** for extending functionality
- **Comprehensive documentation** of unified interfaces  
- **Easier onboarding** for new developers
- **Reduced cognitive load** from simpler architecture

## Risk Mitigation

### Quality Assurance
- Comprehensive test suite covering all functionality before and after refactoring
- Each unified implementation must pass all existing tests for the functionality it replaces
- Code review process to ensure clean implementation patterns

### Performance Validation
- Benchmark tests before and after refactoring to ensure no performance regressions
- Monitor cache hit rates and response times
- Load testing with production-like data volumes

### Error Handling
- Comprehensive exception handling in base classes
- Circuit breaker patterns for external API calls
- Graceful degradation when cache or services fail
- Type-safe operations throughout the stack

This refactoring plan transforms the codebase from a maintenance burden into a clean, extensible architecture that follows industry best practices and significantly improves developer productivity.