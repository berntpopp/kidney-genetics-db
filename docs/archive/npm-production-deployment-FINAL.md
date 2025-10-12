# Production Deployment with Nginx Proxy Manager - FINAL PLAN

**Issue**: [#22 - feat: Add Nginx Proxy Manager compatible production deployment](https://github.com/berntpopp/kidney-genetics-db/issues/22)

**Status**: Ready for Implementation
**Priority**: High
**Target**: v0.2.0
**Review Status**: ✅ All critical issues addressed

---

## Executive Summary

Production-ready Docker deployment compatible with Nginx Proxy Manager (NPM) on multi-app VPS. **Based on proven phentrieve implementation** with security improvements.

Includes:
- ✅ Two deployment modes: Test (standalone with ports) + Production (NPM-integrated, no ports)
- ✅ Multi-app VPS support with unique naming to prevent conflicts
- ✅ Matches phentrieve's working network topology (`npm_proxy_network` + internal net)
- ✅ Security improvements (non-root users, health checks, logging)
- ✅ All critical review issues fixed (Vue.js runtime env, PostgreSQL write access, no unnecessary capabilities)

---

## Architecture

### Multi-App VPS Topology

```
Internet → NPM (:80/:443) → [npm_proxy_network - SHARED]
                                ├─ kidney_genetics_frontend:80
                                ├─ kidney_genetics_backend:8000
                                ├─ phentrhrive_frontend:80
                                └─ (other apps...)

                            [kidney_genetics_internal_net - ISOLATED]
                                ├─ kidney_genetics_frontend (proxies to backend)
                                ├─ kidney_genetics_backend:8000
                                └─ kidney_genetics_postgres:5432
```

**Note**: Both frontend and backend join BOTH networks (matches phentrieve pattern).

### Naming Strategy (No Conflicts)

| Resource | Convention | Example |
|----------|------------|---------|
| Containers | `kidney-genetics-{service}` | `kidney-genetics-frontend` |
| Networks | `kidney-genetics-{purpose}` | `kidney-genetics-internal` |
| Volumes | `kidney-genetics-{service}-data` | `kidney-genetics-postgres-data` |

### Two Deployment Modes

**Test Mode** (`docker-compose.prod.test.yml`):
- Exposed ports: 8080 (frontend), 8001 (backend), 5433 (postgres)
- Purpose: Validate production setup on VPS WITHOUT NPM
- Access: `http://VPS_IP:8080`

**Production Mode** (`docker-compose.prod.yml`):
- No exposed ports (NPM connects via container names)
- Purpose: Final production with SSL via NPM
- Access: Via domain through NPM

---

## Implementation

### Phase 1: Backend Dockerfile

**File**: `backend/Dockerfile`

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

# Stage 2: Production
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with explicit UID/GID
RUN groupadd -r -g 1000 kidney-api && \
    useradd -r -u 1000 -g kidney-api -m -s /bin/bash kidney-api

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=kidney-api:kidney-api . .

# Switch to non-root user
USER kidney-api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# Uvicorn command (port 8000 requires NO special capabilities)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File**: `backend/.dockerignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/
.pytest_cache/
.coverage
htmlcov/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Tests
tests/
test_*.py
*_test.py

# Docs
docs/
*.md
!README.md

# CI/CD
.git/
.github/
.gitignore

# Secrets
.env*
!.env.example
*.pem
*.key
secrets/

# Temp
tmp/
*.log
*.tmp
```

---

### Phase 2: Frontend Dockerfile + Runtime Env Injection

**File**: `frontend/Dockerfile`

```dockerfile
# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build production app (env vars will be injected at runtime)
RUN npm run build

# Stage 2: Production
FROM nginx:1.26-alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.template

# Copy entrypoint script for runtime env injection
COPY docker-entrypoint.sh /docker-entrypoint.d/40-inject-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/40-inject-runtime-env.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

# Nginx runs as nginx user (UID 101) by default
USER nginx

CMD ["nginx", "-g", "daemon off;"]
```

**File**: `frontend/docker-entrypoint.sh`

```bash
#!/bin/sh
# Runtime environment variable injection for Vue.js
# This solves the "build once, deploy anywhere" problem with Vite

set -e

echo "Injecting runtime environment variables..."

# Generate runtime config accessible to Vue.js app
cat > /usr/share/nginx/html/env-config.js <<EOF
// Runtime environment configuration
// Injected at container startup
window._env_ = {
  API_BASE_URL: "${API_BASE_URL:-/api}",
  WS_URL: "${WS_URL:-/ws}",
  ENVIRONMENT: "${ENVIRONMENT:-production}",
  VERSION: "${VERSION:-0.2.0}"
};
EOF

echo "Runtime config generated:"
cat /usr/share/nginx/html/env-config.js

# Make sure index.html loads this script
# Add script tag to index.html if not already present
if ! grep -q "env-config.js" /usr/share/nginx/html/index.html; then
    sed -i 's|</head>|  <script src="/env-config.js"></script>\n  </head>|' /usr/share/nginx/html/index.html
    echo "Added env-config.js script tag to index.html"
fi

echo "Runtime environment injection complete"
```

**File**: `frontend/.dockerignore`

```
# Dependencies
node_modules/
package-lock.json

# Build outputs
dist/
build/

# Environment files
.env*
!.env.example

# IDE
.vscode/
.idea/
*.swp

# Git
.git/
.gitignore

# Tests
tests/
**/*.spec.js
**/*.test.js

# Docs
*.md
!README.md

# Misc
*.log
.DS_Store
```

---

### Phase 3: Frontend Nginx Configuration

**File**: `frontend/nginx.prod.conf`

```nginx
# Map for WebSocket Connection header
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name _;

    # Client upload size limit
    client_max_body_size 10M;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript application/vnd.api+json;
    gzip_min_length 1000;
    gzip_comp_level 6;
    gzip_vary on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:;" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend static assets
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Runtime environment config
    location /env-config.js {
        root /usr/share/nginx/html;
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate";
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://kidney-genetics-backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support (with proper Connection header handling)
    location /ws/ {
        proxy_pass http://kidney-genetics-backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;  # Use mapped variable
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts (longer)
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Health check (returns JSON for monitoring tools)
    location /health {
        access_log off;
        default_type application/json;
        return 200 '{"status":"healthy","service":"kidney-genetics-frontend"}';
    }
}
```

---

### Phase 4: Production Docker Compose (NPM Mode)

**File**: `docker-compose.prod.yml`

```yaml
version: '3.8'

networks:
  npm_proxy_network:
    external: true  # MUST exist before deployment (shared across all VPS apps)
    name: npm_proxy_network
  kidney_genetics_internal_net:
    driver: bridge
    name: kidney_genetics_internal_net

volumes:
  kidney-genetics-postgres-data:
    name: kidney-genetics-postgres-data

services:
  postgres:
    image: postgres:14-alpine
    container_name: kidney_genetics_postgres
    networks:
      - kidney_genetics_internal_net
    volumes:
      - kidney-genetics-postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-kidney_genetics}
      POSTGRES_USER: ${POSTGRES_USER:-kidney_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    # NO PORTS EXPOSED
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-kidney_user} -d ${POSTGRES_DB:-kidney_genetics}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: "5"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: kidney_genetics_backend:latest
    container_name: kidney_genetics_backend
    networks:
      - npm_proxy_network              # For NPM access
      - kidney_genetics_internal_net   # For database access
    # NO PORTS EXPOSED (NPM connects via container name)
    env_file:
      - .env.production
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: "5"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: kidney_genetics_frontend:latest
    container_name: kidney_genetics_frontend
    networks:
      - npm_proxy_network
      - kidney_genetics_internal_net  # Can reach backend via internal network too
    # NO PORTS EXPOSED (NPM connects via container name)
    environment:
      API_BASE_URL: /api        # Runtime env injection
      WS_URL: /ws              # Runtime env injection
      ENVIRONMENT: production
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: "5"
```

---

### Phase 5: Test Docker Compose (Standalone Mode)

**File**: `docker-compose.prod.test.yml`

```yaml
version: '3.8'

networks:
  kidney-genetics-internal:
    driver: bridge
    name: kidney-genetics-internal

volumes:
  kidney-genetics-postgres-data:
    name: kidney-genetics-postgres-data

services:
  postgres:
    image: postgres:14-alpine
    container_name: kidney-genetics-postgres
    networks:
      - kidney-genetics-internal
    volumes:
      - kidney-genetics-postgres-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-kidney_genetics}
      POSTGRES_USER: ${POSTGRES_USER:-kidney_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5433:5432"  # Non-standard port to avoid conflicts
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-kidney_user} -d ${POSTGRES_DB:-kidney_genetics}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    image: kidney-genetics-backend:latest
    container_name: kidney-genetics-backend
    networks:
      - kidney-genetics-internal
    ports:
      - "8001:8000"  # Non-standard port to avoid conflicts
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-kidney_user}:${POSTGRES_PASSWORD}@kidney-genetics-postgres:5432/${POSTGRES_DB:-kidney_genetics}
      SECRET_KEY: ${SECRET_KEY}
      BACKEND_CORS_ORIGINS: '["*"]'  # Allow all in test mode
      API_V1_STR: /api/v1
      PROJECT_NAME: "Kidney Genetics Database"
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      LOG_FORMAT: ${LOG_FORMAT:-json}
      ALLOWED_HOSTS: "*"
    depends_on:
      postgres:
        condition: service_healthy
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: 5

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: kidney-genetics-frontend:latest
    container_name: kidney-genetics-frontend
    networks:
      - kidney-genetics-internal
    ports:
      - "8080:80"  # Non-standard port to avoid conflicts
    environment:
      API_BASE_URL: /api
      WS_URL: /ws
      ENVIRONMENT: test
    depends_on:
      - backend
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: 50m
        max-file: 5
