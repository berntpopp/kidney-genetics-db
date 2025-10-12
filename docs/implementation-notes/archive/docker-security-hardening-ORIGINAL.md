# Docker Security Hardening Implementation Plan

**Status:** Active
**Priority:** Critical
**Target:** Production deployment behind NPM (Nginx Proxy Manager)
**Timeline:** Phase 1 (1 week), Phase 2 (2 weeks), Phase 3 (ongoing)

## Context

Security audit identified 18 vulnerabilities (5 critical, 5 high, 5 medium, 3 low) in current Docker production build. This plan addresses all critical/high issues with NPM proxy compatibility.

## NPM Architecture Constraints

```
Internet → NPM (SSL, External) → npm_proxy_network → Frontend (port 80)
                                                    → Backend (port 8000)
                                 internal_network → PostgreSQL (no ports)
```

**Key NPM Requirements:**
- Containers on `npm_proxy_network` (external proxy access)
- NO host port exposure (NPM connects via container name)
- NO SSL in containers (NPM handles TLS termination)
- Frontend must support being behind reverse proxy
- WebSocket headers must pass through NPM

---

## Phase 1: Critical Fixes (Deploy Within 3 Days)

### 1.1 Frontend: Run as Non-Root User

**File:** `frontend/Dockerfile`

**Problem:** Master nginx process runs as root (privilege escalation risk)

**Solution:** Run nginx on unprivileged port 8080 as nginx user

```dockerfile
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

# SECURITY: Prepare directories for non-root nginx user (UID 101)
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid && \
    # Create necessary directories
    mkdir -p /var/cache/nginx/client_temp && \
    mkdir -p /var/cache/nginx/proxy_temp && \
    mkdir -p /var/cache/nginx/fastcgi_temp && \
    mkdir -p /var/cache/nginx/uwsgi_temp && \
    mkdir -p /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx

# SECURITY: Switch to non-root user
USER nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

**File:** `frontend/nginx.prod.conf`

**Change:** Listen on port 8080 instead of 80

```nginx
server {
    listen 8080;  # Changed from 80 (non-privileged port)
    server_name _;

    # ... rest of config unchanged ...
}
```

**File:** `docker-compose.prod.yml`

**Change:** Update internal port reference (NPM still connects via container name)

```yaml
frontend:
  # ... existing config ...
  # NO CHANGES NEEDED - NPM connects via container name, not port
  # nginx listens on 8080 internally, NPM doesn't care
```

**NPM Configuration:**
- No changes needed in NPM
- NPM connects to `kidney_genetics_frontend` via `npm_proxy_network`
- Container internal port is transparent to NPM

---

### 1.2 Drop All Capabilities (Production)

**File:** `docker-compose.prod.yml`

**Add to ALL services:**

```yaml
postgres:
  # ... existing config ...
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - DAC_OVERRIDE
    - FOWNER
    - SETGID
    - SETUID

backend:
  # ... existing config ...
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  # NO cap_add needed for Python/FastAPI

frontend:
  # ... existing config ...
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - CHOWN      # nginx needs to chown cache files
    - DAC_OVERRIDE
    - SETGID
    - SETUID
```

---

### 1.3 Remove Database Port Exposure (Test Mode)

**File:** `docker-compose.prod.test.yml`

**Remove lines 22-23:**

```yaml
postgres:
  # ... existing config ...
  # REMOVED: ports: ["5434:5432"]
  # For debugging, use: docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

---

### 1.4 Fix CORS in Test Mode

**File:** `docker-compose.prod.test.yml`

**Change line 52:**

```yaml
backend:
  environment:
    # OLD: BACKEND_CORS_ORIGINS: '["*"]'
    # NEW: Explicit whitelist
    BACKEND_CORS_ORIGINS: '["http://localhost:8080","http://localhost:8001"]'
```

---

### 1.5 Improve Content Security Policy (Carefully)

**File:** `frontend/nginx.prod.conf`

**Replace line 25 with:**

```nginx
# CSP: Relaxed for Vue.js compatibility, tightened where possible
# Note: unsafe-inline needed for Vue.js runtime, unsafe-eval needed for dev mode
# In production, consider using nonces or hash-based CSP
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' wss: https:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'; upgrade-insecure-requests;" always;
```

**Notes:**
- Keep `unsafe-inline`/`unsafe-eval` for Vue.js compatibility (documented limitation)
- Add `upgrade-insecure-requests` for HTTPS enforcement behind NPM
- Add `frame-ancestors 'self'` to prevent clickjacking
- Add `object-src 'none'` to block Flash/Java applets

---

## Phase 2: High Priority Hardening (Deploy Within 2 Weeks)

### 2.1 Add Read-Only Filesystem + tmpfs

**File:** `docker-compose.prod.yml`

```yaml
postgres:
  # ... existing config ...
  read_only: true
  tmpfs:
    - /tmp:uid=999,gid=999,mode=1777
    - /var/run/postgresql:uid=999,gid=999,mode=2777

backend:
  # ... existing config ...
  read_only: true
  tmpfs:
    - /tmp:uid=1000,gid=1000

frontend:
  # ... existing config ...
  read_only: true
  tmpfs:
    - /tmp:uid=101,gid=101
    - /var/cache/nginx:uid=101,gid=101
    - /var/run:uid=101,gid=101
```

