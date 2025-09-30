# Reference Documentation

**Technical references and specifications**

## Documentation in This Section

- **[Configuration](configuration.md)** - Configuration system and options
- **[Logging System](logging-system.md)** - Unified logging architecture
- **[Caching Internals](caching-internals.md)** - Cache system implementation
- **[Database Schema](database-schema.md)** - Complete schema reference
- **[Environment Variables](environment-variables.md)** - Environment configuration
- **[Code Style Guide](code-style-guide.md)** - Coding standards and conventions

## Quick Reference

### Key Systems (MUST REUSE)

#### Logging
```python
from app.core.logging import get_logger
logger = get_logger(__name__)
await logger.info("Message", key="value")
```

#### Caching
```python
from app.core.cache_service import get_cache_service
cache = get_cache_service(db_session)
await cache.set("key", value, namespace="annotations")
```

#### Retry Logic
```python
from app.core.retry_utils import retry_with_backoff
@retry_with_backoff()
async def api_call():
    return await client.get(url)
```

### Configuration

See [Configuration Reference](configuration.md) for:
- Environment variables
- Configuration files
- Data source configuration
- Feature flags

### Database

See [Database Schema](database-schema.md) for:
- Table definitions
- Relationships
- Indexes and constraints
- JSONB structures

## Development Principles

### DRY (Don't Repeat Yourself)
- ✅ Use `UnifiedLogger` - Never use `print()` or `logging.getLogger()`
- ✅ Use `CacheService` - Never create new cache implementations
- ✅ Use `retry_with_backoff` - Never write custom retry loops
- ✅ Extend `BaseAnnotationSource` - Never create sources from scratch

### Non-Blocking Architecture
- ✅ Async/await throughout
- ✅ Thread pools for sync DB operations
- ✅ Never block the event loop (<5ms target)
- ✅ WebSocket stability maintained

## Related Documentation

- [Architecture](../architecture/) - System design
- [Developer Guides](../guides/developer/) - Development guides
- [CLAUDE.md](../../CLAUDE.md) - Complete development guidelines