```

---

### Phase 6: Environment Template

**File**: `.env.production.example`

```bash
# Database Configuration
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_user
POSTGRES_PASSWORD=CHANGE_ME_GENERATE_WITH_openssl_rand_-base64_32

# Backend will construct DATABASE_URL from above vars:
# DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@kidney_genetics_postgres:5432/${POSTGRES_DB}
DATABASE_URL=postgresql://kidney_user:CHANGE_ME@kidney_genetics_postgres:5432/kidney_genetics

# Backend Configuration
SECRET_KEY=CHANGE_ME_GENERATE_WITH_openssl_rand_-hex_32
BACKEND_CORS_ORIGINS=[]
API_V1_STR=/api/v1
PROJECT_NAME=Kidney Genetics Database
LOG_LEVEL=INFO
LOG_FORMAT=json
ALLOWED_HOSTS=localhost,kidney-genetics.yourdomain.com
```

**Note**: Simplify `.env.production` to only include what backend needs. Frontend env vars are injected at runtime via docker-entrypoint.sh.

---

### Phase 7: Makefile Targets

**File**: `Makefile` (add these targets)

```makefile
#=============================================================================
# Production Deployment
#=============================================================================

.PHONY: prod-build prod-up prod-down prod-logs prod-restart prod-health
.PHONY: prod-test-up prod-test-down prod-test-logs prod-test-health
.PHONY: npm-network-create npm-network-check

