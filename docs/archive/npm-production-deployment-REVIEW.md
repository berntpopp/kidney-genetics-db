# Expert Review: NPM Production Deployment Plan

**Reviewer**: Senior Product Manager & Full Stack Developer
**Date**: 2025-10-10
**Plan**: `npm-production-deployment.md`
**Status**: Issues Identified - Requires Revisions

---

## Executive Summary

The implementation plan is **85% solid** with excellent structure and comprehensive coverage. However, **7 critical issues** and **5 moderate improvements** were identified through deep research of 2025 best practices, Docker documentation, and real-world production patterns.

### Risk Assessment
- **🔴 Critical Issues**: 3 (will cause failures)
- **🟡 Moderate Issues**: 4 (suboptimal but functional)
- **🟢 Minor Improvements**: 5 (nice-to-haves)

---

## 🔴 Critical Issues (MUST FIX)

### 1. Vue.js Environment Variables - Build-Time vs Runtime Problem

**Issue**: The plan assumes Vite environment variables (`VITE_API_BASE_URL`) can be changed at runtime, but they are **statically inlined at build time**.

**Impact**:
- Cannot change API URLs without rebuilding the entire frontend image
- Defeats Docker's "build once, deploy anywhere" philosophy
- Production and staging would need separate builds

**Evidence** (May 2025 articles):
> "When you run npm run build, Vite crawls through your code and literally replaces any reference like `import.meta.env.VITE_API_URL` with the value... It becomes a hardcoded string in your final JS bundle."

**Correct Solution**:
```dockerfile
# Frontend Dockerfile - Add runtime env injection
FROM nginx:1.26-alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Create entrypoint script for runtime env substitution
COPY docker-entrypoint.sh /docker-entrypoint.d/40-inject-env.sh
RUN chmod +x /docker-entrypoint.d/40-inject-env.sh

# The script will:
# 1. Generate a window.env.js file at startup
# 2. Replace placeholders in index.html if needed
# 3. Inject actual env vars from Docker environment
```

**docker-entrypoint.sh**:
```bash
#!/bin/sh
# Generate runtime config accessible to Vue app
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  API_BASE_URL: "${API_BASE_URL:-/api}",
  WS_URL: "${WS_URL:-/ws}",
  ENVIRONMENT: "${ENVIRONMENT:-production}"
};
EOF
```

**Vue.js Usage**:
```javascript
// Instead of import.meta.env.VITE_API_BASE_URL
const apiUrl = window._env_?.API_BASE_URL || '/api';
```

**References**:
- https://dev.to/dutchskull/setting-up-dynamic-environment-variables-with-vite-and-docker-5cmj
- https://moreillon.medium.com/environment-variables-for-containerized-vue-js-applications-f0aa943cb962

---

### 2. Unnecessary Capability Addition - CAP_NET_BIND_SERVICE

**Issue**: Plan suggests adding `CAP_NET_BIND_SERVICE` capability for port 8000.

**Impact**:
- Adds unnecessary capability (security risk)
- Port 8000 is NOT a privileged port (only 0-1023 are)
- Contradicts "drop all capabilities" principle

**Evidence**:
> "Port 8000 is not a privileged port, so CAP_NET_BIND_SERVICE has never been necessary for binding to it. Privileged ports are those numbered 0-1023."

**Correct Solution**:
```yaml
# docker-compose.prod.yml - Backend service
backend:
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  # No cap_add needed for port 8000!
```

**Remove from Dockerfile specs**:
```diff
- Drop all capabilities except NET_BIND_SERVICE
+ Drop all capabilities (port 8000 doesn't need special privileges)
```

---

### 3. PostgreSQL Read-Only Filesystem - Incomplete Configuration

**Issue**: Plan shows `read_only: true` for PostgreSQL with only `/tmp` and `/var/run/postgresql` as tmpfs mounts. PostgreSQL needs MORE writable directories.

**Impact**:
- Container will fail to start
- PostgreSQL writes to multiple paths: `/var/lib/postgresql/data`, `/var/run/postgresql`, `/tmp`, `/run`

**Evidence**:
> "Errors can occur like 'chmod: changing permissions of '/run/postgresql': Read-only file system' when running PostgreSQL containers in read-only mode."

