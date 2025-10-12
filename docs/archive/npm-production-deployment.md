# Production Deployment with Nginx Proxy Manager

**Issue**: [#22 - feat: Add Nginx Proxy Manager compatible production deployment](https://github.com/berntpopp/kidney-genetics-db/issues/22)

**Status**: Planning
**Priority**: High
**Target**: v0.2.0

---

## Overview

Transform development Docker setup into production-ready deployment compatible with Nginx Proxy Manager (NPM), incorporating 2025 security best practices and container hardening.

## Current Problems

- Direct port exposure (3000, 8000, 5432) unsuitable for production
- No SSL/TLS termination or certificate management
- Missing production optimizations (resource limits, health checks, logging)
- No security hardening (runs as root, excessive capabilities)
- Not compatible with reverse proxy managers

## Target Architecture

### Multi-App VPS Setup

```
VPS Server (Multiple Apps)
├─ Nginx Proxy Manager (NPM) - Port 80/443
│  └─ Shared Network: npm-proxy
│
├─ App 1 (kidney-genetics) ← THIS APP
│  ├─ kidney-genetics-frontend (joins npm-proxy)
│  ├─ kidney-genetics-backend (joins npm-proxy + kidney-genetics-internal)
│  └─ kidney-genetics-postgres (joins kidney-genetics-internal only)
│
├─ App 2 (phentrhrive)
│  ├─ phentrhrive-frontend (joins npm-proxy)
│  └─ ... (isolated internal network)
│
└─ App N (other apps)
   └─ ... (isolated internal networks)
```

### Networking Strategy

```
Internet → NPM (:80/:443) → [npm-proxy network - SHARED]
                                ├─ kidney-genetics-frontend:80
                                ├─ kidney-genetics-backend:8000
                                ├─ phentrhrive-frontend:80
                                └─ ... (other apps)

                            [kidney-genetics-internal - ISOLATED]
                                ├─ kidney-genetics-backend:8000
                                └─ kidney-genetics-postgres:5432

                            [phentrhrive-internal - ISOLATED]
                                └─ ... (other app's DB)
```

### Key Principles

1. **No Conflicts**: Unique container/network names per app (prefix: `kidney-genetics-`)
2. **Shared NPM Network**: All apps join `npm-proxy` for NPM access
3. **Isolated Internals**: Each app has its own internal network for database isolation
4. **Testable Standalone**: Test mode exposes ports before NPM integration
5. **Security by Default**: Non-root users, minimal capabilities, read-only filesystems where possible
6. **Production Hardened**: Resource limits, health checks, structured logging, restart policies
7. **Simple Operations**: Single command deployment, clear documentation

---

## Implementation Plan

### Phase 1: Hardened Dockerfiles

#### 1.1 Backend Dockerfile (`backend/Dockerfile`)

**Features**:
- Multi-stage build (builder + production)
- Non-root user (`kidney-api`)
- Minimal base image (`python:3.11-slim`)
- Security scanning friendly (no unnecessary packages)
- Health check included

**Structure**:
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
- Install build dependencies only
- Use UV package manager
- Create virtual environment
- Install Python dependencies
- Remove build artifacts

# Stage 2: Production
FROM python:3.11-slim AS production
- Minimal runtime dependencies
- Create non-root user (UID 1000)
- Copy only virtual environment from builder
- Drop all capabilities except NET_BIND_SERVICE
- Set read-only /app where possible
- Include health check
- Use SIGTERM for graceful shutdown
```

**Key Security Measures**:
- `USER kidney-api` (non-root)
- `--read-only` mount for application code
- Capability dropping: `--cap-drop ALL --cap-add NET_BIND_SERVICE`
- No shell in production stage (distroless consideration)
- `.dockerignore` excludes secrets, tests, cache

**Files**: `backend/Dockerfile`, `backend/.dockerignore`

---

#### 1.2 Frontend Dockerfile (`frontend/Dockerfile`)

**Features**:
- Multi-stage build (build + production)
- Production Nginx configuration
- Non-root nginx user
- Optimized static asset serving

**Structure**:
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
- Install dependencies
- Build production Vue.js app
- Remove dev dependencies

# Stage 2: Production
FROM nginx:1.26-alpine AS production
- Copy production nginx config
- Copy built assets from builder
- Run as nginx user (UID 101)
- Remove default nginx config
- Security headers included
- Health check for nginx
```

**Key Security Measures**:
- `USER nginx` (non-root)
- Minimal Alpine base
- No unnecessary nginx modules
- Security headers (CSP, HSTS, X-Frame-Options)
- API proxy to backend (no CORS in production)

**Files**: `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx.prod.conf`

---

### Phase 2: Production Docker Compose

#### 2.1 Production Compose File (`docker-compose.prod.yml`)

**Purpose**: NPM-integrated deployment with NO exposed ports (production use on multi-app VPS)

**Architecture**:
```yaml
networks:
  npm-proxy:
    external: true  # MUST exist before deployment (shared across all apps)
  kidney-genetics-internal:
    driver: bridge
    internal: true  # Database completely isolated
    name: kidney-genetics-internal

services:
  postgres:
    image: postgres:14-alpine
    container_name: kidney-genetics-postgres
    networks: [kidney-genetics-internal]
    volumes:
      - kidney-genetics-postgres-data:/var/lib/postgresql/data
    # NO ports exposed
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/run/postgresql

  backend:
    build: ./backend
    container_name: kidney-genetics-backend
    networks:
      - npm-proxy              # For NPM access
      - kidney-genetics-internal  # For database access
    # NO ports exposed (NPM connects via container name)
    depends_on:
      - postgres
    env_file: .env.production

  frontend:
    build: ./frontend
    container_name: kidney-genetics-frontend
    networks: [npm-proxy]
    # NO ports exposed (NPM connects via container name)
    depends_on:
      - backend

volumes:
  kidney-genetics-postgres-data:
    name: kidney-genetics-postgres-data
```

**NPM Configuration** (in NPM UI):
- Forward Hostname/IP: `kidney-genetics-frontend`
- Forward Port: `80`
- Domain: `kidney-genetics.yourdomain.com`
- Enable WebSocket Support: ✅
- SSL Certificate: Let's Encrypt

---

#### 2.2 Test Compose File (`docker-compose.prod.test.yml`)

**Purpose**: Standalone testing with exposed ports BEFORE NPM integration

**Usage**: Test production setup on VPS without NPM (ports exposed temporarily)

```yaml
networks:
  kidney-genetics-internal:
    driver: bridge
    name: kidney-genetics-internal

services:
  postgres:
    image: postgres:14-alpine
    container_name: kidney-genetics-postgres
    networks: [kidney-genetics-internal]
    volumes:
      - kidney-genetics-postgres-data:/var/lib/postgresql/data
    ports:
      - "5433:5432"  # Non-standard port to avoid conflicts
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/run/postgresql

  backend:
    build: ./backend
    container_name: kidney-genetics-backend
    networks: [kidney-genetics-internal]
    ports:
      - "8001:8000"  # Non-standard port to avoid conflicts
    depends_on:
      - postgres
    env_file: .env.production

  frontend:
    build: ./frontend
    container_name: kidney-genetics-frontend
    networks: [kidney-genetics-internal]
    ports:
      - "8080:80"  # Non-standard port to avoid conflicts
    depends_on:
      - backend

volumes:
  kidney-genetics-postgres-data:
    name: kidney-genetics-postgres-data
```

**Test Access**:
- Frontend: `http://YOUR_VPS_IP:8080`
- Backend API: `http://YOUR_VPS_IP:8001/api/health`
- Database: `YOUR_VPS_IP:5433`

**Note**: After testing, stop test mode and switch to prod mode (no ports)

**Key Features**:

1. **Network Isolation**:
   - `npm-proxy`: External network shared with NPM (frontend + backend accessible)
   - `internal`: Internal network (PostgreSQL isolated from internet)

2. **Security Configuration**:
   - `security_opt: no-new-privileges:true` (prevent privilege escalation)
   - `read_only: true` where possible
   - `tmpfs` for writable paths
   - User namespace remapping (optional via daemon.json)

3. **Resource Limits** (per service):
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1.0'
         memory: 1G
       reservations:
         cpus: '0.5'
         memory: 512M
   ```

4. **Health Checks**:
   - Backend: `curl -f http://localhost:8000/api/health`
   - Frontend: `curl -f http://localhost/health`
   - PostgreSQL: `pg_isready -U kidney_user`

5. **Logging**:
   ```yaml
   logging:
     driver: json-file
     options:
       max-size: 50m
       max-file: 5
       labels: "service,environment"
   ```

6. **Restart Policies**:
   - `restart: unless-stopped` (production default)
   - Max retries: 3 with 5s delay

**Files**: `docker-compose.prod.yml`, `.env.production.example`

---

### Phase 3: Nginx Configuration

#### 3.1 Frontend Nginx Config (`frontend/nginx.prod.conf`)

**Features**:
- Backend API proxy (eliminates CORS)
- Static asset caching
- Gzip compression
- Security headers
- Health check endpoint

**Key Sections**:
```nginx
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; ..." always;

    # Frontend static assets
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check (for NPM and container health)
    location /health {
        access_log off;
        return 200 "healthy\n";
    }
}
```

**Files**: `frontend/nginx.prod.conf`

---

### Phase 4: Environment Configuration

#### 4.1 Production Environment Template (`.env.production.example`)

```bash
# Database Configuration
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_user
POSTGRES_PASSWORD=<CHANGE_ME_STRONG_PASSWORD>
DATABASE_URL=postgresql://kidney_user:${POSTGRES_PASSWORD}@postgres:5432/kidney_genetics

# Backend Configuration
SECRET_KEY=<CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32>
BACKEND_CORS_ORIGINS=[]  # Not needed with nginx proxy
API_V1_STR=/api/v1
PROJECT_NAME="Kidney Genetics Database"

# Frontend Configuration (build-time)
VITE_API_BASE_URL=/api  # Relative URL (proxied by nginx)
VITE_WS_URL=/ws         # Relative URL (proxied by nginx)

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
ALLOWED_HOSTS=localhost,your-domain.com
```

**Security Notes**:
- Never commit `.env.production` (add to .gitignore)
- Use strong passwords (20+ chars, random)
- Rotate SECRET_KEY regularly
- Use Docker secrets for sensitive values (optional enhancement)

**Files**: `.env.production.example`, `.gitignore` update

---

### Phase 5: Documentation & Tooling

#### 5.1 Deployment Guide (`docs/deployment/npm-deployment.md`)

**Contents**:
1. **Prerequisites**: Docker, Docker Compose, NPM installed
2. **NPM Network Setup**:
   ```bash
   docker network create npm-proxy
   ```
3. **Initial Deployment**:
   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with secure values
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```
4. **NPM Configuration**:
   - Add Proxy Host in NPM UI
   - Domain: `kidney-genetics.example.com`
   - Forward to: `frontend` (container name)
   - Port: `80`
   - Enable WebSocket support
   - Enable SSL (Let's Encrypt)
5. **Verification**: Health checks, logs, SSL test
6. **Maintenance**: Updates, backups, monitoring

#### 5.2 Makefile Targets

Add production commands:
```makefile
# Production deployment (NPM mode - no ports exposed)
.PHONY: prod-build prod-up prod-down prod-logs prod-restart prod-health

prod-build:
	@echo "Building production images..."
	docker-compose -f docker-compose.prod.yml build --no-cache

prod-up:
	@echo "Starting production deployment (NPM mode)..."
	@echo "⚠️  Requires 'npm-proxy' network to exist!"
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f --tail=100

prod-restart:
	docker-compose -f docker-compose.prod.yml restart

prod-health:
	@echo "=== Service Health Check ==="
	@docker ps --filter "name=kidney-genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test mode (standalone with exposed ports)
.PHONY: prod-test-up prod-test-down prod-test-logs prod-test-health

prod-test-up:
	@echo "Starting production TEST mode (ports exposed)..."
	@echo "Access at: http://YOUR_VPS_IP:8080"
	docker-compose -f docker-compose.prod.test.yml up -d

prod-test-down:
	docker-compose -f docker-compose.prod.test.yml down

prod-test-logs:
	docker-compose -f docker-compose.prod.test.yml logs -f --tail=100

prod-test-health:
	@echo "=== Test Mode Health Check ==="
	@echo "Frontend: http://localhost:8080"
	@echo "Backend: http://localhost:8001/api/health"
	@curl -f http://localhost:8001/api/health 2>/dev/null && echo " ✅" || echo " ❌"
	@docker ps --filter "name=kidney-genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Network management
.PHONY: npm-network-create npm-network-check

npm-network-create:
	@echo "Creating shared npm-proxy network..."
	docker network create npm-proxy || echo "Network already exists"

npm-network-check:
	@echo "Checking npm-proxy network..."
	@docker network inspect npm-proxy >/dev/null 2>&1 && echo "✅ npm-proxy network exists" || echo "❌ npm-proxy network missing! Run 'make npm-network-create'"
```

**Files**: `docs/deployment/npm-deployment.md`, `Makefile` updates

---

## Security Hardening Checklist

Based on 2025 Docker security best practices:

### Container Security
- [x] Multi-stage builds (minimize attack surface)
- [x] Non-root users for all services
- [x] Minimal base images (slim/alpine)
- [x] Read-only root filesystem where possible
- [x] Drop unnecessary capabilities
- [x] No privileged containers
- [x] Security options: `no-new-privileges:true`

### Network Security
- [x] Internal network for database (not exposed)
- [x] External network only for NPM-accessible services
- [x] No direct port exposure
- [x] NPM handles SSL/TLS termination

### Secrets Management
- [x] Environment files excluded from git
- [x] Strong password requirements documented
- [ ] Optional: Docker secrets integration (future enhancement)

### Resource Management
- [x] CPU and memory limits
- [x] Restart policies
- [x] Health checks for all services
- [x] Log rotation (50MB max, 5 files)

### Runtime Security
- [x] Image scanning friendly (minimal layers)
- [x] No shell in production images (where possible)
- [x] Regular base image updates process documented
- [x] CVE monitoring setup documented

### Application Security
- [x] Security headers (CSP, HSTS, X-Frame-Options)
- [x] No CORS needed (nginx proxy)
- [x] WebSocket support secured
- [x] Rate limiting via NPM

---

## Testing Plan

### 1. Local Testing
```bash
# Build images
make prod-build

# Start services (without NPM first)
docker-compose -f docker-compose.prod.yml up -d

# Test health endpoints
curl http://localhost:8000/api/health  # Should fail (no ports exposed)

# Join npm-proxy network temporarily for testing
docker network connect npm-proxy kidney_genetics_backend
docker network connect npm-proxy kidney_genetics_frontend

# Test via network
docker run --rm --network npm-proxy alpine/curl curl http://frontend/health
docker run --rm --network npm-proxy alpine/curl curl http://backend:8000/api/health
```

### 2. NPM Integration Test
- Configure NPM proxy host
- Verify SSL certificate generation
- Test WebSocket connections
- Verify API calls work through proxy
- Check security headers with curl

### 3. Security Audit
```bash
# Scan images for vulnerabilities
docker scout cves kidney-genetics-backend
docker scout cves kidney-genetics-frontend

# Check for secrets in images
docker history kidney-genetics-backend | grep -i "secret\|password"

# Verify non-root users
docker run --rm kidney-genetics-backend whoami  # Should be 'kidney-api'
docker run --rm kidney-genetics-frontend whoami  # Should be 'nginx'
```

### 4. Load Testing
- Verify resource limits work
- Test restart policies (kill containers)
- Monitor CPU/memory usage under load
- Verify log rotation works

---

## Migration Path

### From Development to Production

1. **Backward Compatibility**: Keep `docker-compose.yml` for development
2. **Clear Separation**: Production uses `docker-compose.prod.yml`
3. **Documentation**: Update README with both modes
4. **CI/CD Ready**: Production config works with GitHub Actions

### Deployment Steps

#### Phase 1: Test Mode (Standalone with Exposed Ports)

```bash
# Step 1: Prepare environment
cp .env.production.example .env.production
# Edit .env.production with production values

# Step 2: Build images
make prod-build

# Step 3: Deploy in TEST mode (ports exposed)
make prod-test-up

# Step 4: Verify everything works
make prod-test-health
# Access frontend: http://YOUR_VPS_IP:8080
# Access backend: http://YOUR_VPS_IP:8001/api/health

# Step 5: Test thoroughly
curl http://YOUR_VPS_IP:8001/api/v1/genes
# Test all functionality

# Step 6: Stop test mode
make prod-test-down
```

#### Phase 2: NPM Mode (No Exposed Ports)

```bash
# Step 1: Ensure npm-proxy network exists
make npm-network-check
# If missing: make npm-network-create

# Step 2: Deploy in PRODUCTION mode (no ports)
make prod-up

# Step 3: Configure NPM
# - Open NPM UI (http://npm-host:81)
# - Add Proxy Host:
#   * Domain: kidney-genetics.yourdomain.com
#   * Scheme: http
#   * Forward Hostname: kidney-genetics-frontend
#   * Forward Port: 80
#   * Websockets: ✅ Enabled
# - Request SSL Certificate (Let's Encrypt)

# Step 4: Verify via NPM
curl https://kidney-genetics.yourdomain.com/api/health
# Should return healthy response

# Step 5: Monitor
make prod-logs
```

#### Quick Reference

```bash
# Check if npm-proxy network exists
make npm-network-check

# Test mode (for debugging)
make prod-test-up      # Start with ports
make prod-test-health  # Check health
make prod-test-down    # Stop

# Production mode (NPM-integrated)
make prod-up           # Start without ports
make prod-health       # Check containers
make prod-logs         # View logs
make prod-down         # Stop
```

---

## Multi-App VPS Considerations

### Naming Strategy

**Critical**: All resources MUST use unique `kidney-genetics-` prefix to avoid conflicts with other apps on the VPS.

| Resource Type | Naming Convention | Example |
|--------------|-------------------|---------|
| Containers | `kidney-genetics-{service}` | `kidney-genetics-frontend` |
| Networks | `kidney-genetics-{purpose}` | `kidney-genetics-internal` |
| Volumes | `kidney-genetics-{service}-data` | `kidney-genetics-postgres-data` |

### Shared vs Isolated Networks

```yaml
# SHARED NETWORK (across all apps on VPS)
npm-proxy:
  external: true  # Created once, shared by all apps

# ISOLATED NETWORK (per app)
kidney-genetics-internal:
  name: kidney-genetics-internal  # Unique to this app
  internal: true  # No external access
```

### Port Mapping Strategy

#### NPM Mode (Production)
- **No ports exposed** - NPM connects via container names
- All apps can coexist without port conflicts

#### Test Mode (Temporary)
Use **non-standard ports** to avoid conflicts:
- Frontend: `8080` (instead of 80)
- Backend: `8001` (instead of 8000)
- PostgreSQL: `5433` (instead of 5432)

### Container Name Resolution

NPM uses container names as hostnames:
```yaml
# NPM Proxy Host Configuration:
Forward Hostname: kidney-genetics-frontend  # Container name
Forward Port: 80                            # Internal port
```

### Conflict Prevention Checklist

- [ ] All containers have `kidney-genetics-` prefix
- [ ] Internal network has unique name
- [ ] Volumes have unique names
- [ ] Test mode uses non-standard ports (8080, 8001, 5433)
- [ ] NPM network is external (not owned by this app)
- [ ] No hardcoded IPs (use container names)

### Example Multi-App Setup

```bash
# VPS with multiple apps
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Output (NPM mode):
kidney-genetics-frontend     # No exposed ports
kidney-genetics-backend      # No exposed ports
kidney-genetics-postgres     # No exposed ports
phentrhrive-frontend         # No exposed ports
phentrhrive-backend          # No exposed ports
other-app-frontend           # No exposed ports

# Only NPM exposes ports:
nginx-proxy-manager          0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

### Troubleshooting Multi-App Issues

**Problem**: Container names conflict
- **Solution**: Ensure all containers use app-specific prefix

**Problem**: Network conflicts
- **Solution**: Use unique internal network names per app

**Problem**: Can't access via NPM
- **Solution**: Verify container joined `npm-proxy` network:
  ```bash
  docker network inspect npm-proxy | grep kidney-genetics
  ```

**Problem**: Database connection fails
- **Solution**: Ensure backend joins both networks:
  - `npm-proxy` (for NPM access)
  - `kidney-genetics-internal` (for database)

---

## File Checklist

### New Files
- [ ] `backend/Dockerfile` - Multi-stage, hardened backend image
- [ ] `backend/.dockerignore` - Exclude tests, cache, secrets
- [ ] `frontend/Dockerfile` - Multi-stage, nginx production image
- [ ] `frontend/.dockerignore` - Exclude node_modules, .env files
- [ ] `frontend/nginx.prod.conf` - Production nginx configuration
- [ ] `docker-compose.prod.yml` - Production compose file (NPM mode, no ports)
- [ ] `docker-compose.prod.test.yml` - Test compose file (standalone, with ports)
- [ ] `.env.production.example` - Production environment template
- [ ] `docs/deployment/npm-deployment.md` - Deployment guide
- [ ] `docs/deployment/security-hardening.md` - Security practices guide

### Modified Files
- [ ] `Makefile` - Add production targets
- [ ] `.gitignore` - Exclude `.env.production`
- [ ] `README.md` - Update deployment section
- [ ] `docs/README.md` - Link to deployment guide

### Documentation Updates
- [ ] Architecture diagram update
- [ ] Deployment workflow
- [ ] Security best practices
- [ ] Troubleshooting guide

---

## Success Criteria

- ✅ Single command production deployment: `make prod-up`
- ✅ No ports exposed except via NPM
- ✅ All services pass health checks
- ✅ Non-root users in all containers
- ✅ Resource limits enforced
- ✅ Log rotation working
- ✅ SSL/TLS via NPM working
- ✅ WebSocket connections stable
- ✅ Security headers present
- ✅ Image vulnerability scan passes
- ✅ Documentation complete and tested

---

## Future Enhancements (Post v0.2.0)

1. **Docker Secrets**: Replace env vars with Docker secrets
2. **Container Scanning**: Automated Trivy/Snyk scans in CI
3. **Health Dashboard**: Prometheus + Grafana monitoring
4. **Backup Automation**: Automated PostgreSQL backups to S3
5. **High Availability**: Multi-replica deployment with load balancing
6. **Image Registry**: Push to private registry (GHCR)

---

## References

### Best Practices
- [Docker Security Best Practices 2025](https://docs.docker.com/engine/security/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [FastAPI Docker Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Nginx Proxy Manager Documentation](https://nginxproxymanager.com/)

### Example Implementations
- `gtex-link`: Multi-stage builds, health checks, resource limits
- Project CLAUDE.md: Non-blocking architecture principles

---

**Next Steps**: Create Dockerfiles and test locally before NPM integration.
