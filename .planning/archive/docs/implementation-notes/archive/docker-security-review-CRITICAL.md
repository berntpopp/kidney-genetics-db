# 🔴 CRITICAL: Expert Security Review of Docker Hardening Plan

**Reviewer:** Senior Docker Security Specialist + Product Manager
**Date:** 2025-10-12
**Document Reviewed:** `docker-security-hardening.md`
**Status:** 🔴 **BLOCKING ISSUES FOUND - DO NOT IMPLEMENT AS-IS**

---

## ⚠️ EXECUTIVE SUMMARY

After ultra-careful review against official Docker documentation, OWASP guidelines, and production best practices, **5 CRITICAL BUGS and 8 HIGH-PRIORITY ISSUES** were identified that would cause:

1. **Deployment failures** (syntax errors)
2. **Runtime crashes** (missing configuration)
3. **NPM connectivity loss** (port confusion)
4. **Regressions** (permission issues)

**DO NOT PROCEED** with implementation until these are fixed.

---

## 🔴 CRITICAL BUGS (Will Break Deployment)

### BUG #1: tmpfs uid/gid Syntax Not Supported in Docker Compose
**Location:** Phase 2.1, lines 220-235
**Severity:** 🔴 CRITICAL - Will cause startup failure
**Impact:** Container will fail to start with "unsupported option" error

**BROKEN CODE:**
```yaml
tmpfs:
  - /tmp:uid=999,gid=999,mode=1777
  - /var/run/postgresql:uid=999,gid=999,mode=2777
```

**PROBLEM:**
Docker Compose **does NOT support** `uid` and `gid` options for tmpfs mounts. This is documented in multiple GitHub issues:
- https://github.com/compose-spec/compose-spec/issues/278
- As of Docker Compose v2.14+, only `mode` is supported

**CORRECT SOLUTION:**
```yaml
postgres:
  read_only: true
  tmpfs:
    - /tmp
    - /var/run/postgresql
  # Permissions are handled by the USER directive in Dockerfile
  # PostgreSQL official image already runs as UID 999

backend:
  read_only: true
  tmpfs:
    - /tmp
  # Python as UID 1000 (kidney-api user)

frontend:
  read_only: true
  tmpfs:
    - /tmp
    - /var/cache/nginx
    - /var/run
  # nginx user (UID 101) must own these directories before switching USER
```

**Why This Works:**
- tmpfs inherits permissions from the user running the process
- The USER directive in Dockerfile determines who owns tmpfs
- No uid/gid specification needed in docker-compose.yml

---

### BUG #2: Missing nginx.conf PID File Configuration
**Location:** Phase 1.1, frontend Dockerfile
**Severity:** 🔴 CRITICAL - nginx will crash on startup
**Impact:** "nginx: [emerg] open() "/run/nginx.pid" failed (13: Permission denied)"

**MISSING CONFIGURATION:**
The Dockerfile switches to `USER nginx` but nginx.conf still has default PID location `/run/nginx.pid` which nginx user cannot write to.

**REQUIRED FIX:**
Add nginx.conf modification to Dockerfile:

```dockerfile
# Stage 2: Production
FROM nginx:1.26-alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.prod.conf /etc/nginx/conf.d/default.conf

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.template

# SECURITY: Modify nginx.conf for non-root operation
RUN sed -i 's|pid /var/run/nginx.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf && \
    sed -i '/^user/d' /etc/nginx/nginx.conf

# Copy entrypoint script for runtime env injection
COPY docker-entrypoint.sh /docker-entrypoint.d/40-inject-runtime-env.sh
RUN chmod +x /docker-entrypoint.d/40-inject-runtime-env.sh

# SECURITY: Prepare directories for non-root nginx user (UID 101)
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx

# SECURITY: Switch to non-root user
USER nginx

# Health check (use port 8080)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

**Key Changes:**
1. `sed -i 's|pid /var/run/nginx.pid;|pid /tmp/nginx.pid;|'` - Move PID to /tmp
2. `sed -i '/^user/d'` - Remove user directive (conflicts with USER nginx)
3. Removed `touch /var/run/nginx.pid` (wrong location)

---

### BUG #3: docker-entrypoint.sh Incompatible with Non-Root User
**Location:** Phase 1.1, frontend Dockerfile
**Severity:** 🔴 CRITICAL - Entrypoint will fail
**Impact:** Cannot modify /usr/share/nginx/html/index.html as nginx user

**PROBLEM:**
Current entrypoint script runs as nginx user (UID 101) but tries to:
1. Write to `/usr/share/nginx/html/env-config.js`
2. Modify `/usr/share/nginx/html/index.html` with sed

These work now because script runs as root, but will fail after `USER nginx`.

**SOLUTION:**
Execute entrypoint modifications BEFORE switching to USER nginx:

```dockerfile
# MODIFIED Dockerfile section:
# Copy entrypoint script and execute it during BUILD (as root)
COPY docker-entrypoint.sh /tmp/inject-env-template.sh
RUN chmod +x /tmp/inject-env-template.sh

