# Docker Troubleshooting Guide

Common issues and solutions for Docker-based deployment.

## Quick Diagnostics

### System Health Check
```bash
# Check all services status
docker ps --filter "name=kidney_genetics"

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=50

# Check health status
docker inspect kidney_genetics_backend | grep -A 10 Health
docker inspect kidney_genetics_postgres | grep -A 10 Health

# Check networks
docker network inspect npm_proxy_network
docker network inspect kidney_genetics_internal_net
```

---

## Build Issues

### Problem: "README.md file does not exist" (Backend)

**Symptoms:**
```
OSError: Readme file does not exist: README.md
```

**Cause:** README.md not copied to Docker build context.

**Solution:**
```dockerfile
# backend/Dockerfile - line 21
COPY pyproject.toml README.md ./  # Must include README.md
```

**Verify:**
```bash
ls backend/README.md
cat backend/.dockerignore | grep -i readme  # Should NOT exclude it
```

---

### Problem: "npm ci requires package-lock.json" (Frontend)

**Symptoms:**
```
npm error The `npm ci` command can only install with an existing package-lock.json
```

**Cause:** package-lock.json excluded by .dockerignore.

**Solution:**
```bash
# frontend/.dockerignore should NOT have:
# package-lock.json  ❌ REMOVE THIS LINE

# Keep node_modules excluded but include package-lock.json
```

**Verify:**
```bash
ls frontend/package-lock.json
cat frontend/.dockerignore | grep package-lock.json  # Should be absent or commented
```

---

### Problem: Build context too large / slow

**Symptoms:**
```
Sending build context to Docker daemon  1.5GB
```

**Solution:**

Check .dockerignore files:
```bash
# Backend
cat backend/.dockerignore
# Should exclude: node_modules/, tests/, docs/, .git/

# Frontend
cat frontend/.dockerignore
# Should exclude: node_modules/, dist/, .git/
```

**Verify build context size:**
```bash
# Should be <10MB for backend, <5MB for frontend
docker build --no-cache -f backend/Dockerfile backend/ 2>&1 | grep "Sending build context"
```

---

## Runtime Issues

### Problem: Containers fail to start

**Symptoms:**
```bash
docker ps --filter "name=kidney_genetics"
# Shows no running containers or constantly restarting
```

**Diagnostic steps:**

1. **Check logs:**
```bash
docker compose -f docker-compose.prod.yml logs
```

2. **Check specific service:**
```bash
docker logs kidney_genetics_backend
docker logs kidney_genetics_frontend
docker logs kidney_genetics_postgres
```

3. **Check exit codes:**
```bash
docker ps -a --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}"
```

**Common causes:**

#### Database connection failure
```bash
# Check DATABASE_URL in .env.production
grep DATABASE_URL .env.production

# Should match: postgresql://kidney_user:PASSWORD@kidney_genetics_postgres:5432/kidney_genetics
#                                               ^^^^^^^^^^^^^^^^^^^^^^^^
#                                               Must be container name!
```

#### Missing .env.production
```bash
ls -la .env.production
# If not found:
cp .env.production.example .env.production
# Then edit with actual credentials
```

#### Network not found
```bash
docker network inspect npm_proxy_network
# If error:
docker network create npm_proxy_network
```

---

### Problem: "Unhealthy" status

**Symptoms:**
```bash
docker ps --filter "name=kidney_genetics"
# STATUS shows "(unhealthy)"
```

**Diagnostic:**

```bash
# Check health check logs
docker inspect kidney_genetics_backend | jq '.[0].State.Health'

# Manual health check
docker exec kidney_genetics_backend curl -f http://localhost:8000/api/health
```

**Solutions:**

#### Backend unhealthy
```bash
# Check if backend is actually running
docker exec kidney_genetics_backend ps aux | grep uvicorn

# Check backend logs
docker logs kidney_genetics_backend --tail=100

# Common issues:
# - Database not ready (check postgres health)
# - Port 8000 already in use (check docker ps)
# - Missing environment variables (check .env.production)
```

#### Database unhealthy
```bash
# Check database logs
docker logs kidney_genetics_postgres --tail=100

# Try manual connection
docker exec kidney_genetics_postgres psql -U kidney_user -d kidney_genetics -c "SELECT 1;"

# Check disk space
df -h /var/lib/docker
```

---

### Problem: NPM cannot reach containers

**Symptoms:**
- NPM shows "502 Bad Gateway"
- NPM proxy host shows "Offline"

**Diagnostic:**

