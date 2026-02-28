# Quick Reference - VPS Deployment

**Last Updated:** 2025-10-12

Quick reference for directory structure, required files, and common commands for VPS deployment.

---

## Directory Structure

### Required Directories

```
/opt/
├── kidney-genetics-db/                    # Main application directory
│   ├── .git/                              # Git repository
│   ├── backend/                           # Backend application code
│   │   ├── app/                           # Python application
│   │   ├── Dockerfile                     # Backend Docker build
│   │   └── pyproject.toml                 # Python dependencies
│   ├── frontend/                          # Frontend application code
│   │   ├── src/                           # Vue.js application
│   │   ├── Dockerfile                     # Frontend Docker build
│   │   ├── nginx.prod.conf                # Nginx configuration
│   │   └── package.json                   # NPM dependencies
│   ├── backups/                           # Database backups (auto-created)
│   ├── logs/                              # Application logs (optional)
│   ├── data/                              # Persistent data (optional)
│   ├── docker-compose.prod.yml            # Production compose file
│   ├── docker-compose.prod.test.yml       # Test compose file (localhost ports)
│   ├── .env.production                    # ⚠️ REQUIRED - Environment variables
│   ├── .env.production.example            # Example environment file
│   ├── backup.sh                          # ⚠️ CREATE - Backup script
│   └── monitor.sh                         # CREATE - Monitoring script (optional)
└── nginx-proxy-manager/                   # NPM directory
    ├── data/                              # NPM database
    ├── letsencrypt/                       # SSL certificates
    └── docker-compose.yml                 # NPM compose file
```

### Create Directories Command

```bash
# Create all directories at once
sudo mkdir -p /opt/kidney-genetics-db/{backups,logs,data}
sudo mkdir -p /opt/nginx-proxy-manager/{data,letsencrypt}
sudo chown -R $USER:$USER /opt/kidney-genetics-db /opt/nginx-proxy-manager
```

---

## Required Files

### 1. .env.production (REQUIRED)

**Location:** `/opt/kidney-genetics-db/.env.production`
**Permissions:** `600` (read/write owner only)

**Template:**
```bash
# Database Configuration
POSTGRES_DB=kidney_genetics
POSTGRES_USER=kidney_user
POSTGRES_PASSWORD=<GENERATE_SECURE_PASSWORD>

# Database URL
DATABASE_URL=postgresql://kidney_user:<SAME_PASSWORD>@kidney_genetics_postgres:5432/kidney_genetics

# Backend Configuration
SECRET_KEY=<GENERATE_SECURE_KEY>
BACKEND_CORS_ORIGINS=[]
API_V1_STR=/api/v1
PROJECT_NAME=Kidney Genetics Database
LOG_LEVEL=INFO
LOG_FORMAT=json
ALLOWED_HOSTS=localhost,your-domain.com

# Production domain
DOMAIN=your-domain.com
```

**Generate Secure Values:**
```bash
# Database password
openssl rand -base64 32

# Secret key
openssl rand -hex 32
```

**Create File:**
```bash
# Copy from example and edit
cp .env.production.example .env.production
nano .env.production

# Set proper permissions
chmod 600 .env.production
```

### 2. backup.sh (REQUIRED)

**Location:** `/opt/kidney-genetics-db/backup.sh`
**Permissions:** `755` (executable)

**Content:**
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/kidney-genetics-db/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/kidney_genetics_$DATE.sql"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

docker exec kidney_genetics_postgres pg_dump \
  -U kidney_user kidney_genetics > "$BACKUP_FILE"

gzip "$BACKUP_FILE"

echo "[$(date)] Backup completed: $BACKUP_FILE.gz"

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Cleanup complete"
```

**Create File:**
```bash
nano /opt/kidney-genetics-db/backup.sh
# Paste content above
chmod +x /opt/kidney-genetics-db/backup.sh

# Test
./backup.sh
```

### 3. NPM docker-compose.yml (REQUIRED)

**Location:** `/opt/nginx-proxy-manager/docker-compose.yml`

**Content:**
```yaml
version: '3.8'

services:
  npm:
    image: 'jc21/nginx-proxy-manager:latest'
    container_name: nginx-proxy-manager
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    environment:
      DB_SQLITE_FILE: "/data/database.sqlite"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
    networks:
      - npm_proxy_network