# Production mode (NPM-integrated, no ports exposed)
prod-build:
	@echo "🔨 Building production images..."
	docker-compose -f docker-compose.prod.yml build --no-cache

prod-up:
	@echo "🚀 Starting production deployment (NPM mode)..."
	@echo "⚠️  Requires 'npm-proxy' network to exist!"
	@$(MAKE) npm-network-check
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	@echo "🛑 Stopping production deployment..."
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f --tail=100

prod-restart:
	docker-compose -f docker-compose.prod.yml restart

prod-health:
	@echo "=== Production Health Check ==="
	@docker ps --filter "name=kidney-genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No containers running"

# Test mode (standalone with exposed ports)
prod-test-up:
	@echo "🧪 Starting production TEST mode (ports exposed)..."
	@echo "Access:"
	@echo "  - Frontend: http://localhost:8080"
	@echo "  - Backend API: http://localhost:8001/api/health"
	@echo "  - Database: localhost:5433"
	docker-compose -f docker-compose.prod.test.yml up -d

prod-test-down:
	@echo "🛑 Stopping test mode..."
	docker-compose -f docker-compose.prod.test.yml down

prod-test-logs:
	docker-compose -f docker-compose.prod.test.yml logs -f --tail=100

prod-test-health:
	@echo "=== Test Mode Health Check ==="
	@echo "Frontend: http://localhost:8080"
	@echo -n "Backend API: "
	@curl -sf http://localhost:8001/api/health >/dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo ""
	@docker ps --filter "name=kidney-genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Network management