```bash
# Verify containers are on npm_proxy_network
docker inspect kidney_genetics_frontend | grep npm_proxy_network
docker inspect kidney_genetics_backend | grep npm_proxy_network

# Test connectivity from NPM container
NPM_CONTAINER=$(docker ps --filter "name=nginx-proxy-manager" --format "{{.Names}}")
docker exec $NPM_CONTAINER ping -c 2 kidney_genetics_frontend
docker exec $NPM_CONTAINER curl -I http://kidney_genetics_frontend:80
```

**Solutions:**

#### Containers not on network
```bash
# Restart services (will auto-join networks)
docker compose -f docker-compose.prod.yml restart

# Or manually connect (temporary):
docker network connect npm_proxy_network kidney_genetics_frontend
```

#### Wrong container names in NPM
```bash
# NPM proxy configuration must use EXACT container names with underscores:
# ✅ kidney_genetics_frontend
# ❌ kidney-genetics-frontend (dashes won't work!)

# Verify actual names:
docker ps --format "table {{.Names}}"
```

#### Port mismatch
```nginx
# NPM Forward Port must match container internal port:
Frontend:  80  (not 8080!)
Backend:   8000
```

---

## SSL/TLS Issues

### Problem: SSL certificate fails to provision

**Symptoms:**
- NPM shows "Certificate request failed"
- HTTPS site shows "Connection not secure"

**Solutions:**

#### DNS not pointed correctly
```bash
# Verify DNS resolution
nslookup db.kidney-genetics.org

# Should return your VPS IP
# If not, update DNS A record and wait 5-60 minutes for propagation
```

#### Ports 80/443 blocked
```bash
# Check firewall
sudo ufw status | grep -E "80|443"

# Should show:
# 80/tcp                     ALLOW       Anywhere
# 443/tcp                    ALLOW       Anywhere

# If not:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

#### Rate limit hit (Let's Encrypt)
```
# Let's Encrypt limits: 5 failures per account per hour
# Solution: Wait 1 hour before retrying
```

---

## Database Issues

### Problem: Database connection refused

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Diagnostic:**
```bash
# Check if PostgreSQL is running
docker ps --filter "name=kidney_genetics_postgres"

# Check health
docker exec kidney_genetics_postgres pg_isready -U kidney_user

# Check logs
docker logs kidney_genetics_postgres --tail=50
```

**Solutions:**

#### PostgreSQL not healthy yet
```bash
# Wait for health check to pass (10-30 seconds)
watch -n 2 'docker inspect kidney_genetics_postgres | grep -A 5 Health'
```

#### Wrong database credentials
```bash
# Verify .env.production matches docker-compose
grep POSTGRES .env.production

# Test connection manually
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

---

### Problem: Database data lost after restart

**Symptoms:**
- All data disappears when containers restart
- Database starts empty

**Cause:** Volume not properly configured or removed.

**Diagnostic:**
```bash
# Check if volume exists
docker volume ls | grep kidney_genetics_postgres_data

# Check volume mount
docker inspect kidney_genetics_postgres | grep -A 10 Mounts
```

**Solutions:**

#### Volume deleted accidentally
```bash
# Check docker-compose has named volume:
grep -A 2 "volumes:" docker-compose.prod.yml
# Should show:
#   kidney_genetics_postgres_data:
#     name: kidney_genetics_postgres_data

# Restore from backup:
docker exec -i kidney_genetics_postgres psql \
  -U kidney_user kidney_genetics < backup.sql
```

#### Using wrong compose file
```bash
# ❌ DON'T USE:
docker compose down -v  # -v flag REMOVES volumes!

# ✅ USE:
docker compose down     # Keeps volumes
```

---

## Performance Issues

### Problem: Slow response times

**Symptoms:**
- API requests take >5 seconds
- Frontend loads slowly

**Diagnostic:**

```bash
# Check container resource usage
docker stats --no-stream kidney_genetics_backend kidney_genetics_frontend kidney_genetics_postgres

# Check logs for errors
docker logs kidney_genetics_backend --tail=100 | grep -i error

# Check database queries
docker exec kidney_genetics_postgres psql -U kidney_user -d kidney_genetics -c "
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
"
```

**Solutions:**

#### High memory usage (backend)
```bash
# Restart backend to clear cache
docker restart kidney_genetics_backend

# Check for memory leaks in logs
docker logs kidney_genetics_backend | grep -i "memory\|oom"
```

#### Database slow queries
```sql
-- Connect to database
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics

-- Check missing indexes
SELECT schemaname, tablename, attname, null_frac, avg_width, n_distinct
FROM pg_stats
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY null_frac DESC;

-- Check table sizes
SELECT schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

### Problem: Disk space issues

**Symptoms:**
```
Error: no space left on device
```

**Diagnostic:**
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Check log sizes
du -sh /var/lib/docker/containers/*/*-json.log | sort -h
```