networks:
  npm_proxy_network:
    external: true
```

---

## Docker Networks

### npm_proxy_network (REQUIRED)

**Create Network:**
```bash
docker network create npm_proxy_network
```

**Verify Network:**
```bash
docker network ls | grep npm_proxy_network
```

**Check Which Containers Use It:**
```bash
docker network inspect npm_proxy_network
```

---

## Common Commands

### Deployment Commands

```bash
# Clone repository
cd /opt/kidney-genetics-db
git clone https://github.com/bernt-popp/kidney-genetics-db.git .

# Build images
docker compose -f docker-compose.prod.yml build --no-cache

# Test deployment (with localhost ports)
docker compose -f docker-compose.prod.test.yml up -d

# Production deployment (no exposed ports, NPM only)
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f --tail=50

# Stop services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (⚠️ DELETES DATA)
docker compose -f docker-compose.prod.yml down -v
```

### Service Management

```bash
# Restart all services
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker restart kidney_genetics_backend
docker restart kidney_genetics_frontend
docker restart kidney_genetics_postgres

# Stop specific service
docker stop kidney_genetics_backend

# Start specific service
docker start kidney_genetics_backend

# View service logs
docker logs kidney_genetics_backend -f --tail=100
```

### Health Checks

```bash
# Check container health
docker ps --filter "name=kidney_genetics" --format "table {{.Names}}\t{{.Status}}"

# Test backend health
curl http://localhost:8001/health
# Production: curl https://your-domain.com/api/v1/health

# Test frontend health
curl http://localhost:8080/health
# Production: curl https://your-domain.com/health

# Check database
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics
```

### Database Operations

```bash
# Connect to database
docker exec -it kidney_genetics_postgres psql -U kidney_user -d kidney_genetics

# Backup database
./backup.sh

# List backups
ls -lh /opt/kidney-genetics-db/backups/

# Restore backup (replace FILENAME)
gunzip -c /opt/kidney-genetics-db/backups/FILENAME.sql.gz | \
  docker exec -i kidney_genetics_postgres psql -U kidney_user kidney_genetics

# Check database size
docker exec kidney_genetics_postgres psql -U kidney_user -d kidney_genetics \
  -c "SELECT pg_size_pretty(pg_database_size('kidney_genetics'));"
```

### Update Application

```bash
cd /opt/kidney-genetics-db

# Pull latest code
git pull origin main

# Rebuild images
docker compose -f docker-compose.prod.yml build --no-cache

# Restart with new images
docker compose -f docker-compose.prod.yml up -d

# Check logs for errors
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

### Monitoring

```bash
# Container resource usage
docker stats --no-stream kidney_genetics_backend kidney_genetics_frontend kidney_genetics_postgres

# Continuous monitoring (updates every 5 seconds)
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"'

# Disk usage
df -h /opt/kidney-genetics-db /var/lib/docker

# Check Docker volume usage
docker system df -v

# View Docker logs size
du -sh /var/lib/docker/containers/*
```

### Security Verification

```bash
# Check non-root users
docker exec kidney_genetics_backend id
docker exec kidney_genetics_frontend id

# Check capabilities
docker inspect kidney_genetics_backend | grep -A5 "CapDrop"

# Check security headers
curl -I https://your-domain.com | grep -E "X-Frame|X-Content|Security-Policy"

# Check resource limits
docker inspect kidney_genetics_backend | grep -A10 "Resources"

# Verify SHA256 pinning
docker inspect kidney_genetics_postgres | grep Image
```

### Troubleshooting

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs --tail=100

# Check for errors in logs
docker compose -f docker-compose.prod.yml logs | grep -i error

# Check container inspect (detailed info)
docker inspect kidney_genetics_backend

# Check network connectivity
docker network inspect npm_proxy_network

# Test DNS resolution from within container
docker exec kidney_genetics_backend ping kidney_genetics_postgres

# Check port bindings
sudo netstat -tulpn | grep -E '80|443|8000|8080|5432'

