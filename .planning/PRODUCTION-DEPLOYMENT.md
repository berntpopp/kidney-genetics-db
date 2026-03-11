# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose v2+
- A VPS with 4+ CPU cores and 8+ GB RAM
- A domain name pointed at the server
- Nginx Proxy Manager (NPM) running on the server

## Quick Start

### 1. Create Docker Network

```bash
docker network create npm_proxy_network
```

### 2. Configure Environment

```bash
cp .env.production.example .env.production
# Edit .env.production with your values:
# - POSTGRES_PASSWORD (strong, unique)
# - SECRET_KEY (generate: openssl rand -hex 32)
# - ADMIN_USERNAME / ADMIN_PASSWORD
# - ALLOWED_ORIGINS (your domain)
```

### 3. Start Services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Configure Nginx Proxy Manager

**Frontend proxy host:**
- Domain: `your-domain.com`
- Forward hostname: `kidney_genetics_frontend`
- Forward port: `8080`
- SSL: Request Let's Encrypt certificate

**API proxy host:**
- Domain: `your-domain.com`
- Custom location: `/api` → `kidney_genetics_backend:8000`
- Custom location: `/health` → `kidney_genetics_backend:8000`
- WebSocket support: Enable for `/api/progress/ws`

**Advanced nginx config for WebSocket:**
```nginx
location /api/progress/ws {
    proxy_pass http://kidney_genetics_backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

### 5. Verify Deployment

```bash
# Health checks
curl https://your-domain.com/health        # Frontend nginx
curl https://your-domain.com/api/health    # Backend API

# Create admin user (if not auto-created)
# Done via ADMIN_USERNAME/ADMIN_PASSWORD env vars on first startup
```

### 6. Run Initial Pipeline

Via API (recommended):
```bash
curl -X POST https://your-domain.com/api/annotations/pipeline/update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "full"}'
```

## Automated Backups

The `db-backup` sidecar automatically:
- Creates daily backups at 2:00 AM
- Keeps 7 daily, 4 weekly, 6 monthly backups
- Stores in the `db-backups` Docker volume

### Manual Backup

```bash
docker exec kidney_genetics_db_backup /backup.sh
```

### List Backups

```bash
docker exec kidney_genetics_db_backup ls -la /backups/
```

### Restore from Backup

```bash
# Stop the backend first
docker compose -f docker-compose.prod.yml stop backend

# Restore (replace filename)
docker exec -i kidney_genetics_postgres \
  pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists \
  < /path/to/backup.dump

# Restart
docker compose -f docker-compose.prod.yml up -d backend
```

## Production Checklist

- [ ] Create Docker network: `docker network create npm_proxy_network`
- [ ] Copy `.env.production.example` → `.env.production`, fill secrets
- [ ] `docker compose -f docker-compose.prod.yml up -d`
- [ ] Configure NPM proxy hosts (frontend + API)
- [ ] Request SSL certificates via NPM
- [ ] Verify health: `/health` (frontend), `/api/health` (backend)
- [ ] Create initial admin user (via env vars or API)
- [ ] Run initial data pipeline via API
- [ ] Verify WebSocket connection for pipeline progress
- [ ] Verify backup sidecar is running: `docker logs kidney_genetics_db_backup`
- [ ] Test backup restore on a non-production instance
