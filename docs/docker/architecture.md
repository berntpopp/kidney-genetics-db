# Docker Architecture

Technical deep-dive into the Docker architecture for Kidney Genetics Database production deployment.

## Overview

The production deployment uses a sophisticated multi-container architecture with:
- **Multi-stage builds** for minimal image sizes
- **Runtime environment injection** for deployment flexibility
- **NPM integration** for SSL/TLS termination
- **Security hardening** with non-root users
- **WebSocket support** for real-time updates

## Network Topology

### High-Level Architecture

```
Internet
   ↓ (HTTPS)
   ↓
┌──────────────────────────────────────────────┐
│  Nginx Proxy Manager (NPM)                   │
│  - SSL/TLS Termination (Let's Encrypt)       │
│  - Domain routing (db.kidney-genetics.org)   │
│  - WebSocket upgrade handling                │
└──────────────────────────────────────────────┘
   ↓ (HTTP via Docker network)
   ↓
┌─────────────── npm_proxy_network ────────────┐
│  (Shared across all VPS applications)        │
│                                               │
│  ┌─────────────────┐  ┌──────────────────┐  │
│  │  Frontend       │  │  Other Apps      │  │
│  │  (nginx:80)     │  │  (phentrieve...) │  │
│  └────────┬────────┘  └──────────────────┘  │
└───────────┼───────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────┐
│  kidney_genetics_internal_net               │
│  (Isolated application network)             │
│                                              │
│  ┌──────────────┐       ┌─────────────────┐│
│  │  Frontend    │────→  │  Backend        ││
│  │  nginx:80    │       │  FastAPI:8000   ││
│  └──────────────┘       └────────┬────────┘│
│                                   ↓         │
│                          ┌─────────────────┐│
│                          │  PostgreSQL     ││
│                          │  :5432          ││
│                          │  (no external   ││
│                          │   access)       ││
│                          └─────────────────┘│
└──────────────────────────────────────────────┘
```

### Network Details

#### npm_proxy_network
- **Type:** External bridged network
- **Purpose:** Shared across all applications on VPS for NPM access
- **Created once:** `docker network create npm_proxy_network`
- **Containers:** Frontend, Backend, (other VPS apps)
- **Traffic:** HTTP only (HTTPS terminated at NPM)

#### kidney_genetics_internal_net
- **Type:** Isolated bridged network
- **Purpose:** Internal communication between application services
- **Containers:** Frontend, Backend, PostgreSQL
- **Traffic:** Internal HTTP and PostgreSQL protocol
- **Isolation:** Database has NO exposure to npm_proxy_network

### Port Mapping Strategy

#### NPM Mode (Production)
```yaml
# NO EXPOSED PORTS
# NPM connects to containers via Docker network using container names
Frontend:  kidney_genetics_frontend:80  (internal only)
Backend:   kidney_genetics_backend:8000 (internal only)
Database:  kidney_genetics_postgres:5432 (internal only)
```

#### Test Mode (Standalone)
```yaml
# Exposed on non-standard ports to avoid conflicts
Frontend:  localhost:8080 → container:80
Backend:   localhost:8001 → container:8000
Database:  localhost:5433 → container:5432
```

## Container Architecture

### Container Naming Convention

All containers use **underscores** (not dashes) to match phentrieve pattern:
- `kidney_genetics_postgres`
- `kidney_genetics_backend`
- `kidney_genetics_frontend`

**Why underscores?** Nginx proxy configuration works more reliably with underscores in DNS-like container names.

### Container Details

#### PostgreSQL Container
```yaml
Image:    postgres:14-alpine
Purpose:  Persistent data storage
User:     postgres (default Alpine user)
Networks: kidney_genetics_internal_net only
Volume:   kidney_genetics_postgres_data (named volume)
Health:   pg_isready check every 10s
Memory:   ~256-512MB typical usage
```