**Testing:**
```bash
# After deployment, verify read-only enforcement
docker exec kidney_genetics_backend touch /test.txt  # Should fail
docker exec kidney_genetics_frontend touch /test.txt  # Should fail
docker exec kidney_genetics_postgres touch /test.txt  # Should fail

# Verify tmpfs works
docker exec kidney_genetics_backend touch /tmp/test.txt  # Should succeed
docker exec kidney_genetics_frontend touch /tmp/test.txt  # Should succeed

# Verify app still works
curl http://kidney-genetics.yourdomain.com/api/health  # Should return 200
```

---

### 2.2 Add Resource Limits

**File:** `docker-compose.prod.yml`

```yaml
postgres:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
        pids: 200
      reservations:
        cpus: '0.5'
        memory: 512M
  ulimits:
    nproc: 512
    nofile:
      soft: 4096
      hard: 8192

backend:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
        pids: 200
      reservations:
        cpus: '0.5'
        memory: 512M
  ulimits:
    nproc: 512
    nofile:
      soft: 4096
      hard: 8192

frontend:
  # ... existing config ...
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
        pids: 100
      reservations:
        cpus: '0.25'
        memory: 128M
  ulimits:
    nproc: 256
    nofile:
      soft: 2048
      hard: 4096
```

**Monitoring:**
```bash
# Monitor resource usage
docker stats kidney_genetics_backend
docker stats kidney_genetics_frontend
docker stats kidney_genetics_postgres
```

---

### 2.3 Pin Base Images to SHA256

**Get Current SHAs:**
```bash
docker pull python:3.11-slim && docker inspect python:3.11-slim --format='{{index .RepoDigests 0}}'
docker pull node:20-alpine && docker inspect node:20-alpine --format='{{index .RepoDigests 0}}'
docker pull nginx:1.26-alpine && docker inspect nginx:1.26-alpine --format='{{index .RepoDigests 0}}'
docker pull postgres:14-alpine && docker inspect postgres:14-alpine --format='{{index .RepoDigests 0}}'
```

**File:** `backend/Dockerfile`

```dockerfile
# Pin to specific SHA256 (update quarterly)
FROM python:3.11-slim@sha256:[ACTUAL_SHA] AS builder
# ...
FROM python:3.11-slim@sha256:[ACTUAL_SHA] AS production
```

**File:** `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine@sha256:[ACTUAL_SHA] AS builder
# ...
FROM nginx:1.26-alpine@sha256:[ACTUAL_SHA] AS production
```

**File:** `docker-compose.prod.yml`

```yaml
postgres:
  image: postgres:14-alpine@sha256:[ACTUAL_SHA]
```

**Maintenance:** Update SHAs quarterly or when CVEs announced

---

### 2.4 Add Trivy Security Scanning

**File:** `.github/workflows/docker-security-scan.yml`

```yaml
name: Docker Security Scan

on:
  push:
    branches: [main, dev/*]
  pull_request:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday 2 AM

jobs:
  trivy-scan:
    name: Trivy Vulnerability Scan
    runs-on: ubuntu-latest

    permissions:
      security-events: write
      actions: read
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build backend image
        run: docker build -t kidney-genetics-backend:${{ github.sha }} ./backend

      - name: Build frontend image
        run: docker build -t kidney-genetics-frontend:${{ github.sha }} ./frontend

      - name: Run Trivy scan - Backend
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'kidney-genetics-backend:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-backend.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Run Trivy scan - Frontend
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'kidney-genetics-frontend:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-frontend.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: '.'

      - name: Fail on HIGH/CRITICAL vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'kidney-genetics-backend:${{ github.sha }}'
          format: 'table'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'
```

---

### 2.5 Additional Security Headers

**File:** `frontend/nginx.prod.conf`

**Add after line 26:**

```nginx
    # Additional security headers for production
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()" always;
    # Remove deprecated header
    # add_header X-XSS-Protection "1; mode=block" always;  # REMOVED - deprecated
```

**Note:** HSTS header only effective when NPM serves HTTPS (which it should be)

---

## Phase 3: Advanced Hardening (Ongoing)

### 3.1 Custom Seccomp Profiles (Optional)