# Create env-config.js template and inject script tag into index.html
RUN echo "// Runtime environment configuration\n\
// Injected at container startup\n\
window._env_ = {\n\
  API_BASE_URL: \"\${API_BASE_URL:-/api}\",\n\
  WS_URL: \"\${WS_URL:-/ws}\",\n\
  ENVIRONMENT: \"\${ENVIRONMENT:-production}\",\n\
  VERSION: \"\${VERSION:-0.2.0}\"\n\
};" > /usr/share/nginx/html/env-config.js && \
    sed -i 's|</head>|  <script src="/env-config.js"></script>\n  </head>|' /usr/share/nginx/html/index.html && \
    chown nginx:nginx /usr/share/nginx/html/env-config.js /usr/share/nginx/html/index.html

# SECURITY: Prepare directories for non-root nginx user
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chown -R nginx:nginx /var/cache/nginx

# SECURITY: Switch to non-root user
USER nginx
```

**NEW docker-entrypoint.sh** (simplified for runtime):
```bash
#!/bin/sh
# Runtime environment variable injection for Vue.js
set -e

echo "Regenerating runtime environment variables..."

# Overwrite env-config.js with actual runtime values
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

echo "Runtime environment injection complete"
```

**⚠️ WAIT - This Still Won't Work!**
nginx user still can't write to /usr/share/nginx/html/env-config.js even if we own it, because the directory is read-only.

**BETTER SOLUTION:**
Use envsubst to do variable substitution and generate config in /tmp, then copy during startup:

```dockerfile
# In Dockerfile (as root):
RUN echo 'window._env_={API_BASE_URL:"${API_BASE_URL}",WS_URL:"${WS_URL}",ENVIRONMENT:"${ENVIRONMENT}",VERSION:"${VERSION}"}' > /tmp/env-config.template.js && \
    sed -i 's|</head>|  <script src="/env-config.js"></script>\n  </head>|' /usr/share/nginx/html/index.html
```

```bash
# New docker-entrypoint.sh (runs as nginx user):
#!/bin/sh
set -e
envsubst < /tmp/env-config.template.js > /usr/share/nginx/html/env-config.js
echo "Runtime config generated"
```

**⚠️ BUT WAIT - Read-Only Filesystem!**
With `read_only: true`, even nginx user can't write to /usr/share/nginx/html!

**FINAL CORRECT SOLUTION:**
Mount env-config.js from tmpfs:

```yaml
# docker-compose.prod.yml
frontend:
  read_only: true
  tmpfs:
    - /tmp
    - /var/cache/nginx
    - /var/run
    - /usr/share/nginx/html/env-config.js:uid=101,gid=101  # ❌ WAIT, uid/gid not supported!
```

**ACTUAL FINAL SOLUTION:**
Create a dedicated volume for runtime config OR skip read-only for frontend (security vs functionality trade-off):

**Option A: Skip read-only for frontend (RECOMMENDED)**
```yaml
frontend:
  # read_only: false  # Cannot use read-only with runtime env injection
  tmpfs:
    - /tmp
    - /var/cache/nginx
    - /var/run
```

**Option B: Use bind mount (complex)**
```yaml
frontend:
  read_only: true
  volumes:
    - frontend_runtime_config:/usr/share/nginx/html/env-config-volume:rw
  tmpfs:
    - /tmp
    - /var/cache/nginx
    - /var/run
volumes:
  frontend_runtime_config:
```

**RECOMMENDATION:** Use Option A - skip read-only for frontend. The security benefit is minimal since static assets don't change, and nginx still runs as non-root user with dropped capabilities.

---

### BUG #4: NPM Configuration Instructions Are Contradictory
**Location:** Phase 1.1 vs NPM-Specific Configuration section
**Severity:** 🔴 CRITICAL - Will break NPM connectivity
**Impact:** NPM cannot connect to frontend after port change

**CONTRADICTORY STATEMENTS:**

**Line 108 says:**
```
NPM Configuration:
- No changes needed in NPM
- NPM connects to `kidney_genetics_frontend` via `npm_proxy_network`
- Container internal port is transparent to NPM
```

**Line 529 says:**
```
**For Frontend:**
- Forward Port: `8080` (updated from 80)
```

**WHICH IS CORRECT?**

After researching NPM documentation: **Line 529 is WRONG**.

**HOW NPM ACTUALLY WORKS:**
1. NPM connects to containers via Docker DNS (container name)
2. NPM connects to the EXPOSED port in the Dockerfile
3. NPM **DOES NOT** need to know the internal port
4. Docker handles port mapping internally

**CORRECT NPM CONFIGURATION:**
```
NPM Proxy Host Settings:
- Scheme: http
- Forward Hostname/IP: kidney_genetics_frontend
- Forward Port: 80  # ← THIS IS CORRECT (Docker maps to 8080 internally)
- Websockets Support: ✓ Enabled
```

**⚠️ ACTUALLY, I'M WRONG TOO!**

Let me reconsider: If nginx listens on 8080 inside the container, and there's NO port mapping in docker-compose.yml (no `ports:` directive), then NPM connects directly to the container via Docker network.

**REAL CORRECT ANSWER:**
```
NPM Proxy Host Settings:
- Scheme: http
- Forward Hostname/IP: kidney_genetics_frontend
- Forward Port: 8080  # ← Matches nginx listen port inside container
- Websockets Support: ✓ Enabled
```

**WHY:**
- No `ports:` mapping in docker-compose.yml
- NPM on same network connects directly to container
- Must use the actual listen port (8080)

**FIX FOR PLAN:**
Update line 108 to:
```yaml
**NPM Configuration (REQUIRED CHANGE):**
- Forward Port must be updated from 80 to 8080 in NPM Proxy Host settings
- Forward Hostname/IP remains: `kidney_genetics_frontend`
- NPM connects via Docker DNS to container's actual listen port
```

---

### BUG #5: Incorrect Capability Requirements for Non-Root nginx
**Location:** Phase 1.2, lines 148-152
**Severity:** 🟠 HIGH - nginx may fail to start or be over-privileged
**Impact:** Either startup failure or unnecessary capabilities granted

**CURRENT PLAN:**
```yaml
frontend:
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - DAC_OVERRIDE
    - SETGID
    - SETUID
```

**PROBLEM:**
When nginx runs as non-root user from the start (via USER directive), it does NOT need SETUID/SETGID capabilities. These are only needed when nginx starts as root and drops to unprivileged user.

**RESEARCH FINDINGS:**
From Stack Overflow answer on "Which capabilities can I drop in a Docker Nginx container":
- CHOWN, DAC_OVERRIDE, SETGID, SETUID, NET_BIND_SERVICE are minimum for nginx:alpine
- But NET_BIND_SERVICE only needed for ports <1024
- SETUID/SETGID only needed if starting as root then switching users

**CORRECT CONFIGURATION:**
```yaml
frontend:
  cap_drop:
    - ALL
  cap_add:
    - CHOWN          # nginx needs to chown cache files
    - DAC_OVERRIDE   # Bypass file permission checks (controversial but required)
  # NO SETGID - not needed, already running as nginx user
  # NO SETUID - not needed, already running as nginx user
  # NO NET_BIND_SERVICE - listening on port 8080 (unprivileged)
```

**ALTERNATIVE (if issues occur):**
```yaml
frontend:
  cap_drop:
    - ALL
  cap_add:
    - CHOWN
    - DAC_OVERRIDE
    - SETGID      # Add back if nginx complains about group operations
    - SETUID      # Add back if nginx complains about user operations
```

**TESTING PROCEDURE:**
```bash
# Start with minimal capabilities
docker compose up frontend