#### Backend Container
```yaml
Image:    kidney_genetics_backend:latest (custom multi-stage build)
Purpose:  FastAPI REST API + WebSocket server
User:     kidney-api (UID 1000, non-root)
Networks: npm_proxy_network + kidney_genetics_internal_net
Env:      Loaded from .env.production
Health:   HTTP GET /api/health every 30s
Memory:   ~512MB-1GB typical usage
```

#### Frontend Container
```yaml
Image:    kidney_genetics_frontend:latest (custom multi-stage build)
Purpose:  Static Vue.js assets + nginx reverse proxy
User:     nginx (UID 101, non-root)
Networks: npm_proxy_network + kidney_genetics_internal_net
Env:      Runtime injection via docker-entrypoint.sh
Health:   HTTP GET /health every 30s
Memory:   ~50-100MB typical usage
```

## Multi-Stage Build Strategy

### Backend Build Stages

#### Stage 1: Builder
```dockerfile
FROM python:3.11-slim AS builder
- Install system build dependencies (gcc, etc.)
- Install UV package manager (faster than pip)
- Copy pyproject.toml + README.md
- Create virtual environment at /opt/venv
- Install all Python dependencies in venv
Result: ~600MB with all build tools
```

#### Stage 2: Production
```dockerfile
FROM python:3.11-slim AS production
- Install ONLY runtime dependencies (curl for health checks)
- Create non-root user (kidney-api, UID 1000)
- Copy venv from builder stage (dependencies only)
- Copy application code with proper ownership
- Switch to non-root user
- Configure healthcheck
Result: ~450MB (no build tools, only runtime)
```

**Benefit:** 25% smaller image, no unnecessary build tools in production.

### Frontend Build Stages

#### Stage 1: Builder
```dockerfile
FROM node:20-alpine AS builder
- Install Node.js dependencies via npm ci
- Copy source code
- Run Vite production build (minification, tree-shaking)
- Generate static dist/ directory
Result: ~400MB with node_modules + source
```

#### Stage 2: Production
```dockerfile
FROM nginx:1.26-alpine AS production
- Copy ONLY dist/ from builder (static assets)
- Copy nginx.prod.conf (custom configuration)
- Copy docker-entrypoint.sh (runtime env injection)
- Remove default nginx config
- Configure healthcheck
Result: ~60MB (nginx + static assets only, NO node_modules)
```

**Benefit:** 85% smaller image, instant startup (no build process).

## Runtime Environment Injection

### Problem: Vite Build-Time Variables

Traditional Vite approach:
```javascript
// ❌ Build-time only - requires rebuild for different environments
const apiUrl = import.meta.env.VITE_API_URL
```

**Issue:** Each environment (staging, production, etc.) needs separate builds.

### Solution: Window Object Injection

Our approach:
```javascript
// ✅ Runtime - single build for all environments
const apiUrl = window._env_?.API_BASE_URL || '/api'
```

Implementation flow:

1. **Build Time (Vite):**
   ```bash
   npm run build
   # Creates static dist/ with NO hardcoded API URLs
   ```

2. **Container Startup:**
   ```bash
   # docker-entrypoint.sh runs before nginx
   cat > /usr/share/nginx/html/env-config.js <<EOF
   window._env_ = {
     API_BASE_URL: "${API_BASE_URL:-/api}",
     WS_URL: "${WS_URL:-/ws}",
     ENVIRONMENT: "${ENVIRONMENT:-production}"
   };
   EOF
   ```

3. **index.html:**
   ```html
   <head>
     <script src="/env-config.js"></script>  <!-- Loads first -->
     <script src="/assets/index.js"></script> <!-- Accesses window._env_ -->
   </head>
   ```

4. **Vue.js Code:**
   ```javascript
   // frontend/src/config.js
   export const config = {
     apiBaseUrl: window._env_?.API_BASE_URL || '/api',
     // Falls back to Vite env for local development
   };
   ```

