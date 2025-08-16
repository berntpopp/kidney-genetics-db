# Cache System Refactoring

## Overview

This document outlines the comprehensive refactoring of the caching system for the kidney genetics database. The current system has inconsistent caching strategies across different data sources, leading to inefficiencies and missed optimization opportunities.

## Current State Analysis

### Existing Cache Implementations

#### 1. HGNC Client (`backend/app/core/hgnc_client.py`)
- **Type**: `functools.lru_cache` (in-memory)
- **Configuration**: 
  - `symbol_to_hgnc_id`: 10,000 entries max
  - `get_gene_info`: 10,000 entries max
  - `standardize_symbol`: 1,000 entries max
  - `standardize_symbols_batch`: 1,000 entries max
- **Issues**: Cache lost on application restart, no persistence

#### 2. PubTator (`backend/app/pipeline/sources/pubtator.py` + `pubtator_cache.py`)
- **Type**: Custom file-based cache using JSON
- **Configuration**: 7-day TTL, MD5 hashing for keys
- **Storage**: `.cache/pubtator` directory
- **Features**: Cache validity checking, metadata storage
- **Issues**: File-based, not shared across instances

#### 3. GenCC (`backend/app/pipeline/sources/gencc.py`)
- **Type**: No caching
- **Problem**: Downloads 3.6MB Excel file on every request
- **Impact**: Major performance and bandwidth inefficiency

#### 4. PanelApp (`backend/app/pipeline/sources/panelapp.py`)
- **Type**: No caching
- **Problem**: API calls for each panel search
- **Impact**: Repeated requests for same panel data

#### 5. HPO (`backend/app/pipeline/sources/hpo.py`)
- **Type**: Basic file validation with `is_cache_valid()`
- **Problem**: Downloads large files repeatedly
- **Impact**: Bandwidth waste and slow initialization

## Problems Identified

### 1. Inconsistent Strategies
- Each data source implements its own caching approach
- No unified interface or management
- Different TTL strategies and storage mechanisms

### 2. No Persistence
- HGNC cache (most frequently used) is lost on restart
- No shared cache across multiple application instances
- Cold start performance issues

### 3. Major Inefficiencies
- GenCC downloads 3.6MB file repeatedly (could be cached for 12+ hours)
- PanelApp makes redundant API calls for same panels
- HPO downloads large ontology files without intelligent caching

### 4. No Management Interface
- No way to monitor cache performance
- No ability to clear or warm caches
- No cache statistics or health monitoring

### 5. Poor Error Handling
- No intelligent retry logic for failed requests
- No graceful degradation when APIs are down
- Cache misses lead to immediate external API calls

## Proposed Modern Architecture

### Core Principles
1. **Unified Interface**: Single cache service for all data sources
2. **Multi-layer Caching**: Memory + Database + HTTP layers
3. **RFC 9111 Compliance**: Modern HTTP caching standards
4. **Intelligent TTL**: Per-source optimized expiration
5. **Persistent Storage**: Database-backed for sharing across instances
6. **Management API**: Admin endpoints for cache control
7. **Monitoring**: Comprehensive statistics and health tracking

### Technology Stack
- **Hishel**: RFC 9111 compliant HTTP caching for httpx
- **PostgreSQL**: Persistent cache storage (existing infrastructure)
- **Redis** (future): Optional high-performance cache layer
- **Pydantic**: Cache models and validation
- **FastAPI**: Management API endpoints

## Implementation Design

### 1. Database Schema

```sql
-- Core cache entries table
CREATE TABLE cache_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key TEXT NOT NULL UNIQUE,
    namespace TEXT NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    access_count INTEGER DEFAULT 1,
    data_size INTEGER GENERATED ALWAYS AS (pg_column_size(data)) STORED,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Performance indexes
CREATE INDEX idx_cache_entries_namespace ON cache_entries(namespace);
CREATE INDEX idx_cache_entries_expires_at ON cache_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_cache_entries_last_accessed ON cache_entries(last_accessed);

-- Cache statistics view
CREATE VIEW cache_stats AS
SELECT 
    namespace,
    COUNT(*) as total_entries,
    SUM(data_size) as total_size_bytes,
    SUM(access_count) as total_accesses,
    AVG(access_count) as avg_accesses,
    COUNT(*) FILTER (WHERE expires_at IS NULL OR expires_at > NOW()) as active_entries,
    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_entries
FROM cache_entries 
GROUP BY namespace;
```

### 2. Cache Service Architecture

#### Multi-Layer Caching
- **L1 (Memory)**: Fast in-memory cache for hot data (LRU eviction)
- **L2 (Database)**: Persistent PostgreSQL storage for sharing across instances
- **L3 (HTTP)**: Hishel-powered HTTP response caching with RFC 9111 compliance

#### Cache-Aside Pattern
```python
async def get_or_fetch(key, fetch_func, namespace, ttl):
    # 1. Check L1 (memory)
    # 2. Check L2 (database)
    # 3. Execute fetch_func if cache miss
    # 4. Store result in both L1 and L2
    # 5. Return result
```

### 3. Per-Source Configuration

#### TTL Strategy by Data Source
- **HGNC**: 24 hours (stable reference data)
- **PubTator**: 7 days (literature updates periodically)
- **GenCC**: 12 hours (regular submission updates)
- **PanelApp**: 6 hours (moderate update frequency)
- **HPO**: 7 days (stable ontology releases)

