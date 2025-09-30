# Development Workflow

**Day-to-day development guide for the Kidney Genetics Database**

## Daily Workflow

### Starting Your Day

```bash
# 1. Pull latest changes
git pull origin main

# 2. Start development environment
make hybrid-up

# 3. Start backend (Terminal 1)
make backend

# 4. Start frontend (Terminal 2)
make frontend

# 5. Verify everything is running
make status
```

### During Development

**Backend Changes**:
- Hot reload automatic with Uvicorn
- Check logs in backend terminal
- Test endpoints at http://localhost:8000/docs

**Frontend Changes**:
- Hot reload automatic with Vite
- Check logs in frontend terminal
- View changes at http://localhost:5173

**Database Changes**:
- Create migration: `cd backend && uv run alembic revision --autogenerate -m "Description"`
- Apply migration: `make db-reset` or `uv run alembic upgrade head`

### Ending Your Day

```bash
# 1. Stop services (Ctrl+C in each terminal)
# 2. Stop database
make hybrid-down

# 3. Commit your work (see Git Workflow below)
```

## Git Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch (if used)
- `feature/*` - New features
- `fix/*` - Bug fixes
- `refactor/*` - Code refactoring

### Creating a Feature

```bash
# Create feature branch
git checkout -b feature/add-export-functionality

# Make changes
# ... code ...

# Stage changes
git add .

# Commit (following commit conventions)
git commit -m "feat: Add CSV export functionality"

# Push to remote
git push origin feature/add-export-functionality

# Create pull request on GitHub
```

### Commit Message Conventions

We follow Conventional Commits:

```bash
feat: Add new feature
fix: Fix bug
refactor: Refactor code
docs: Update documentation
test: Add or update tests
chore: Maintenance tasks
perf: Performance improvement
style: Code style changes (formatting, etc.)
```

**Examples**:
```bash
git commit -m "feat: Add user export to CSV"
git commit -m "fix: Resolve caching issue in annotation pipeline"
git commit -m "refactor: Simplify evidence scoring calculation"
git commit -m "docs: Update API documentation"
```

## Code Quality Checks

### Before Committing

```bash
# Backend linting
make lint

# Run tests
make test

# Check type hints (if configured)
cd backend && uv run mypy app/
```

### Pre-commit Hooks

Install pre-commit hooks (recommended):

```bash
pip install pre-commit
pre-commit install
```

This will automatically:
- Run linters
- Format code
- Check for issues

## Testing Workflow

### Running Tests

```bash
# All tests
make test

# Specific test file
cd backend && uv run pytest tests/test_gene_normalization.py

# With coverage
cd backend && uv run pytest --cov=app tests/

# Verbose output
cd backend && uv run pytest -v
```

### Writing Tests

Place tests in `backend/tests/`:

```python
# tests/test_new_feature.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_new_endpoint():
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200
    assert "expected_key" in response.json()
```

## Database Workflow

### Creating Migrations

```bash
cd backend

# Auto-generate migration
uv run alembic revision --autogenerate -m "Add new column to genes table"

# Review generated migration in backend/alembic/versions/

# Apply migration
uv run alembic upgrade head

# Or use make command
make db-reset  # Complete reset with migrations
```

### Migration Best Practices

- ✅ Review auto-generated migrations
- ✅ Test migrations on dev database
- ✅ Include both upgrade and downgrade
- ✅ Use descriptive migration messages
- ❌ Don't modify existing migrations
- ❌ Don't skip migration review

### Database Operations

```bash
# Reset database completely
make db-reset

# Clean data only (keep schema)
make db-clean

# Backup database
make db-backup

# Check database status
make status
```

## Debugging

### Backend Debugging

#### Using VSCode

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

#### Using Print Debugging

**Don't** use `print()` - use unified logger:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
await logger.debug("Debug message", variable=value)
```

### Frontend Debugging

#### Browser DevTools
- Open: F12 or Ctrl+Shift+I
- Console: View errors and logs
- Network: Monitor API calls
- Vue DevTools: Install browser extension

#### Vue DevTools

Install: https://devtools.vuejs.org/

Features:
- Component inspector
- State management (Pinia)
- Event tracking
- Performance profiling

## Performance Monitoring

### Backend Performance

```python
from app.core.logging import timed_operation