**Benefits:**
- Single Docker image for all environments
- Change API URL without rebuilding
- Override via docker-compose environment variables
- Maintains backward compatibility with Vite dev server

## Security Architecture

### Non-Root Users

#### Backend
```dockerfile
RUN groupadd -r -g 1000 kidney-api && \
    useradd -r -u 1000 -g kidney-api -m -s /bin/bash kidney-api
USER kidney-api
```
- UID 1000: Standard first user ID on Linux
- Home directory: /home/kidney-api
- Shell: bash (for debugging if needed)
- Permissions: Can only write to /app directory (owned by user)

#### Frontend
```dockerfile
USER nginx  # Built-in nginx user (UID 101)
```
- Alpine nginx default user
- Minimal permissions
- Can only read static files

### Network Isolation

Security layers:
1. **PostgreSQL:** Only on internal network (no npm_proxy access)
2. **Backend:** On both networks but only accepts connections from frontend
3. **Frontend:** Public-facing but serves only static files
4. **NPM:** SSL/TLS termination keeps internal traffic HTTP

### Docker Security Options

```yaml
security_opt:
  - no-new-privileges:true  # Prevent privilege escalation
cap_drop:
  - ALL  # Drop all capabilities (backend only)
```

### Log Rotation

```yaml
logging:
  driver: json-file
  options:
    max-size: 50m   # Rotate after 50MB
    max-file: "5"   # Keep 5 files (total 250MB max)
```

Prevents disk space exhaustion from logs.

## WebSocket Architecture

### Challenge: Proper Upgrade Handling

WebSocket connections need special header handling:

```
Client (Browser)                    nginx                     Backend
     |                                |                          |
     |-- Upgrade: websocket -------→|                          |
     |   Connection: Upgrade          |                          |
     |                                |-- Upgrade: websocket --→|
     |                                |   Connection: upgrade    |
     |                                |                          |
     |←-------------- 101 Switching Protocols -----------------←|
     |                                |                          |
     |←================== WebSocket Connection ===============→|
```

### Implementation: nginx Map Directive

```nginx
# nginx.prod.conf
map $http_upgrade $connection_upgrade {
    default upgrade;    # If Upgrade header present, set Connection: upgrade
    ''      close;      # If no Upgrade header, set Connection: close
}

location /ws/ {
    proxy_pass http://kidney_genetics_backend:8000/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;  # Use mapped value
    # ...
}
```

**Why map?**
- Regular HTTP requests: Connection header should be "close" or unset
- WebSocket requests: Connection header must be "upgrade"
- Map dynamically sets correct value based on Upgrade header presence

**Without map:** All requests get Connection: upgrade, breaking HTTP keepalive.

## Health Check Strategy

### Backend Health Check
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
  interval: 30s      # Check every 30 seconds
  timeout: 10s       # Fail if no response in 10s
  retries: 3         # Retry 3 times before marking unhealthy
  start_period: 40s  # Grace period for startup
```

Health endpoint returns:
```json
{"status": "ok", "database": "connected"}
```

### Frontend Health Check
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 5s  # nginx starts faster
```

Health endpoint (nginx.prod.conf):
```nginx
location /health {
    access_log off;
    default_type application/json;
    return 200 '{"status":"healthy","service":"kidney_genetics_frontend"}';
}
```

### PostgreSQL Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U kidney_user -d kidney_genetics"]
  interval: 10s   # Check frequently (critical dependency)
  timeout: 5s
  retries: 5
  start_period: 10s
```

### Dependency Chain

```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy  # Wait for DB to be healthy

frontend:
  depends_on:
    backend:
      condition: service_healthy  # Wait for API to be healthy
```

**Startup sequence:** PostgreSQL → Backend → Frontend

## Volume Management

### PostgreSQL Data Volume

```yaml
volumes:
  kidney_genetics_postgres_data:
    name: kidney_genetics_postgres_data  # Named volume (persists across recreates)

services:
  postgres:
    volumes:
      - kidney_genetics_postgres_data:/var/lib/postgresql/data