**Correct Solution**:
```yaml
postgres:
  image: postgres:14-alpine
  read_only: true
  tmpfs:
    - /tmp
    - /run
    - /var/run/postgresql
  # Data volume is NOT read-only
  volumes:
    - postgres_data:/var/lib/postgresql/data  # Writable volume
  security_opt:
    - no-new-privileges:true
```

**Alternative** (if read-only is too restrictive):
```yaml
postgres:
  image: postgres:14-alpine
  # Skip read_only for database - focus on other security measures
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
    - CAP_CHOWN
    - CAP_FOWNER
  # Still very secure without read_only
```

**References**:
- https://github.com/docker-library/postgres/issues/154
- https://blog.ploetzli.ch/2025/docker-best-practices-read-only-containers/

---

## 🟡 Moderate Issues (SHOULD FIX)

### 4. Missing Nginx Map Directive for WebSocket Connection Header

**Issue**: WebSocket proxy configuration missing `map` directive for proper `Connection` header handling.

**Impact**:
- WebSocket connections may not upgrade correctly in edge cases
- When `Upgrade` header is empty, Connection should be "close", not "upgrade"

**Current (Incomplete)**:
```nginx
location /ws/ {
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**Correct Solution**:
```nginx
# Add to nginx.prod.conf (outside server block)
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    # ... other config ...

    location /ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;  # Use mapped variable
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Recommended timeouts for WebSockets
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

**References**:
- https://www.f5.com/company/blog/nginx/websocket-nginx
- https://fastapitutorial.com/blog/wss-nginx-fastapi/

---

### 5. Database Credentials in Plain Text Environment Files

**Issue**: Plan stores database passwords in `.env.production` files, committed (example) to repo.

**Impact**:
- Credentials visible in container inspect
- Not using Docker's built-in secrets mechanism
- Harder to rotate credentials

**Current**:
```bash
POSTGRES_PASSWORD=<CHANGE_ME_STRONG_PASSWORD>
DATABASE_URL=postgresql://kidney_user:${POSTGRES_PASSWORD}@postgres:5432/kidney_genetics
```

**Better Solution** (for future enhancement):
```yaml
# docker-compose.prod.yml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

  backend:
    environment:
      DATABASE_URL_FILE: /run/secrets/database_url
    secrets:
      - database_url

secrets:
  db_password:
    file: ./secrets/db_password.txt
  database_url:
    file: ./secrets/database_url.txt
```

**Recommendation**:
- Document current approach as "Phase 1"
- Add Docker secrets to "Future Enhancements" (already there)
- Add warning about `.env.production` in gitignore

---

### 6. External Network Naming Inconsistency

**Issue**: Plan uses `npm-proxy` but phentrieve example uses `npm_proxy_network`.

**Impact**:
- Minor confusion
- Inconsistency with your own established pattern
- Network names are case-sensitive and dash vs underscore matters

**Recommendation**:
```yaml
# docker-compose.prod.yml
networks:
  npm_proxy_network:  # Match phentrieve naming
    name: npm_proxy_network
    external: true
  internal:
    driver: bridge
    internal: true

services:
  frontend:
    networks:
      - npm_proxy_network  # Consistent naming

  backend:
    networks:
      - npm_proxy_network
      - internal
```

**Network Creation Command**:
```bash
docker network create npm_proxy_network
```

---

### 7. Missing Health Check Content-Type Header

**Issue**: Health check endpoints return plain text without Content-Type header.

**Impact**:
- Some monitoring tools expect JSON
- Browser warnings about missing content type

**Current**:
```nginx
location /health {
    access_log off;
    return 200 "healthy\n";
}
```

**Better**:
```nginx
location /health {
    access_log off;
    default_type application/json;
    return 200 '{"status":"healthy","service":"frontend"}';
}
```

**Even Better** (proxy to actual health endpoint):
```nginx
location /health {
    proxy_pass http://backend:8000/api/health;
    proxy_set_header Host $host;
}
```

---

## 🟢 Minor Improvements (NICE TO HAVE)

### 8. Add Nginx Client Body Size Limit

**Issue**: No limit on upload size could cause memory issues.

