# Docker Documentation

Complete guide to Docker-based deployment for the Kidney Genetics Database.

## Overview

This project uses Docker for production deployment with a sophisticated multi-stage build strategy, runtime environment injection, and integration with Nginx Proxy Manager (NPM) for SSL/TLS termination.

**Production Domain:** [db.kidney-genetics.org](https://db.kidney-genetics.org)

## Quick Links

- **[Production Deployment Guide](production-deployment.md)** - Step-by-step deployment to VPS with NPM
- **[Docker Architecture](architecture.md)** - System design and network topology
- **[Dockerfile Reference](dockerfile-reference.md)** - Deep dive into multi-stage builds
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

## Key Features

### 1. Multi-Stage Builds
- **Backend**: Python 3.11 with UV package manager
- **Frontend**: Node 20 build + nginx 1.26 production
- Minimal image sizes with security hardening

### 2. Runtime Environment Injection
- Build once, deploy anywhere pattern for Vue.js frontend
- Environment variables injected at container startup
- No rebuild needed for different environments

### 3. NPM Integration
- Automatic SSL/TLS via Let's Encrypt
- Shared network topology for multi-app VPS
- No exposed ports (NPM connects via container names)

### 4. Security Features
- Non-root users (UID 1000 for backend, nginx user for frontend)
- Minimal attack surface with multi-stage builds
- Security headers in nginx configuration
- No unnecessary capabilities

### 5. WebSocket Support
- Proper Connection header handling via nginx map
- Real-time progress updates during data pipeline operations
- Graceful fallback for non-WebSocket requests

## Production Files

```
kidney-genetics-db/
├── docker-compose.prod.yml         # NPM mode (no exposed ports)
├── docker-compose.prod.test.yml    # Test mode (standalone with ports)
├── .env.production                 # Production secrets (git-ignored)
├── .env.production.example         # Environment template
├── backend/
│   ├── Dockerfile                  # Multi-stage Python build
│   └── .dockerignore              # Build context optimization
└── frontend/
    ├── Dockerfile                  # Multi-stage Node + nginx build
    ├── .dockerignore              # Build context optimization
    ├── nginx.prod.conf            # Production nginx config
    ├── docker-entrypoint.sh       # Runtime env injection script
    └── src/config.js              # Runtime config accessor
```

## Deployment Modes

### NPM Mode (Production)
```bash
make prod-build    # Build images
make prod-up       # Start services (no ports exposed)
make prod-logs     # View logs
make prod-health   # Check service health
make prod-down     # Stop services
```

**Requirements:**
- Nginx Proxy Manager running
- `npm_proxy_network` Docker network exists
- DNS pointing to VPS

### Test Mode (Standalone)
```bash
make prod-test-up      # Start with exposed ports
make prod-test-health  # Check health
make prod-test-down    # Stop services
```

**Access:**
- Frontend: http://localhost:8080
- Backend API: http://localhost:8001/api/health
- Database: localhost:5433

### Network Management
```bash
make npm-network-create    # Create shared network
make npm-network-check     # Verify network exists
```

## Development vs Production

| Aspect | Development | Production |
|--------|------------|------------|
| **Mode** | Hybrid (DB in Docker, API/Frontend local) | Full Docker with NPM |
| **Ports** | Exposed (5432, 8000, 5173) | None (NPM proxies) |
| **SSL/TLS** | None (HTTP only) | Let's Encrypt via NPM |
| **Build** | Hot reload with volumes | Optimized multi-stage |
| **Environment** | .env files | .env.production |
| **Commands** | `make hybrid-up`, `make backend`, `make frontend` | `make prod-up` |

## Architecture Highlights

### Network Topology
```
Internet → NPM (SSL termination) → npm_proxy_network
                                       ↓
                   ┌──────────────────┼──────────────────┐
                   ↓                  ↓                  ↓
            Frontend:80         Backend:8000      (Other Apps)
                   ↓
          kidney_genetics_internal_net
                   ↓
             PostgreSQL:5432 (isolated)
```

### Container Names (with underscores)
- `kidney_genetics_postgres` - PostgreSQL 14 database
- `kidney_genetics_backend` - FastAPI application
- `kidney_genetics_frontend` - Vue.js + nginx

**Note:** Container names use underscores to match the phentrieve pattern and avoid nginx proxy issues.

## Environment Variables

### Critical Variables (.env.production)
```bash
# Database
POSTGRES_PASSWORD=<generate with: openssl rand -base64 32>
DATABASE_URL=postgresql://kidney_user:PASSWORD@kidney_genetics_postgres:5432/kidney_genetics

# Backend
SECRET_KEY=<generate with: openssl rand -hex 32>
DOMAIN=db.kidney-genetics.org
ALLOWED_HOSTS=localhost,db.kidney-genetics.org

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Frontend Runtime Variables
```bash
API_BASE_URL=/api          # Backend API path
WS_URL=/ws                 # WebSocket path
ENVIRONMENT=production     # Environment identifier
```

## Security Best Practices

1. **Never commit .env.production** (git-ignored by default)
2. **Generate strong secrets** using openssl
3. **Keep images updated** (rebuild regularly)
4. **Monitor logs** via `make prod-logs`
5. **Use non-root users** (already configured)
6. **Enable log rotation** (50MB max, 5 files)

## Performance

### Image Sizes
- **Backend**: ~450MB (multi-stage build with dependencies)
- **Frontend**: ~60MB (nginx + static assets only)
- **PostgreSQL**: ~250MB (Alpine base)

### Build Times
- **Backend**: ~3-5 minutes (cold build with UV)
- **Frontend**: ~2-3 minutes (npm ci + Vite build)
- **Cached builds**: <30 seconds

### Resource Usage (Typical)
- **Backend**: 512MB-1GB RAM, 0.5-1 CPU
- **Frontend**: 50-100MB RAM, 0.1-0.2 CPU
- **PostgreSQL**: 256-512MB RAM, 0.2-0.5 CPU

## Common Commands

### Health Checks
```bash
# Production health
make prod-health

# Test mode health
make prod-test-health

# Manual checks
docker ps --filter "name=kidney_genetics"
curl http://localhost:8001/api/health  # Test mode only
```

### Logs
```bash
# All services
make prod-logs

# Specific service
docker logs kidney_genetics_backend -f
docker logs kidney_genetics_frontend -f
docker logs kidney_genetics_postgres -f
```

### Restart Services
```bash
# Restart all
make prod-restart

# Restart specific service
docker restart kidney_genetics_backend
```

### Cleanup
```bash
# Stop and remove containers
make prod-down

# Remove images
docker rmi kidney_genetics_backend:latest
docker rmi kidney_genetics_frontend:latest

# Full cleanup (DANGER: removes volumes!)
docker compose -f docker-compose.prod.yml down -v
```

## Maintenance

### Update Application Code
```bash
# Pull latest code
git pull origin main

# Rebuild images
make prod-build

# Recreate containers
make prod-down
make prod-up

# Verify health
make prod-health
```

### Database Backups
```bash
# Backup (run on VPS)
docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user kidney_genetics > backup_$(date +%Y%m%d).sql

# Restore (run on VPS)
docker exec -i kidney_genetics_postgres psql \
  -U kidney_user kidney_genetics < backup_20251010.sql
```

### View Database
```bash
# Connect to PostgreSQL (production)
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics

# Common queries
\dt                    # List tables
\d+ genes             # Describe genes table
SELECT COUNT(*) FROM genes;
```

## Next Steps

- **New to Docker deployment?** Start with [Production Deployment Guide](production-deployment.md)
- **Want to understand the architecture?** Read [Docker Architecture](architecture.md)
- **Dockerfile details?** Check [Dockerfile Reference](dockerfile-reference.md)
- **Having issues?** See [Troubleshooting](troubleshooting.md)

## Related Documentation

- [Getting Started](../getting-started/quick-start.md) - Local development setup
- [Architecture Overview](../architecture/README.md) - Application architecture
- [Deployment Guide](../guides/deployment/vps-deployment.md) - General deployment info

## Support

For issues or questions:
- Check [Troubleshooting](troubleshooting.md)
- Review [GitHub Issues](https://github.com/bernt-popp/kidney-genetics-db/issues)
- Consult CLAUDE.md for development patterns