**Solutions:**

```bash
# Clean up old images
docker image prune -a

# Clean up old containers
docker container prune

# Clean up build cache
docker builder prune -a

# Rotate large logs manually
truncate -s 0 /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

---

## WebSocket Issues

### Problem: WebSocket connections fail

**Symptoms:**
- Real-time updates don't work
- Browser console shows "WebSocket connection failed"

**Diagnostic:**
```bash
# Test WebSocket from command line
npm install -g wscat
wscat -c wss://db.kidney-genetics.org/ws/test

# Check nginx configuration
docker exec kidney_genetics_frontend cat /etc/nginx/conf.d/default.conf | grep -A 10 "location /ws"
```

**Solutions:**

#### NPM WebSocket support not enabled
```
In NPM Proxy Host configuration:
- Websockets Support: ✅ MUST BE ENABLED
```

#### Missing Connection header map
```nginx
# nginx.prod.conf must have:
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

location /ws/ {
    proxy_set_header Connection $connection_upgrade;  # Use mapped variable!
}
```

---

## Makefile Issues

### Problem: "make: command not found"

**Solution:**
```bash
# Install make
sudo apt-get update && sudo apt-get install make

# Or run docker-compose directly:
docker compose -f docker-compose.prod.yml up -d
```

---

### Problem: "npm_proxy_network missing"

**Symptoms:**
```bash
make prod-up
# Error: network npm_proxy_network not found
```

**Solution:**
```bash
# Create network
make npm-network-create

# Or manually:
docker network create npm_proxy_network

# Verify:
docker network ls | grep npm_proxy
```

---

## Environment Variable Issues

### Problem: Frontend API calls fail (404 or CORS)

**Symptoms:**
- Browser console: "Failed to fetch" or CORS error
- Frontend can't reach backend

**Diagnostic:**
```bash
# Check frontend runtime config
docker exec kidney_genetics_frontend cat /usr/share/nginx/html/env-config.js

# Should show:
# window._env_ = {
#   API_BASE_URL: "/api",
#   WS_URL: "/ws",
#   ...
# };
```

**Solutions:**

#### env-config.js not generated
```bash
# Check docker-entrypoint.sh permissions
docker exec kidney_genetics_frontend ls -la /docker-entrypoint.d/40-inject-runtime-env.sh
# Should be executable (-rwxr-xr-x)

# Restart frontend to re-run entrypoint
docker restart kidney_genetics_frontend
```

#### Wrong API_BASE_URL
```bash
# Check environment in docker-compose.prod.yml
grep -A 3 "environment:" docker-compose.prod.yml | grep -A 3 "frontend:"

# Should have:
#   API_BASE_URL: /api
#   WS_URL: /ws

# If using custom values, restart after changing:
docker compose -f docker-compose.prod.yml up -d --force-recreate frontend
```

---

## Emergency Procedures

### Full Reset (Nuclear Option)

⚠️ **WARNING: This will DELETE ALL DATA!**

```bash
# Stop all containers
docker compose -f docker-compose.prod.yml down

# Remove volumes (DATA LOSS!)
docker volume rm kidney_genetics_postgres_data

# Remove images
docker rmi kidney_genetics_backend:latest
docker rmi kidney_genetics_frontend:latest

# Rebuild from scratch
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### Backup Before Reset

```bash
# Backup database
docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user kidney_genetics > emergency_backup_$(date +%Y%m%d_%H%M%S).sql

# Backup volumes
docker run --rm -v kidney_genetics_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_volume_backup.tar.gz /data

# Now safe to reset
```

---

## Getting Help

### Collect Debug Info

Before asking for help, collect this information:

```bash
# System info
docker --version
docker compose version
uname -a

# Container status
docker ps -a --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Logs (last 100 lines each service)
docker compose -f docker-compose.prod.yml logs --tail=100 > debug_logs.txt

# Network config
docker network inspect npm_proxy_network > network_debug.txt
docker network inspect kidney_genetics_internal_net >> network_debug.txt

# Resource usage
docker stats --no-stream >> debug_logs.txt
```

### Support Channels

1. Check [Production Deployment Guide](production-deployment.md)
2. Review [Architecture Documentation](architecture.md)
3. Check [GitHub Issues](https://github.com/bernt-popp/kidney-genetics-db/issues)
4. Consult CLAUDE.md for development patterns

---

## Related Documentation

- [Production Deployment](production-deployment.md) - Deployment steps
- [Docker Architecture](architecture.md) - System design
- [Dockerfile Reference](dockerfile-reference.md) - Build details
- [README](README.md) - Documentation index
