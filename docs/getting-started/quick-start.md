# Quick Start Guide

**Get the Kidney Genetics Database running in 5 minutes**

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.11+ installed (`python --version`)
- ✅ Node.js 18+ installed (`node --version`)
- ✅ Docker Desktop running (`docker ps`)
- ✅ Make installed (`make --version`)

## Step 1: Clone and Navigate

```bash
git clone <repository-url>
cd kidney-genetics-db
```

## Step 2: Start Development Environment

We recommend **hybrid mode** (database in Docker, services local):

```bash
make hybrid-up
```

This command:
- ✅ Starts PostgreSQL in Docker
- ✅ Creates database schema
- ✅ Seeds initial data
- ⏱️ Takes ~30 seconds

## Step 3: Start Backend (New Terminal)

```bash
make backend
```

Backend will start at: **http://localhost:8000**

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

## Step 4: Start Frontend (New Terminal)

```bash
make frontend
```

Frontend will start at: **http://localhost:5173**

Expected output:
```
  VITE ready in 284 ms
  ➜  Local:   http://localhost:5173/
```

## Step 5: Verify Installation

### Check Frontend
1. Open http://localhost:5173
2. You should see the gene list page
3. Try searching for "PKD1"

### Check Backend API
1. Open http://localhost:8000/docs
2. You should see Swagger UI
3. Try the `/api/genes` endpoint

### Check Database
```bash
make status
```

Expected: All services running ✅

## You're Ready! 🎉

### What's Next?

#### Explore the Interface
- **Gene List**: http://localhost:5173
- **Admin Panel**: http://localhost:5173/admin
- **API Docs**: http://localhost:8000/docs

#### Common Tasks

**Stop Services**
```bash
# In backend/frontend terminals: Ctrl+C
make hybrid-down  # Stop database
```

**Reset Database**
```bash
make db-reset
```

**View Logs**
```bash
# Backend: Check terminal output
# Frontend: Check terminal output
# Database: Admin panel → Logs
```

## Troubleshooting

### Port Already in Use

**Error**: "Address already in use"

**Solution**:
```bash
# Find and kill process
lsof -i :8000   # Backend
lsof -i :5173   # Frontend
lsof -i :5432   # Database

# Or change ports in .env
```

### Database Connection Failed

**Error**: "Connection refused"

**Solution**:
```bash
# Check if database is running
make status

# Restart
make hybrid-down
make hybrid-up
```

### Dependencies Out of Sync

**Error**: Import errors or missing packages

**Solution**:
```bash
# Backend
cd backend && uv sync

# Frontend
cd frontend && npm install
```

## Alternative: Full Docker Mode

If you prefer everything in Docker:

```bash
make dev-up
```

Access:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

Stop:
```bash
make dev-down
```

## Next Steps

1. **[Installation Guide](installation.md)** - Detailed environment setup
2. **[Development Workflow](development-workflow.md)** - Day-to-day development
3. **[Developer Guides](../guides/developer/)** - Comprehensive development docs
4. **[Architecture](../architecture/)** - Understand the system

## Quick Reference

| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:5173 | 5173 |
| Backend | http://localhost:8000 | 8000 |
| API Docs | http://localhost:8000/docs | 8000 |
| Database | localhost | 5432 |

## Support

Having issues? Check:
- [Troubleshooting Guide](../troubleshooting/common-issues.md)
- [Developer Guides](../guides/developer/)
- Project repository issues

---

**Time to Complete**: ~5 minutes
**Difficulty**: Beginner
**Last Updated**: September 2025