# If nginx fails with permission error, check logs:
docker logs kidney_genetics_frontend

# Add capabilities incrementally until it works
# Principle of least privilege
```

---

## 🟠 HIGH-PRIORITY ISSUES (Must Fix Before Deployment)

### ISSUE #1: Backend Has No Need for Capabilities at All
**Location:** Phase 1.2, line 140
**Severity:** 🟠 HIGH - Violates principle of least privilege

**CURRENT PLAN:**
```yaml
backend:
  cap_drop:
    - ALL
  # NO cap_add needed for Python/FastAPI
```

This is actually **CORRECT**! But the comment should be stronger.

**RECOMMENDED:**
```yaml
backend:
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  # NO cap_add - Python/Uvicorn requires ZERO capabilities when:
  # 1. Running as non-root user (UID 1000)
  # 2. Listening on unprivileged port (8000)
  # 3. Not binding to interfaces requiring elevated permissions
  # This is the IDEAL security posture - no capabilities whatsoever
```

---

### ISSUE #2: PostgreSQL Capabilities Are Excessive
**Location:** Phase 1.2, lines 127-132
**Severity:** 🟠 HIGH - Over-privileged

**CURRENT PLAN:**
```yaml
postgres:
  cap_add:
    - CHOWN
    - DAC_OVERRIDE
    - FOWNER
    - SETGID
    - SETUID
```

**PROBLEM:**
PostgreSQL official image already handles user switching internally. When using official postgres image, it may not need all these capabilities.

**BETTER APPROACH:**
```yaml
postgres:
  cap_drop:
    - ALL
  cap_add:
    - CHOWN        # For data directory ownership
    - SETGID       # For switching to postgres user
    - SETUID       # For switching to postgres user
  # Remove DAC_OVERRIDE - should not need to bypass permissions
  # Remove FOWNER - covered by CHOWN
```

**TESTING PROCEDURE:**
```bash
# Start with minimal set
docker compose up postgres

# Check if postgres starts successfully
docker exec kidney_genetics_postgres psql -U kidney_user -c "SELECT 1"

# If fails, check logs and add capabilities one at a time
docker logs kidney_genetics_postgres | grep -i "permission\|capability"
```

---

### ISSUE #3: Resource Limits May Be Too Aggressive
**Location:** Phase 2.2, lines 260-310
**Severity:** 🟠 HIGH - May cause OOM kills or performance degradation

**CURRENT PLAN:**
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
        pids: 200
```

**PROBLEMS:**
1. **PID limit of 200 is very low** for Python application with thread pools
2. **Memory limit of 2G** may be insufficient during data pipeline operations
3. **No consideration for actual workload** - these are arbitrary numbers

**RECOMMENDED APPROACH:**

**Phase 1: Baseline (Generous Limits)**
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '4.0'          # Start generous
        memory: 4G           # Allow headroom
        pids: 1000           # Python can spawn many threads
      reservations:
        cpus: '0.5'
        memory: 512M
```

**Phase 2: Monitoring & Tuning**
```bash
# Monitor actual usage for 1 week
docker stats kidney_genetics_backend --no-stream

# Check actual PID usage
docker top kidney_genetics_backend | wc -l

# Tune based on 95th percentile + 20% headroom
```

**Frontend is TOO restrictive:**
```yaml
frontend:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
        pids: 100           # ← Probably fine for nginx
```

**PostgreSQL limits need workload analysis:**
```yaml
postgres:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G          # ← Might be too low for 571+ genes with complex queries
        pids: 200           # ← PostgreSQL uses processes, might need more
```

**CRITICAL RECOMMENDATION:**
Start with NO resource limits in Phase 1, monitor for 1-2 weeks, then set limits based on actual usage data.

---

### ISSUE #4: Missing Alembic Migration Compatibility Check
**Location:** Phase 2.1, read-only filesystem for backend
**Severity:** 🟠 HIGH - Alembic may fail to run migrations

**PROBLEM:**
Alembic writes migration state to `/app/alembic/versions/` and needs to create lock files during migrations.

**VERIFICATION NEEDED:**
```bash
# Test with read-only filesystem
docker compose exec backend alembic upgrade head

