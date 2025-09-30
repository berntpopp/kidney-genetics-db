# Developer Guides

**Comprehensive guides for developers working on the platform**

## Documentation in This Section

- **[Setup Environment](setup-environment.md)** - Complete environment setup
- **[Hybrid Development](hybrid-development.md)** - Docker + local workflow
- **[Database Operations](database-operations.md)** - Database management
- **[Testing Guide](testing.md)** - Testing strategies and practices
- **[Contributing Guide](contributing.md)** - Contribution guidelines

## Development Workflow

1. **Setup** - Follow [Setup Environment](setup-environment.md)
2. **Daily Work** - Use [Hybrid Development](hybrid-development.md) mode
3. **Database** - Manage with [Database Operations](database-operations.md)
4. **Testing** - Write tests per [Testing Guide](testing.md)

## Key Commands

```bash
# Start development environment
make hybrid-up
make backend
make frontend

# Database operations
make db-reset
make db-clean

# Testing and linting
make test
make lint

# System status
make status
```

## Best Practices

- ✅ Always use unified logging (`UnifiedLogger`)
- ✅ Use cache service (never create new cache implementations)
- ✅ Extend `BaseAnnotationSource` for new annotation sources
- ✅ Use thread pools for blocking operations in async context
- ✅ Preserve git history with `git mv` when moving files

## Related Documentation

- [Getting Started](../../getting-started/) - Quick start guide
- [Architecture](../../architecture/) - System design
- [Reference](../../reference/) - Technical references
- [CLAUDE.md](../../../CLAUDE.md) - AI assistant instructions