**Solution**:
```nginx
server {
    client_max_body_size 10M;  # Adjust based on needs
}
```

---

### 9. Missing Gzip Configuration in Nginx Spec

**Issue**: Plan mentions "Gzip compression" but doesn't show config.

**Solution**:
```nginx
# Add to nginx.prod.conf
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
gzip_min_length 1000;
gzip_comp_level 6;
gzip_vary on;
```

---

### 10. Backend Dockerfile Missing Specific Tmpfs Paths

**Issue**: Plan shows backend with read-only but doesn't specify which tmpfs mounts FastAPI/Uvicorn needs.

**Solution**:
```yaml
backend:
  read_only: true
  tmpfs:
    - /tmp
    - /run
    - /home/kidney-api/.cache  # For any caching
```

---

### 11. CSP Header Incomplete in Plan

**Issue**: Shows `Content-Security-Policy "default-src 'self'; ..."` without full policy.

**Solution**:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:;" always;
```

**Note**: Vue.js needs `'unsafe-inline'` and `'unsafe-eval'` for development builds. For production with proper build optimization, these can be tightened.

---

### 12. Missing Explicit User ID in Dockerfile

**Issue**: Plan says "Create non-root user (UID 1000)" but doesn't show explicit UID assignment.

**Solution**:
```dockerfile
# Backend Dockerfile
RUN groupadd -r -g 1000 kidney-api && \
    useradd -r -u 1000 -g kidney-api -m -s /bin/bash kidney-api
```

**Why**: Explicit UIDs prevent permission issues with volume mounts.

---

## Anti-Patterns Identified

### 1. ❌ Over-Engineering Read-Only Filesystems

**Pattern**: Applying `read_only: true` to every service without testing needs.

**Why It's Wrong**:
- PostgreSQL struggles with read-only
- FastAPI might need cache directories
- Adds complexity without proportional security gain for internal services

**Better Approach**:
- Focus read-only on **frontend** (static assets)
- Use capability dropping and security opts for backend/database
- Reserve read-only for services that naturally support it

---

### 2. ❌ Assuming Vite Env Vars Work Like Traditional Apps

**Pattern**: Treating Vite environment variables as runtime-configurable.

**Why It's Wrong**:
- Vite is a **build tool**, not a runtime environment
- `import.meta.env.*` values are **replaced at build time**
- This is fundamentally different from Node.js `process.env`

**Better Approach**:
- Generate JavaScript config files at container startup
- Use `window._env_` pattern for runtime configuration
- Document this prominently in deployment guide

---

### 3. ❌ Capability Dropping Without Understanding

**Pattern**: Adding `CAP_NET_BIND_SERVICE` "just in case."

**Why It's Wrong**:
- Violates principle of least privilege
- Port 8000 never needed this capability
- Shows lack of understanding of Linux capabilities

**Better Approach**:
- Drop ALL capabilities by default
- Only add back what's **proven necessary through testing**
- Document why each capability is needed

---

## Security Considerations

### ✅ What's Done Well

1. **Multi-stage builds** - Excellent attack surface reduction
2. **Non-root users** - Correctly applied
3. **Network isolation** - Database on internal network only
4. **No port exposure** - All access via NPM
5. **Health checks** - Comprehensive coverage
6. **Log rotation** - Prevents disk filling

### ⚠️ What Could Be Better

1. **Image scanning** - Mentioned but not enforced in CI/CD
2. **Secrets management** - Env files instead of Docker secrets
3. **Dependency pinning** - No mention of pinning base image tags to digests
4. **SBOM generation** - Not mentioned for supply chain security

---

## Production Readiness Checklist

### Before Implementation

- [ ] **Fix Critical Issue #1**: Vue.js runtime env injection
- [ ] **Fix Critical Issue #2**: Remove unnecessary CAP_NET_BIND_SERVICE
- [ ] **Fix Critical Issue #3**: PostgreSQL read-only configuration
- [ ] **Fix Moderate Issue #4**: Nginx WebSocket map directive
- [ ] **Update**: Network naming to `npm_proxy_network`

### Before Production Deployment

- [ ] **Test**: Vue.js env vars change without rebuild
- [ ] **Test**: PostgreSQL starts with read-only config (or remove it)
- [ ] **Test**: WebSocket connections under load
- [ ] **Verify**: No capabilities added beyond what's needed
- [ ] **Scan**: Images with Docker Scout or Trivy
- [ ] **Document**: Known limitations and future enhancements

### Post-Deployment Monitoring

- [ ] **Monitor**: Container restart frequency
- [ ] **Monitor**: WebSocket connection stability
- [ ] **Monitor**: Resource usage vs limits
- [ ] **Review**: Security scan results
- [ ] **Test**: Disaster recovery procedures

---

## Recommended Changes Priority

### Must Do (Before Implementation)

1. Implement Vue.js runtime env injection mechanism
2. Remove CAP_NET_BIND_SERVICE from specs
3. Fix PostgreSQL read-only configuration or remove it
4. Add Nginx map directive for WebSocket
5. Update network naming for consistency

### Should Do (Before Production)

6. Enhance health check endpoints with proper content types
7. Add client_max_body_size to Nginx config
8. Complete CSP header specification
9. Add explicit UID/GID in Dockerfiles
10. Document secrets rotation procedure

### Nice to Do (Post v0.2.0)

11. Migrate to Docker secrets
12. Implement automated image scanning in CI
13. Add SBOM generation
14. Create backup and restore procedures
15. Set up monitoring dashboard

---

## Testing Recommendations

### Unit Tests for Infrastructure

```bash
# Test 1: Verify non-root users
docker run --rm kidney-genetics-backend id
# Expected: uid=1000(kidney-api) gid=1000(kidney-api)