# If fails, check error:
# "cannot create lock file" or "read-only file system"
```

**SOLUTION IF NEEDED:**
```yaml
backend:
  read_only: true
  tmpfs:
    - /tmp
    - /app/alembic/.migration-lock:uid=1000,gid=1000  # ❌ uid/gid not supported!
```

**ACTUAL SOLUTION:**
```yaml
backend:
  read_only: true
  volumes:
    - ./backend/alembic:/app/alembic:rw  # Mount alembic directory as writable
  tmpfs:
    - /tmp
```

**OR BETTER:**
Run migrations in a separate init container BEFORE starting the main backend:

```yaml
services:
  backend-migrate:
    <<: *backend-base
    command: ["alembic", "upgrade", "head"]
    read_only: false  # Migrations need write access
    restart: "no"

  backend:
    <<: *backend-base
    depends_on:
      backend-migrate:
        condition: service_completed_successfully
    read_only: true
```

---

### ISSUE #5: Healthcheck Uses curl (Unnecessary Binary)
**Location:** Multiple locations
**Severity:** 🟡 MEDIUM - Increased attack surface
**Impact:** curl binary in production images is unnecessary

**PROBLEM:**
```dockerfile
# Backend
HEALTHCHECK CMD curl -f http://localhost:8000/api/health || exit 1

# Frontend uses wget (better, but still unnecessary)
HEALTHCHECK CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1
```

**BETTER:** Use TCP connection check (no external binary)

**OPTION 1: Python built-in (backend)**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health').read()" || exit 1
```

**OPTION 2: Shell TCP (works for both)**
```dockerfile
# Backend
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD timeout 5 bash -c '</dev/tcp/localhost/8000' || exit 1

# Frontend (Alpine has timeout command)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD timeout 5 sh -c 'nc -z localhost 8080' || exit 1
```

**OPTION 3: Keep wget/curl for reliability (RECOMMENDED)**
Removing curl/wget saves ~500KB but adds complexity and potential reliability issues. For production, keep them.

---

### ISSUE #6: No IPv6 Consideration
**Location:** Entire plan
**Severity:** 🟡 MEDIUM - IPv6 environments will have issues

**PROBLEM:**
nginx default configuration may try to bind to IPv6 [::]:80 which will fail with non-root user.

**FIX:**
Update nginx.prod.conf:

```nginx
server {
    listen 8080;
    listen [::]:8080;  # Explicit IPv6 binding (optional, can remove if not needed)
    server_name _;

    # OR disable IPv6 completely:
    # listen 8080;
    # (remove IPv6 line)
}
```

**RECOMMENDED:**
Add to Dockerfile:

```dockerfile
# Disable IPv6 in nginx if not needed (reduces attack surface)
RUN echo "events { use epoll; }" >> /etc/nginx/nginx.conf
```

---

### ISSUE #7: Trivy Scan Will Block CI/CD
**Location:** Phase 2.4, line 415
**Severity:** 🟠 HIGH - CI/CD will fail frequently

**PROBLEM:**
```yaml
- name: Fail on HIGH/CRITICAL vulnerabilities
  uses: aquasecurity/trivy-action@master
  with:
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
```

This will block ALL deployments when ANY high/critical CVE is found in base images (very common).

**BETTER APPROACH:**
```yaml
- name: Fail on CRITICAL vulnerabilities (HIGH is warning only)
  uses: aquasecurity/trivy-action@master
  with:
    exit-code: '1'
    severity: 'CRITICAL'

- name: Report HIGH vulnerabilities (non-blocking)
  uses: aquasecurity/trivy-action@master
  with:
    exit-code: '0'  # Don't fail
    severity: 'HIGH'
    format: 'table'
```

**EVEN BETTER:**
Allow ignoring false positives:

```yaml
- name: Run Trivy scan with policy
  uses: aquasecurity/trivy-action@master
  with:
    exit-code: '1'
    severity: 'CRITICAL'
    trivyignores: '.trivyignore'  # File with CVE exceptions
```

Create `.trivyignore`:
```
# CVE-2024-1234 - False positive, not exploitable in our use case
CVE-2024-1234

# CVE-2024-5678 - Waiting for upstream fix, mitigated by network policies
CVE-2024-5678
```

---

### ISSUE #8: Missing Logging Configuration for Read-Only Filesystem
**Location:** Phase 2.1
**Severity:** 🟠 HIGH - nginx logs will fail