#### Cache Policies
- **HGNC**: Aggressive caching, high hit ratio expected
- **PubTator**: Medium TTL, intelligent pagination caching
- **GenCC**: File-level caching with ETag validation
- **PanelApp**: API response caching with conditional requests
- **HPO**: Large file caching with version checking

### 4. Management API

#### Endpoints
```
GET    /api/admin/cache/stats                    # Overall cache statistics
GET    /api/admin/cache/stats/{namespace}        # Namespace-specific stats
DELETE /api/admin/cache/{namespace}              # Clear namespace
DELETE /api/admin/cache/{namespace}/{key}        # Clear specific key
POST   /api/admin/cache/warm                     # Warm cache with critical data
GET    /api/admin/cache/health                   # Cache system health
GET    /api/admin/cache/keys                     # List cache keys (with pagination)
```

#### Statistics Tracked
- Hit/miss ratios per namespace
- Cache size and memory usage
- Average response times
- TTL effectiveness
- Error rates and retry statistics

### 5. Error Handling & Resilience

#### Circuit Breaker Pattern
- Prevent cascading failures when external APIs are down
- Automatic fallback to cached data during outages
- Gradual recovery when services come back online

#### Intelligent Retry Logic
- Exponential backoff for transient failures
- Different retry strategies per data source
- Cache successful responses, don't cache errors

#### Graceful Degradation
- Serve stale cache when external APIs fail
- Configurable staleness tolerance per source
- User notification of potentially outdated data

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1)
1. **Database Migration**: Create cache_entries table and indexes
2. **Base Service**: Implement CacheService with basic get/set operations
3. **Configuration**: Add cache settings to config.py
4. **HTTP Client**: Create Hishel-powered HTTP client wrapper

### Phase 2: Data Source Integration (Week 2-3)
1. **HGNC Migration**: Replace lru_cache with persistent cache
2. **PubTator Migration**: Migrate from file cache to unified system
3. **GenCC Enhancement**: Add intelligent file caching
4. **PanelApp/HPO**: Implement caching for previously uncached sources

### Phase 3: Management & Monitoring (Week 3-4)
1. **API Endpoints**: Implement cache management API
2. **Statistics**: Add comprehensive monitoring
3. **Health Checks**: Cache system health monitoring
4. **Admin Interface**: Basic cache management in admin panel

### Phase 4: Optimization & Testing (Week 4)
1. **Performance Testing**: Benchmark cache performance
2. **Memory Optimization**: Tune cache sizes and TTLs
3. **Error Testing**: Validate error handling and resilience
4. **Documentation**: Complete implementation documentation

## Expected Benefits

### Performance Improvements
- **HGNC**: 5-10x faster gene standardization (persistent cache)
- **GenCC**: 100x faster file access (eliminate repeated downloads)
- **PubTator**: 2-3x faster literature searches (optimized caching)
- **Overall**: 30-50% reduction in external API calls

### Operational Benefits
- **Reduced API costs**: Fewer external requests
- **Better reliability**: Graceful degradation during outages
- **Improved monitoring**: Unified cache statistics
- **Easier debugging**: Centralized cache management

### Developer Experience
- **Consistent API**: Same caching interface across all sources
- **Easy configuration**: Environment-based TTL settings
- **Better testing**: Mockable cache service for unit tests
- **Clear documentation**: Comprehensive cache behavior documentation

## Configuration

### Environment Variables
```bash
# Cache system settings
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600
CACHE_MAX_MEMORY_SIZE=1000
CACHE_CLEANUP_INTERVAL=3600

# Per-source TTL configuration
CACHE_TTL_HGNC=86400        # 24 hours
CACHE_TTL_PUBTATOR=604800   # 7 days
CACHE_TTL_GENCC=43200       # 12 hours
CACHE_TTL_PANELAPP=21600    # 6 hours
CACHE_TTL_HPO=604800        # 7 days

# HTTP cache settings
HTTP_CACHE_DIR=.cache/http
HTTP_CACHE_MAX_SIZE=500     # MB
```

## Testing Strategy

### Unit Tests
- Cache service operations (get/set/delete)
- TTL handling and expiration
- Error conditions and fallbacks
- Memory management and cleanup

### Integration Tests
- End-to-end caching for each data source
- Database persistence across restarts
- HTTP cache validation with real APIs
- Performance benchmarks

### Load Tests
- Cache performance under high load
- Memory usage with large datasets
- Database performance with many cache entries
- Concurrent access patterns

## Monitoring & Alerting

### Key Metrics
- Cache hit ratio (target: >80% for HGNC, >60% overall)
- Average response time improvement
- Memory usage and cache size
- Error rates and failed cache operations

### Alerts
- Cache hit ratio drops below threshold
- Cache size exceeds memory limits
- Database connection failures
- Excessive external API calls (cache miss spike)

## Future Enhancements

### Redis Integration
- Optional Redis layer for high-performance caching
- Distributed caching across multiple instances
- Pub/sub for cache invalidation events

### Advanced Features
- Predictive cache warming based on usage patterns
- Automatic TTL optimization based on data freshness
- Cache compression for large entries
- Backup and restore cache data

## Conclusion

This cache refactoring will significantly improve the performance, reliability, and maintainability of the kidney genetics database. By implementing modern caching standards and providing a unified interface, we'll reduce external API dependencies while improving user experience and system resilience.

The phased implementation approach ensures minimal disruption to existing functionality while providing immediate benefits as each component is migrated to the new system.