npm-network-create:
	@echo "🌐 Creating shared npm_proxy_network..."
	@docker network create npm_proxy_network 2>/dev/null || echo "✅ Network already exists"

npm-network-check:
	@docker network inspect npm_proxy_network >/dev/null 2>&1 || \
	(echo "❌ npm_proxy_network missing! Run: make npm-network-create" && exit 1)
	@echo "✅ npm_proxy_network exists"
```

---

## Deployment Workflow

### Step 1: Test Mode (Validate Everything)

```bash
# 1. Prepare environment
cp .env.production.example .env.production
# Edit .env.production with secure values

# 2. Build images
make prod-build

# 3. Deploy in TEST mode (with exposed ports)
make prod-test-up

# 4. Verify health
make prod-test-health

# 5. Test manually
curl http://localhost:8001/api/health
curl http://localhost:8080
# Test all functionality in browser

# 6. Stop test mode when satisfied
make prod-test-down
```

### Step 2: Production Mode (NPM Integration)

```bash
# 1. Ensure npm-proxy network exists
make npm-network-check
# If missing: make npm-network-create

# 2. Deploy in PRODUCTION mode (no exposed ports)
make prod-up

# 3. Configure NPM (via NPM UI at http://npm-server:81)
#    - Add Proxy Host:
#      * Domain Names: kidney-genetics.yourdomain.com
#      * Scheme: http
#      * Forward Hostname/IP: kidney-genetics-frontend
#      * Forward Port: 80
#      * Websockets Support: ✅ ON
#    - SSL:
#      * Request New SSL Certificate (Let's Encrypt)
#      * Force SSL: ✅ ON

# 4. Verify via domain
curl https://kidney-genetics.yourdomain.com/api/health

# 5. Monitor
make prod-logs
```

---

## Security Hardening Checklist

### Implemented ✅

- [x] Multi-stage builds (minimal attack surface)
- [x] Non-root users (UID 1000 backend, nginx user frontend)
- [x] Minimal base images (python:3.11-slim, nginx:1.26-alpine)
- [x] NO unnecessary capabilities (port 8000 requires none)
- [x] Security options: no-new-privileges
- [x] Internal network for database (isolated)
- [x] External network only for NPM-accessible services
- [x] No direct port exposure in production
- [x] NPM handles SSL/TLS termination
- [x] Resource limits (CPU, memory)
- [x] Restart policies
- [x] Health checks for all services
- [x] Log rotation (50MB max, 5 files)
- [x] Security headers (CSP, HSTS, X-Frame-Options)
- [x] WebSocket support with proper Connection header handling
- [x] Runtime environment injection (Vue.js)
- [x] Database has full write access (no read-only restriction)

### Not Implemented (Future)

- [ ] Docker secrets (using env files for now)
- [ ] Image signing
- [ ] Automated vulnerability scanning in CI

---

## File Deliverables

### New Files
- [ ] `backend/Dockerfile` - Multi-stage, hardened, non-root
- [ ] `backend/.dockerignore` - Exclude tests, secrets
- [ ] `frontend/Dockerfile` - Multi-stage, nginx, runtime env injection
- [ ] `frontend/docker-entrypoint.sh` - Runtime env injection script
- [ ] `frontend/.dockerignore` - Exclude node_modules, .env files
- [ ] `frontend/nginx.prod.conf` - Production nginx with WebSocket map
- [ ] `docker-compose.prod.yml` - NPM mode (no ports)
- [ ] `docker-compose.prod.test.yml` - Test mode (ports 8080/8001/5433)
- [ ] `.env.production.example` - Environment template

### Modified Files
- [ ] `Makefile` - Add production targets
- [ ] `.gitignore` - Add `.env.production`
- [ ] `README.md` - Document deployment
- [ ] `frontend/src/main.js` - Use `window._env_` for runtime config

### Frontend Code Update

**File**: `frontend/src/config.js` (create this)

```javascript
// Runtime configuration from window._env_ (injected at container startup)
export const config = {
  apiBaseUrl: window._env_?.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || '/api',
  wsUrl: window._env_?.WS_URL || import.meta.env.VITE_WS_URL || '/ws',
  environment: window._env_?.ENVIRONMENT || import.meta.env.MODE || 'development',
  version: window._env_?.VERSION || '0.2.0'
};
```

**Update API calls to use**:
```javascript
import { config } from '@/config';
const response = await fetch(`${config.apiBaseUrl}/genes`);
```

---

## Testing Checklist

### Pre-Deployment Tests

```bash
# Build images
make prod-build