**PROBLEM:**
nginx logs to `/var/log/nginx/` by default. With read-only filesystem, logs will fail.

**SOLUTION:**
Redirect logs to stdout/stderr (Docker best practice):

```dockerfile
# In frontend Dockerfile (before USER nginx)
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log
```

**OR** mount logs to tmpfs:
```yaml
frontend:
  read_only: true
  tmpfs:
    - /tmp
    - /var/cache/nginx
    - /var/run
    - /var/log/nginx  # Add logs to tmpfs
```

**RECOMMENDED:** Use stdout/stderr redirect (follows 12-factor app principles).

---

## 📋 ANTIPATTERNS IDENTIFIED

### ANTIPATTERN #1: Over-Engineering Phase 3
**Location:** Phase 3.1 - Custom Seccomp Profiles

**PROBLEM:**
The custom seccomp profile is:
1. **Extremely brittle** - breaks with any syscall changes
2. **Hard to maintain** - requires deep kernel knowledge
3. **Minimal security benefit** - default seccomp profile is already restrictive
4. **High testing burden** - needs extensive QA

**RECOMMENDATION:**
```yaml
# Instead of custom profile, use Docker's default seccomp
# It's already very restrictive and well-maintained
backend:
  security_opt:
    - no-new-privileges:true
  # NO custom seccomp - default is fine
```

**ONLY create custom seccomp if:**
1. You have specific compliance requirements (PCI-DSS Level 1, etc.)
2. You've identified specific syscalls being exploited
3. You have dedicated security team to maintain profiles

---

### ANTIPATTERN #2: Docker Content Trust Without Infrastructure
**Location:** Phase 3.2

**PROBLEM:**
Docker Content Trust requires:
1. Registry with Notary support (Docker Hub, private registry)
2. Key management infrastructure
3. Signing workflow in CI/CD
4. Key rotation procedures

**CURRENT PLAN:** Shows manual signing commands only

**RECOMMENDATION:**
Either:
1. **Skip entirely** - Use image SHA pinning instead (already in Phase 2.3)
2. **Implement properly** - Set up full DCT infrastructure with:
   - Notary server
   - Automated signing in CI/CD
   - Key backup and rotation policies
   - Team training

**For most organizations:** SHA pinning + Trivy scanning is sufficient.

---

### ANTIPATTERN #3: SBOM Generation Without Consumption
**Location:** Phase 3.3

**PROBLEM:**
```makefile
sbom:
    docker sbom kidney_genetics_backend:latest > sbom-backend.spdx.json
```

**QUESTIONS:**
1. Who consumes these SBOMs?
2. How are they stored/versioned?
3. What's the incident response plan when SBOM shows vulnerability?

**WITHOUT ANSWERS:** SBOM is just compliance theater.

**BETTER APPROACH:**
```makefile
sbom:
    docker sbom kidney_genetics_backend:latest --format spdx-json | \
        tee sbom-backend.spdx.json | \
        grype  # Scan SBOM for vulnerabilities

    # Upload to vulnerability management platform
    curl -X POST https://vuln-mgmt.example.com/sboms \
        -H "Content-Type: application/json" \
        -d @sbom-backend.spdx.json
```

---

## ✅ WHAT THE PLAN GETS RIGHT

### STRENGTH #1: Phased Approach
The 3-phase implementation is excellent:
- Phase 1 fixes critical security issues
- Phase 2 adds defense-in-depth
- Phase 3 is advanced (though some items should be cut)

### STRENGTH #2: NPM Architecture Understanding
The plan correctly identifies:
- No port exposure needed
- Containers on shared network
- NPM handles TLS termination

### STRENGTH #3: Non-Root Users
Emphasis on running all containers as non-root is spot-on and follows best practices.

### STRENGTH #4: Comprehensive Testing Procedures
Pre-deployment and post-deployment checklists are thorough and actionable.

### STRENGTH #5: Resource Limit Approach
While specific numbers need tuning, the concept of limits + reservations is correct.

---

## 🔧 REVISED IMPLEMENTATION PRIORITY