# Restart Docker daemon (if needed)
sudo systemctl restart docker
```

---

## NPM Configuration Quick Reference

### Frontend Proxy Host

**Domain:** your-domain.com
**Forward To:** `kidney_genetics_frontend:8080` ⚠️ **Port 8080, not 80!**
**SSL:** Let's Encrypt (auto)
**WebSockets:** Enabled
**Force SSL:** Enabled

### Custom Nginx Config (Advanced Tab)

```nginx
client_max_body_size 10M;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

---

## Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow NPM admin (restrict to your IP!)
sudo ufw allow from YOUR_IP to any port 81 proto tcp

# Deny application ports (accessed via NPM only)
sudo ufw deny 8000/tcp
sudo ufw deny 8080/tcp
sudo ufw deny 5432/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status numbered
```

---

## Cron Jobs

### Automated Backups

```bash
# Edit crontab
crontab -e

# Add this line (daily backup at 2 AM)
0 2 * * * /opt/kidney-genetics-db/backup.sh >> /opt/kidney-genetics-db/backup.log 2>&1
```

### Optional: Daily Health Check

```bash
# Add to crontab
0 */4 * * * curl -sf https://your-domain.com/health || echo "Health check failed" | mail -s "Health Check Alert" your-email@example.com
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `POSTGRES_DB` | ✅ | Database name | `kidney_genetics` |
| `POSTGRES_USER` | ✅ | Database user | `kidney_user` |
| `POSTGRES_PASSWORD` | ✅ | Database password | `<generate-secure>` |
| `DATABASE_URL` | ✅ | Full connection string | See template above |
| `SECRET_KEY` | ✅ | Backend secret key | `<generate-secure>` |
| `BACKEND_CORS_ORIGINS` | ✅ | CORS origins (JSON array) | `[]` for production |
| `API_V1_STR` | ✅ | API version prefix | `/api/v1` |
| `PROJECT_NAME` | ✅ | Project name | `Kidney Genetics Database` |
| `LOG_LEVEL` | ✅ | Logging level | `INFO` |
| `LOG_FORMAT` | ✅ | Log format | `json` |
| `ALLOWED_HOSTS` | ✅ | Allowed hostnames | `localhost,your-domain.com` |
| `DOMAIN` | ✅ | Production domain | `your-domain.com` |

---

## Port Reference

| Port | Service | Exposure | Purpose |
|------|---------|----------|---------|
| `80` | NPM | Public | HTTP (redirects to HTTPS) |
| `443` | NPM | Public | HTTPS (production traffic) |
| `81` | NPM | Restricted IP | Admin panel |
| `8000` | Backend | Internal only | Backend API (NPM proxies) |
| `8080` | Frontend | Internal only | Frontend nginx (NPM proxies) |
| `5432` | PostgreSQL | Internal only | Database (backend connects) |
| `8001` | Backend Test | Localhost only | Test mode only |

---

## Quick Diagnostics

```bash
# One-line health check
curl -sf https://your-domain.com/health && echo "✓ Healthy" || echo "✗ Unhealthy"

# Container status one-liner
docker ps --filter "name=kidney_genetics" --format "{{.Names}}: {{.Status}}"

# Resource usage one-liner
docker stats --no-stream --format "{{.Name}}: CPU {{.CPUPerc}}, MEM {{.MemUsage}}"

# Backup size check
du -sh /opt/kidney-genetics-db/backups/

# Log size check
docker compose -f docker-compose.prod.yml logs --tail=1 | wc -l
```

---

## URLs Reference

| URL | Purpose |
|-----|---------|
| `http://YOUR_VPS_IP:81` | NPM Admin Panel |
| `https://your-domain.com` | Production Site (Frontend) |
| `https://your-domain.com/health` | Frontend Health |
| `https://your-domain.com/api/v1/health` | Backend Health (via frontend proxy) |
| `https://your-domain.com/docs` | API Documentation (Swagger UI) |
| `http://localhost:8080` | Frontend (test mode only) |
| `http://localhost:8001` | Backend (test mode only) |

---

## Support

- **Full VPS Setup Guide:** [vps-setup-guide.md](vps-setup-guide.md)
- **Production Deployment:** [production-deployment.md](production-deployment.md)
- **Troubleshooting:** [troubleshooting.md](troubleshooting.md)
- **Security Documentation:** [../implementation-notes/completed/docker-security-implementation-summary.md](../implementation-notes/completed/docker-security-implementation-summary.md)