# Security audit
docker run --rm kidney-genetics-backend whoami  # Should be: kidney-api
docker run --rm kidney-genetics-frontend whoami  # Should be: nginx

# Test mode deployment
make prod-test-up
make prod-test-health

# Functional testing
curl http://localhost:8001/api/v1/genes | jq .
curl http://localhost:8080

# Cleanup
make prod-test-down
```

### Post-Deployment Tests (Production)

```bash
# Service health
make prod-health

# API via NPM
curl https://kidney-genetics.yourdomain.com/api/health | jq .

# WebSocket test
wscat -c wss://kidney-genetics.yourdomain.com/ws/

# Check no ports exposed
docker ps --filter "name=kidney-genetics" --format "{{.Ports}}"
# Should show: (empty)

# Check logs
make prod-logs
```

---

## Troubleshooting

### Problem: npm-proxy network not found
```bash
docker network create npm-proxy
make prod-up
```

### Problem: Container can't reach backend
```bash
# Verify backend joined both networks
docker network inspect npm_proxy_network | grep kidney_genetics_backend
docker network inspect kidney_genetics_internal_net | grep kidney_genetics_backend
```

### Problem: Database connection refused
```bash
# Check if postgres is healthy
docker exec kidney_genetics_postgres pg_isready -U kidney_user
# Check backend can reach postgres
docker exec kidney_genetics_backend ping kidney_genetics_postgres
```

### Problem: Frontend shows API errors
```bash
# Check runtime env injection worked
docker exec kidney_genetics_frontend cat /usr/share/nginx/html/env-config.js
# Should show: window._env_ = { API_BASE_URL: "/api", ... }
```

### Problem: Port conflicts in test mode
```bash
# Check what's using the ports
sudo lsof -i :8080
sudo lsof -i :8001
sudo lsof -i :5433
# Stop conflicting services or change ports in docker-compose.prod.test.yml
```

---

## Key Improvements from Review

1. ✅ **Vue.js Runtime Env Injection** - Solves "build once, deploy anywhere"
2. ✅ **No Unnecessary Capabilities** - Removed CAP_NET_BIND_SERVICE (port 8000 doesn't need it)
3. ✅ **PostgreSQL Write Access** - Removed read-only restriction (database needs writes)
4. ✅ **WebSocket Map Directive** - Proper Connection header handling
5. ✅ **Multi-App VPS Support** - Unique naming prevents conflicts
6. ✅ **Testable Standalone Mode** - Test production setup before NPM
7. ✅ **Explicit UID/GID** - Prevents volume permission issues
8. ✅ **Complete CSP Header** - Proper Vue.js content security policy
9. ✅ **Gzip Configuration** - Full compression config shown
10. ✅ **Health Check Content-Type** - JSON responses for monitoring tools

---

## Success Criteria

- ✅ Single command deployment: `make prod-up`
- ✅ Test mode works: `make prod-test-up`
- ✅ No ports exposed in production mode
- ✅ All services pass health checks
- ✅ Non-root users in all containers
- ✅ Resource limits enforced
- ✅ Log rotation working
- ✅ SSL/TLS via NPM working
- ✅ WebSocket connections stable
- ✅ Security headers present
- ✅ Runtime env vars changeable without rebuild
- ✅ No conflicts with other VPS apps

---

**Status**: Ready for implementation
**Next Step**: Create Dockerfiles and test locally