### IMMEDIATE (Week 1):
1. ✅ Fix tmpfs syntax (remove uid/gid)
2. ✅ Fix nginx PID file location
3. ✅ Fix entrypoint script for non-root
4. ✅ Update NPM port configuration instructions
5. ✅ Test frontend end-to-end with non-root
6. ✅ Add capability dropping (with corrected caps)
7. ✅ Remove database port exposure in test mode
8. ✅ Fix CORS whitelist

### SHORT-TERM (Week 2-3):
1. ✅ Add read-only filesystem (EXCEPT frontend - too complex with runtime env)
2. ✅ Add minimal resource limits (monitor mode)
3. ✅ Pin base images to SHA256
4. ✅ Add Trivy scanning (CRITICAL only, non-blocking for HIGH)
5. ✅ Add security headers

### MEDIUM-TERM (Month 1-2):
1. ✅ Tune resource limits based on monitoring data
2. ✅ Implement separate migration container for read-only backend
3. ⚠️ SKIP: Custom seccomp profiles (not worth effort)
4. ⚠️ SKIP: Docker Content Trust (use SHA pinning instead)
5. ⚠️ SKIP: SBOM generation (add only if you have tooling to consume it)

---

## 📝 CORRECTED IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (3-5 days)
- [ ] Update frontend/Dockerfile with PID fix and user directive removal
- [ ] Fix docker-entrypoint.sh OR skip read-only for frontend
- [ ] Update frontend/nginx.prod.conf to listen on 8080
- [ ] Remove tmpfs uid/gid syntax from Phase 2.1
- [ ] Correct capability lists for all services
- [ ] Update NPM configuration documentation (port 8080 required)
- [ ] Test frontend locally with non-root user
- [ ] Test backend with no capabilities
- [ ] Test postgres with minimal capabilities
- [ ] Remove database port in docker-compose.prod.test.yml
- [ ] Fix CORS origins in test mode

### Phase 2: Hardening (1-2 weeks)
- [ ] Add read-only filesystem for backend and postgres ONLY
- [ ] Add minimal resource limits (monitoring mode)
- [ ] Pin all base images to SHA256
- [ ] Set up Trivy GitHub Action (CRITICAL only)
- [ ] Add HSTS and Permissions-Policy headers
- [ ] Redirect nginx logs to stdout/stderr
- [ ] Create separate migration container for backend
- [ ] Monitor resource usage for 1 week
- [ ] Tune resource limits based on data

### Phase 3: Optional Enhancements (Ongoing)
- [ ] Consider official nginxinc/nginx-unprivileged image instead of custom
- [ ] Implement automated SHA update workflow
- [ ] Set up vulnerability management platform
- [ ] Document security incident response procedures

---

## 🎯 FINAL RECOMMENDATIONS

### CRITICAL: Do NOT implement as-is
The plan has 5 blocking bugs that will cause deployment failures. Fix all bugs before proceeding.

### HIGH: Simplify Phase 3
Remove custom seccomp, Docker Content Trust, and SBOM generation unless you have specific requirements and infrastructure.

### MEDIUM: Test extensively in staging
With read-only filesystems and capability dropping, extensive testing is required. Allocate 2x estimated time.

### BEST PRACTICE: Use official unprivileged image
Consider using `nginxinc/nginx-unprivileged:1.26-alpine` instead of customizing official nginx image. It's already configured correctly for non-root operation.

**Example:**
```dockerfile
FROM nginxinc/nginx-unprivileged:1.26-alpine AS production
# Already runs as UID 101, listens on 8080, PID in /tmp
# Just copy your config and assets
```

---

## 📚 REFERENCES USED IN REVIEW

1. Docker Compose tmpfs spec: https://github.com/compose-spec/compose-spec/issues/278
2. nginxinc unprivileged repo: https://github.com/nginxinc/docker-nginx-unprivileged
3. Docker capabilities in practice: https://blog.container-solutions.com/linux-capabilities-in-practice
4. OWASP Docker Security: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
5. NPM documentation: https://nginxproxymanager.com/guide/
6. Python bytecode in Docker: https://discuss.python.org/t/cpython-behavior-regarding-pycache-folder-on-read-only-volume/30992

---

**Review Status:** 🔴 COMPLETE - BLOCKING ISSUES IDENTIFIED
**Next Action:** Fix all CRITICAL bugs before implementation
**Estimated Fix Time:** 2-3 days for experienced Docker engineer
**Re-Review Required:** Yes, after bugs fixed