**File:** `security/seccomp-backend.json` (create new directory)

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
  "syscalls": [
    {
      "names": [
        "accept4", "access", "arch_prctl", "bind", "brk", "chdir", "chmod",
        "clone", "close", "connect", "dup", "dup2", "epoll_create1",
        "epoll_ctl", "epoll_wait", "execve", "exit", "exit_group", "fcntl",
        "fstat", "futex", "getcwd", "getdents64", "getpid", "getppid",
        "gettid", "ioctl", "listen", "lseek", "mmap", "mprotect", "munmap",
        "open", "openat", "pipe", "poll", "read", "readlink", "recvfrom",
        "rt_sigaction", "rt_sigprocmask", "sendto", "set_robust_list",
        "set_tid_address", "setsockopt", "sigaltstack", "socket", "stat",
        "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

**File:** `docker-compose.prod.yml`

```yaml
backend:
  # ... existing config ...
  security_opt:
    - no-new-privileges:true
    - seccomp=./security/seccomp-backend.json
```

**Notes:**
- Start with permissive profile, monitor denials in logs
- Tighten gradually based on actual syscalls needed
- Test thoroughly in staging before production

---

### 3.2 Docker Content Trust (Image Signing)

**Setup (one-time):**
```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Generate signing keys (follow prompts)
docker trust key generate kidney-genetics

# Sign images during push
docker tag kidney_genetics_backend:latest your-registry.com/kidney_genetics_backend:latest
docker push your-registry.com/kidney_genetics_backend:latest
```

---

### 3.3 SBOM Generation

**File:** `Makefile`

```makefile
.PHONY: sbom
sbom:
	@echo "Generating Software Bill of Materials..."
	docker sbom kidney_genetics_backend:latest --format spdx-json > sbom-backend.spdx.json
	docker sbom kidney_genetics_frontend:latest --format spdx-json > sbom-frontend.spdx.json
	@echo "SBOMs generated: sbom-backend.spdx.json, sbom-frontend.spdx.json"
```

---

## NPM-Specific Configuration

### Required NPM Proxy Host Settings

**For Frontend:**
- Scheme: `http` (not https, NPM handles SSL)
- Forward Hostname/IP: `kidney_genetics_frontend`
- Forward Port: `8080` (updated from 80)
- Websockets Support: ✓ Enabled
- Block Common Exploits: ✓ Enabled
- Cache Assets: ✓ Enabled (optional)

**For Backend (if direct API access):**
- Scheme: `http`
- Forward Hostname/IP: `kidney_genetics_backend`
- Forward Port: `8000`
- Websockets Support: ✓ Enabled (for /ws/ endpoint)
- Custom Nginx Config (optional):
  ```nginx
  # Increase timeouts for long-running operations
  proxy_read_timeout 300s;
  proxy_connect_timeout 300s;
  proxy_send_timeout 300s;
  ```

**NPM Custom Headers (Optional):**
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Backup current production database
- [ ] Test all changes in `docker-compose.prod.test.yml` locally
- [ ] Verify health checks pass: `docker compose ps`
- [ ] Verify logs show no errors: `docker compose logs`
- [ ] Test login functionality
- [ ] Test WebSocket connections (data sources page)
- [ ] Run Trivy scan locally: `trivy image kidney_genetics_backend:latest`

### Deployment Steps

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild images with security hardening
docker compose -f docker-compose.prod.yml build --no-cache

# 3. Stop old containers (zero-downtime with NPM)
docker compose -f docker-compose.prod.yml down

# 4. Start new containers
docker compose -f docker-compose.prod.yml up -d

# 5. Verify health
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50

# 6. Test via NPM
curl -I https://kidney-genetics.yourdomain.com/api/health
```

### Post-Deployment Verification

```bash
# Check security settings
docker inspect kidney_genetics_backend --format='{{.HostConfig.ReadonlyRootfs}}'  # Should be true
docker inspect kidney_genetics_backend --format='{{.HostConfig.CapDrop}}'  # Should show [ALL]

# Monitor resource usage
docker stats

# Check for security issues
docker scan kidney_genetics_backend:latest
```

---

## Rollback Plan

If issues occur:

```bash
# Quick rollback
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Or use tagged images
docker tag kidney_genetics_backend:latest kidney_genetics_backend:backup
docker tag kidney_genetics_backend:v0.1.0 kidney_genetics_backend:latest
docker compose -f docker-compose.prod.yml up -d
```

---

## Monitoring & Maintenance

### Weekly
- [ ] Review GitHub Security tab for Trivy findings
- [ ] Check Docker logs for security errors: `docker compose logs | grep -i "permission denied\|forbidden"`

### Monthly
- [ ] Update base image SHAs if CVEs announced
- [ ] Review resource limits based on actual usage
- [ ] Test rollback procedure

### Quarterly
- [ ] Update all base images to latest patch versions
- [ ] Re-run full security audit
- [ ] Review and tighten seccomp profiles

---

## Success Metrics

- ✅ No containers running as root (`docker top <container>`)
- ✅ All containers have `ReadonlyRootfs: true`
- ✅ All containers have `CapDrop: [ALL]`
- ✅ Zero HIGH/CRITICAL vulnerabilities in Trivy scans
- ✅ Database not exposed to host (`netstat -tlnp | grep 5432` shows nothing)
- ✅ Resource limits enforced (`docker stats` shows limits)
- ✅ Health checks passing (`docker compose ps` shows healthy)
- ✅ NPM successfully proxies to containers
- ✅ WebSockets work through NPM
- ✅ Login functionality works
- ✅ No security-related errors in logs

---

## References

- OWASP Docker Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- CIS Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- Docker Security Best Practices: https://docs.docker.com/engine/security/
- NPM Documentation: https://nginxproxymanager.com/guide/

---

**Implementation Owner:** DevOps/Security Team
**Last Updated:** 2025-10-12
**Next Review:** Phase 1 completion (3 days)
