# Troubleshooting

**Common issues and solutions**

## Documentation in This Section

- **[Common Issues](common-issues.md)** - Frequently encountered problems
- **[Performance Tuning](performance-tuning.md)** - Optimization guide
- **[Fixes](fixes/)** - Detailed fix documentation

## Quick Troubleshooting

### Development Environment

**Database connection fails**
```bash
# Check if database is running
make status

# Restart database
make hybrid-down
make hybrid-up
```

**Port already in use**
```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Database

# Kill the process or change ports in .env
```

**Dependencies out of sync**
```bash
# Backend
cd backend && uv sync

# Frontend
cd frontend && npm install
```

### Pipeline Issues

**Annotation updates failing**
- Check logs in admin panel or system_logs table
- Verify API keys in environment variables
- Check rate limiting and retry logic
- Review specific data source documentation

**WebSocket disconnections**
- Verify non-blocking patterns in use
- Check event loop blocking (<5ms target)
- Review thread pool usage for sync operations

### Performance Issues

**Slow API responses**
- Check cache hit rates (should be 75-95%)
- Verify database indexes
- Review query patterns
- Check cache invalidation logic

**High memory usage**
- Monitor cache size (L1 and L2)
- Check for memory leaks in long-running processes
- Review thread pool sizes

## Common Error Messages

### "Event loop is closed"
- Using sync database operations in async context
- Solution: Use thread pools for blocking operations

### "Cache miss on expected hit"
- Cache invalidation may be too aggressive
- Check TTL settings and namespace configuration

### "Gene normalization failed"
- HGNC API may be unavailable
- Check retry logic and fallback mechanisms

## Getting Help

1. **Check Logs**
   - Admin panel: http://localhost:5173/admin/logs
   - Database: `system_logs` table
   - Console output from backend/frontend

2. **Review Documentation**
   - [Features](../features/) - Feature-specific docs
   - [Architecture](../architecture/) - System design
   - [Implementation Notes](../implementation-notes/) - Technical details

3. **Check Status**
   ```bash
   make status  # System health check
   ```

## Related Documentation

- [Developer Guides](../guides/developer/) - Development guides
- [Reference](../reference/) - Technical references
- [Implementation Notes](../implementation-notes/) - Implementation details