```

**Properties:**
- **Type:** Named volume (managed by Docker)
- **Location:** `/var/lib/docker/volumes/kidney_genetics_postgres_data/_data`
- **Persistence:** Survives container recreation
- **Backup:** Must be backed up separately (see maintenance docs)

### Why No Bind Mounts?

```yaml
# ❌ NOT USED - Bind mount
volumes:
  - ./data:/var/lib/postgresql/data

# ✅ USED - Named volume
volumes:
  - kidney_genetics_postgres_data:/var/lib/postgresql/data
```

**Reasons:**
- Named volumes have better performance on some systems
- Docker manages permissions automatically
- Easier to backup/restore with docker cp
- Portable across different VPS environments

## Performance Optimizations

### Build Context Optimization (.dockerignore)

Backend .dockerignore:
```
node_modules/
tests/
docs/
*.log
.git/
```
**Result:** Build context reduced from ~50MB to ~5MB (10x smaller transfer).

Frontend .dockerignore:
```
node_modules/     # Don't copy (npm ci will download)
dist/             # Don't copy (build will generate)
tests/
.git/
```
**Result:** Build context reduced from ~100MB to ~2MB (50x smaller transfer).

### Layer Caching Strategy

```dockerfile
# ✅ Copy dependencies first (changes rarely)
COPY package*.json ./
RUN npm ci

# ✅ Copy source code last (changes frequently)
COPY . .
RUN npm run build
```

**Benefit:** Dependency installation cached unless package files change.

### Nginx Compression

```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.api+json;
gzip_min_length 1000;
gzip_comp_level 6;
gzip_vary on;
```

**Result:** 70-80% size reduction for text assets (CSS, JS, JSON).

## Comparison: Development vs Production

| Feature | Development | Production |
|---------|------------|------------|
| **Docker Compose** | docker-compose.yml | docker-compose.prod.yml |
| **Build Strategy** | Simple Dockerfile | Multi-stage builds |
| **Hot Reload** | ✅ Yes (volume mounts) | ❌ No (static build) |
| **Image Size** | Not optimized (~1GB+) | Optimized (~510MB total) |
| **Networks** | Single default network | Two isolated networks |
| **Ports** | Exposed (5432, 8000, 5173) | None (NPM proxies) |
| **SSL/TLS** | ❌ HTTP only | ✅ HTTPS via NPM |
| **User** | root (for ease) | non-root (security) |
| **Healthchecks** | Optional | ✅ Required |
| **Environment** | .env (simple) | .env.production (secured) |
| **Startup Time** | ~10-30s | ~30-60s (healthchecks) |

## Design Decisions

### Why Multi-Stage Builds?

**Alternative:** Single-stage build with all dependencies.

**Chosen:** Multi-stage to minimize attack surface.

**Trade-off:** Slightly longer build time (2x stages) vs. 50%+ smaller images.

### Why Runtime Env Injection?

**Alternative:** Build separate images per environment.

**Chosen:** Single image with runtime configuration.

**Trade-off:** Slight complexity (docker-entrypoint.sh) vs. massive CI/CD simplification.

### Why NPM Instead of Traefik/Caddy?

**Alternative:** Traefik for automatic service discovery, Caddy for simplicity.

**Chosen:** NPM for user-friendly GUI and proven multi-app VPS setup.

**Trade-off:** GUI overhead vs. easier management for non-Docker-experts.

### Why Container Name Underscores?

**Alternative:** Use dashes (kidney-genetics-backend).

**Chosen:** Underscores for DNS compatibility and pattern consistency.

**Trade-off:** Slightly unusual naming vs. avoiding nginx proxy edge cases.

## Related Documentation

- [Production Deployment](production-deployment.md) - Step-by-step setup
- [Dockerfile Reference](dockerfile-reference.md) - Build configuration details
- [Troubleshooting](troubleshooting.md) - Common issues
- [README](README.md) - Documentation index
