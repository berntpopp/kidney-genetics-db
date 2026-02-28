# Common Issues

**Frequently encountered problems and solutions**

## Development Environment Issues

### Database Connection Failures

**Symptom**: `Connection refused` or `could not connect to server`

**Solutions**:
```bash
# Check if database is running
make status

# Restart database
make hybrid-down
make hybrid-up

# Check Docker
docker ps

# Check DATABASE_URL in .env
```

### Port Already in Use

**Symptom**: `Address already in use` on ports 8000, 5173, or 5432

**Solutions**:
```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # Database

# Kill process
kill -9 <PID>

# Or change ports in .env
```

### Dependency Sync Issues

**Symptom**: Import errors, missing modules

**Solutions**:
```bash
# Backend
cd backend && uv sync

# Frontend
cd frontend && rm -rf node_modules package-lock.json && npm install
```

## Pipeline Issues

### Annotation Updates Failing

**Symptom**: Annotation pipeline errors, 0% coverage

**Common Causes**:
1. API rate limiting
2. Network issues
3. Invalid API keys
4. Cache issues

**Solutions**:
```bash
# Check logs
# Admin panel → Logs
# Or backend terminal output

# Clear cache
# Admin panel → Cache Management → Clear

# Verify API keys in .env
NCBI_API_KEY=your_key_here

# Check retry logic is working
# Should see "Retrying..." in logs
```

### WebSocket Disconnections

**Symptom**: Progress updates stop, WebSocket connection lost

**Common Causes**:
1. Event loop blocking
2. Long-running sync operations
3. Memory issues

**Solutions**:
- Check for blocking operations in async code
- Verify thread pools are used for sync DB operations
- Monitor memory usage
- Review recent code changes

See: [Architecture - Non-Blocking Patterns](../architecture/README.md#non-blocking-architecture)

## Performance Issues

### Slow API Responses

**Symptom**: Requests take >1 second

**Diagnostics**:
```bash
# Check cache hit rate
# Should be 75-95%

# Check database indexes
# Admin panel → Database Health

# Monitor query times
# Check logs for slow queries
```

**Solutions**:
- Verify cache is enabled
- Check cache TTL settings
- Review database indexes
- Check for N+1 queries

### High Memory Usage

**Symptom**: System slow, high memory usage

**Common Causes**:
1. Large cache size
2. Memory leaks
3. Too many concurrent requests

**Solutions**:
```bash
# Check cache size
# Admin panel → Cache Statistics

# Clear cache if needed
# Admin panel → Clear Cache

# Restart services
make hybrid-down && make hybrid-up
```

## Database Issues

### Migrations Out of Sync

**Symptom**: Migration errors, schema mismatch

**Solutions**:
```bash
# Check current migration
cd backend && uv run alembic current

# Reset database (CAUTION: Destroys data)
make db-reset

# Or apply missing migrations
cd backend && uv run alembic upgrade head
```

### Data Corruption

**Symptom**: Unexpected null values, invalid data

**Solutions**:
```bash
# Backup first
make db-backup

# Reset and re-import
make db-reset

# Trigger pipeline
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer <token>"
```

## Authentication Issues

### Login Fails

**Symptom**: "Invalid credentials" or 401 errors

**Solutions**:
1. Verify email and password
2. Check user exists in database
3. Verify JWT_SECRET_KEY in .env
4. Check token expiration

```bash
# Create admin user if needed
cd backend
uv run python -m app.scripts.create_admin \
  --email admin@example.com \
  --password secure_password
```

### Token Expiration

**Symptom**: 401 Unauthorized after some time

**Solution**: This is expected - tokens expire for security. Log in again.

## Frontend Issues

### Hot Reload Not Working

**Symptom**: Changes don't appear in browser

**Solutions**:
- Save file (Ctrl+S)
- Hard refresh browser (Ctrl+Shift+R)
- Check browser console for errors
- Restart frontend server

### Build Errors

**Symptom**: Frontend build fails

**Solutions**:
```bash
cd frontend

# Clean and reinstall
rm -rf node_modules package-lock.json dist
npm install

# Check for syntax errors in files
npm run lint
```

## Testing Issues

### Tests Failing

**Symptom**: pytest failures

**Common Causes**:
1. Database not set up
2. Missing test data
3. Changed API contracts

**Solutions**:
```bash
# Run with verbose output
cd backend && uv run pytest -v

# Run specific test
uv run pytest tests/test_specific.py -v

# Check test database
# Should use separate test database
```

## Git Issues

### Merge Conflicts

**Symptom**: Merge conflicts in migrations or dependencies

**Solutions**:
```bash
# For migrations
cd backend
# Keep both migrations, resolve in new migration

# For dependencies
# Backend
uv sync

# Frontend
npm install
```

## Docker Issues

### Container Won't Start

**Symptom**: Docker container exits immediately

**Solutions**:
```bash
# Check logs
docker logs kidney-genetics-db-postgres-1

# Remove volumes and restart
docker-compose down -v
make hybrid-up

# Check disk space
df -h
```

### Permission Errors

**Symptom**: Permission denied on Docker volumes

**Solutions**:
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in

# Check volume permissions
docker volume inspect <volume-name>
```

## Cache Issues

### Stale Data

**Symptom**: Old data showing after updates

**Solutions**:
```bash
# Clear specific namespace
# Admin panel → Cache Management → Clear Namespace

# Clear all cache
# Admin panel → Cache Management → Clear All

# Or via API
curl -X POST http://localhost:8000/api/admin/cache/clear
```

### Cache Misses

**Symptom**: Low cache hit rate (<50%)

**Common Causes**:
1. TTL too short
2. Cache eviction
3. High traffic

**Solutions**:
- Review cache TTL settings
- Increase cache size
- Monitor cache metrics

## Logging Issues

### No Logs Appearing

**Symptom**: Empty log output

**Solutions**:
- Check log level in .env (should be INFO or DEBUG)
- Verify logging is not disabled
- Check database logs table: `system_logs`
- Review unified logger usage

### Too Many Logs

**Symptom**: Excessive logging, log spam

**Solutions**:
- Adjust log level to WARNING or ERROR
- Review verbose debug statements
- Configure log filtering

## Getting More Help

### If Issue Persists

1. **Check Documentation**
   - [Architecture](../architecture/) - System design
   - [Developer Guides](../guides/developer/) - Development guides
   - [Implementation Notes](../implementation-notes/) - Technical details

2. **Search Logs**
   - Backend terminal output
   - Admin panel → Logs
   - Database: `system_logs` table

3. **Check System Status**
   ```bash
   make status
   ```

4. **Create Issue**
   - Include error messages
   - Include steps to reproduce
   - Include relevant logs
   - Include system information

## Prevention Tips

### Best Practices

- ✅ Always use `make` commands
- ✅ Keep dependencies updated
- ✅ Run tests before committing
- ✅ Clear cache after major changes
- ✅ Backup database before migrations
- ✅ Review logs regularly
- ✅ Use unified logging system
- ✅ Follow non-blocking patterns

### Regular Maintenance

```bash
# Weekly
make db-backup          # Backup database
uv sync                 # Update dependencies
npm update             # Update frontend deps

# Before major changes
make db-backup          # Safety backup
make test              # Run tests

# After major changes
make db-reset          # Clean slate
make test              # Verify tests
```

---

**Last Updated**: September 2025
**Maintained By**: Development Team