@timed_operation(warning_threshold_ms=1000)
async def slow_operation():
    # Automatically logs if >1000ms
    result = await expensive_computation()
    return result
```

### Monitoring Cache Performance

Check cache hit rates in logs:

```bash
# Search for cache-related logs
cd backend
grep "cache_hit" logs/app.log
```

### Database Query Performance

```python
# Enable SQL logging (development only)
# In app/core/config.py
ECHO_SQL = True  # Shows all SQL queries
```

## Common Tasks

### Adding a New Annotation Source

1. Create source class in `backend/app/pipeline/sources/unified/`
2. Extend `BaseAnnotationSource`
3. Implement required methods
4. Add to source registry
5. Update documentation

See: [Developer Guides](../guides/developer/) for detailed steps

### Adding a New API Endpoint

1. Create endpoint in `backend/app/api/endpoints/`
2. Add route to router
3. Create schema in `backend/app/schemas/`
4. Add CRUD operations in `backend/app/crud/`
5. Update API documentation

### Updating the Frontend

1. Create/modify component in `frontend/src/components/`
2. Update route in `frontend/src/router/`
3. Update Pinia store if needed in `frontend/src/stores/`
4. Test in browser
5. Update documentation

## Environment Management

### Switching Environments

```bash
# Development (default)
cp .env.development .env

# Testing
cp .env.test .env

# Production (when ready)
cp .env.production .env
```

### Managing Dependencies

**Backend** (UV):
```bash
cd backend

# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Update dependencies
uv sync

# Lock dependencies
uv lock
```

**Frontend** (npm):
```bash
cd frontend

# Add dependency
npm install package-name

# Add dev dependency
npm install --save-dev package-name

# Update dependencies
npm update

# Check for outdated
npm outdated
```

## Collaboration

### Code Review Checklist

**For Authors**:
- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Documentation updated
- [ ] Migration included (if needed)
- [ ] No sensitive data committed
- [ ] Follows code style guide

**For Reviewers**:
- [ ] Code follows DRY principles
- [ ] Uses unified systems (logging, cache, retry)
- [ ] No blocking operations in async context
- [ ] Proper error handling
- [ ] Tests cover new code
- [ ] Documentation is clear

### Pair Programming

Use VSCode Live Share for remote pair programming:

```bash
# Install Live Share extension
code --install-extension ms-vsliveshare.vsliveshare
```

## Troubleshooting Development Issues

### Hot Reload Not Working

**Backend**:
- Check Uvicorn is running with `--reload`
- Verify file is saved
- Check syntax errors in terminal

**Frontend**:
- Check Vite is running
- Clear browser cache (Ctrl+Shift+R)
- Check browser console for errors

### Import Errors

**Backend**:
```bash
cd backend
uv sync  # Reinstall dependencies
```

**Frontend**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Database Out of Sync

```bash
# Check migration status
cd backend
uv run alembic current

# Reset to clean state
make db-reset
```

## Best Practices

### DO ✅

- Use unified logging system
- Use cache service for all caching
- Use retry logic for external APIs
- Write descriptive commit messages
- Test before committing
- Update documentation
- Use thread pools for blocking operations
- Follow code style guide

### DON'T ❌

- Use `print()` for logging
- Create custom cache implementations
- Write custom retry loops
- Commit directly to main
- Skip code review
- Block the event loop
- Ignore linting errors
- Hardcode configuration

## Resources

- **[Developer Guides](../guides/developer/)** - Comprehensive guides
- **[Architecture](../architecture/)** - System design
- **[API Documentation](../api/)** - API reference
- **[Troubleshooting](../troubleshooting/)** - Common issues
- **[CLAUDE.md](../../CLAUDE.md)** - Complete guidelines

## Quick Reference

### Most Used Commands

```bash
make hybrid-up        # Start database
make backend          # Start backend
make frontend         # Start frontend
make status           # Check status
make db-reset         # Reset database
make lint             # Lint backend
make test             # Run tests
make hybrid-down      # Stop database
```

### URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Admin Panel | http://localhost:5173/admin |

---

**Difficulty**: Intermediate
**Last Updated**: September 2025
**Maintained By**: Development Team