# Test 2: Verify no unnecessary capabilities
docker inspect kidney-genetics-backend | jq '.[0].HostConfig.CapAdd'
# Expected: null or []

# Test 3: Verify Vue env injection
docker run --rm -e API_BASE_URL=/custom kidney-genetics-frontend cat /usr/share/nginx/html/env-config.js
# Expected: API_BASE_URL: "/custom"

# Test 4: Verify WebSocket upgrade
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://frontend/ws/
# Expected: 101 Switching Protocols
```

### Integration Tests

```bash
# Test 5: Health checks working
docker-compose -f docker-compose.prod.yml ps
# All services should show "healthy"

# Test 6: Database connectivity
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.db.session import get_db; print('DB OK')"

# Test 7: Frontend serves correctly
curl -s http://frontend/ | grep -q "<title>"

# Test 8: API accessible through frontend proxy
curl -s http://frontend/api/health | jq .
```

---

## Conclusion

The plan is **structurally excellent** and shows deep understanding of Docker and security principles. The issues identified are **fixable** and mostly stem from:

1. **Vite-specific behavior** not widely known
2. **Over-application** of security features without testing
3. **Minor gaps** in nginx configuration best practices

### Overall Score: **B+ (85/100)**

**Breakdown**:
- Architecture & Design: A (95/100)
- Security Approach: A- (90/100)
- Implementation Details: B (80/100)
- Documentation: A (95/100)
- Production Readiness: B (75/100) ← Biggest gap

### Recommendation: **APPROVE WITH REVISIONS**

Fix the 3 critical issues before starting implementation. The moderate and minor issues can be addressed during development or in a follow-up PR.

---

## Additional Resources

### Must Read Before Implementation

1. **Vite Environment Variables**: https://vite.dev/guide/env-and-mode
2. **Docker Capabilities**: https://man7.org/linux/man-pages/man7/capabilities.7.html
3. **Nginx WebSocket Proxying**: https://www.f5.com/company/blog/nginx/websocket-nginx
4. **PostgreSQL Docker Best Practices**: https://www.docker.com/blog/how-to-use-the-postgres-docker-official-image/

### Security Scanning Tools

```bash
# Install Docker Scout
docker scout quickview

# Scan backend image
docker scout cves kidney-genetics-backend

# Scan with Trivy
trivy image kidney-genetics-backend

# Generate SBOM
docker sbom kidney-genetics-backend > backend-sbom.json
```

---

**Reviewed By**: Senior Developer
**Review Date**: 2025-10-10
**Next Review**: After critical fixes implemented
